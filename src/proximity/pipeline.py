"""Headline pass: five-city hexes, dual-access walk times, maps."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.ops import unary_union

from .access import mean_time_to_n
from .car_access import GRADE_LABELS, WALK_LABEL, car_dual_access, walk_dual_access
from .cartography import framed_choropleth
from .cities import CITIES, HEX_SIDE_M, N_DUAL_NONSUBSTITUTABLE, WALK_M_PER_MIN, City
from .download import DATASETS, ensure_inputs, unzip_if_needed
from .hexgrid import hex_grid
from .metrics import city_metrics, metrics_table
from .facilities import filter_state, load_local_facilities
from .gpkg_styles import embed_metro_lga_style
from .paths import DATA_PROCESSED, DATA_RAW, MAPS
from .population import (
    link_local_rasters,
    populate_hexes,
    population_label,
    resolve_population_raster,
)


def _first_vector(folder: Path) -> Path:
    for ext in ("*.gpkg", "*.shp", "*.geojson"):
        hits = list(folder.rglob(ext))
        if hits:
            return hits[0]
    raise FileNotFoundError(folder)


def _read_points(path: Path) -> gpd.GeoDataFrame:
    if path.suffix == ".zip":
        path = _first_vector(unzip_if_needed(path))
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    if gdf.geom_type.isin(["Polygon", "MultiPolygon"]).any():
        gdf = gdf.copy()
        gdf.geometry = gdf.geometry.centroid
    return gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()


def _clip(gdf: gpd.GeoDataFrame, city: City) -> gpd.GeoDataFrame:
    west, south, east, north = city.bbox
    return gdf.cx[west:east, south:north].copy()


def metro_lga_polygons(city: City) -> gpd.GeoDataFrame:
    path = DATA_RAW / DATASETS["geoboundaries_adm2"]["filename"]
    gdf = gpd.read_file(path)
    gdf = gdf[gdf["shapeName"].isin(city.metro_lgas)]
    west, south, east, north = city.bbox
    gdf = gdf.cx[west:east, south:north].copy()
    if gdf.empty:
        raise RuntimeError(f"No metro LGAs found for {city.name}")
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326)


def urban_boundary_lgas(city: City) -> gpd.GeoDataFrame:
    gdf = metro_lga_polygons(city)
    return gpd.GeoDataFrame(geometry=[unary_union(gdf.geometry)], crs=gdf.crs)


def load_facility_layers() -> dict[str, gpd.GeoDataFrame]:
    paths = ensure_inputs(["grid3_health_v3", "grid3_schools", "hotosm_health", "hotosm_education"])
    out: dict[str, gpd.GeoDataFrame] = {}
    for key, kind in [
        ("grid3_health_v3", "health_grid3_v3"),
        ("grid3_schools", "education_grid3"),
        ("hotosm_health", "health_osm"),
        ("hotosm_education", "education_osm"),
    ]:
        if key not in paths:
            continue
        try:
            out[kind] = _read_points(paths[key])
        except Exception as exc:
            print(f"could not read {key}: {exc}")
    return out


def overpass_facilities(city: City) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    from .overpass import fetch_amenities

    health = fetch_amenities(city, ["hospital", "clinic", "doctors", "healthcare"])
    schools = fetch_amenities(city, ["school", "college", "university", "kindergarten"])
    return health, schools


def analyse_city(
    city: City,
    facilities: dict[str, gpd.GeoDataFrame],
    pop_raster: Path | None,
    pop_layer: int = 2,
    write_maps: bool = True,
    reuse_hexes: bool = True,
    with_car: bool = False,
) -> dict:
    boundary = urban_boundary_lgas(city)
    gpkg = DATA_PROCESSED / f"{city.slug}_hexes.gpkg"
    if reuse_hexes and gpkg.exists():
        hexes = gpd.read_file(gpkg)
        hexes = hexes[["geometry"]].copy()
        hexes["hex_id"] = range(len(hexes))
    else:
        hexes = hex_grid(boundary, HEX_SIDE_M)
    pop_source = population_label(pop_raster, pop_layer)
    if pop_raster and pop_raster.exists() and pop_raster.stat().st_size > 1000:
        hexes = populate_hexes(hexes, pop_raster)
    else:
        hexes = hexes.copy()
        hexes["pop"] = 1.0
        pop_source = population_label(None, pop_layer)

    hexes_wgs = hexes.to_crs(4326)
    frame = unary_union(boundary.to_crs(4326).geometry)

    def _inside(gdf: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame | None:
        if gdf is None or len(gdf) == 0:
            return gdf
        pts = gdf.to_crs(4326)
        return pts[pts.intersects(frame)].copy()

    def _health_layer(key: str) -> gpd.GeoDataFrame | None:
        raw = facilities.get(key)
        clipped = _inside(raw)
        if clipped is None or len(clipped) == 0:
            return None
        clipped = filter_state(clipped, city)
        return clipped if len(clipped) else None

    health = _health_layer("health_grid3_v3")
    health_source = "GRID3 health v3.0"
    if health is None:
        health = _health_layer("health_grid3_v2")
        health_source = "GRID3 health v2.0"
    schools = _inside(facilities["education_grid3"]) if "education_grid3" in facilities else None
    if schools is not None and len(schools):
        schools = filter_state(schools, city)
    school_source = "GRID3 schools / HDX"

    if health is None or len(health) == 0:
        osm_h = _inside(facilities["health_osm"]) if "health_osm" in facilities else None
        if osm_h is not None and len(osm_h):
            health = osm_h
            health_source = "HOT OSM on HDX (GRID3 gap)"
        else:
            try:
                from .overpass import fetch_amenities

                health = _inside(fetch_amenities(city, ["hospital", "clinic", "doctors"]))
                health_source = "OSM Overpass (GRID3 gap)"
            except Exception as exc:
                print(f"Overpass health failed for {city.name}: {exc}")
                health = gpd.GeoDataFrame(geometry=[], crs=4326)

    if schools is None or len(schools) == 0:
        osm_s = _inside(facilities["education_osm"]) if "education_osm" in facilities else None
        if osm_s is not None and len(osm_s):
            schools = osm_s
            school_source = "HOT OSM on HDX"
        else:
            try:
                _, schools = overpass_facilities(city)
                schools = _inside(schools)
                school_source = "OSM Overpass (HDX not local)"
            except Exception as exc:
                print(f"Overpass schools failed for {city.name}: {exc}")
                schools = gpd.GeoDataFrame(geometry=[], crs=4326)

    if health is None:
        health = gpd.GeoDataFrame(geometry=[], crs=4326)
    if schools is None:
        schools = gpd.GeoDataFrame(geometry=[], crs=4326)

    t_health_eu, k_health_eu = mean_time_to_n(hexes_wgs, health, n=N_DUAL_NONSUBSTITUTABLE)
    t_school_eu, k_school_eu = mean_time_to_n(hexes_wgs, schools, n=N_DUAL_NONSUBSTITUTABLE)

    hexes = hexes_wgs.copy()
    hexes["t_health_eucl"] = t_health_eu
    hexes["t_school_eucl"] = t_school_eu
    stacked_eu = np.vstack([t_health_eu, t_school_eu])
    with np.errstate(all="ignore"):
        hexes["PT_eucl"] = np.nanmean(stacked_eu, axis=0)
    hexes.loc[~np.isfinite(t_health_eu) & ~np.isfinite(t_school_eu), "PT_eucl"] = np.nan

    prev_car = None
    if with_car and reuse_hexes and gpkg.exists():
        prev = gpd.read_file(gpkg)
        if len(prev) == len(hexes) and "PT_car_A" in prev.columns:
            prev_car = prev

    walk_ok = False
    try:
        walk = walk_dual_access(hexes_wgs, health, schools, city, n=N_DUAL_NONSUBSTITUTABLE)
        hexes["t_health"] = walk["t_health_walk"]
        hexes["t_school"] = walk["t_school_walk"]
        hexes["k_health"] = walk["k_health_walk"]
        hexes["k_school"] = walk["k_school_walk"]
        hexes["PT_k"] = walk["PT_walk"]
        hexes["PT_walk"] = walk["PT_walk"]
        walk_ok = True
    except Exception as exc:
        print(f"OSM walk routing failed for {city.name}, Euclidean headline: {exc}", flush=True)
        hexes["t_health"] = t_health_eu
        hexes["t_school"] = t_school_eu
        hexes["k_health"] = k_health_eu
        hexes["k_school"] = k_school_eu
        hexes["PT_k"] = hexes["PT_eucl"]

    hexes["mapped"] = np.isfinite(hexes["PT_k"])
    hexes["within_15"] = hexes["mapped"] & (hexes["PT_k"] <= 15)

    if prev_car is not None:
        for col in prev_car.columns:
            if col.startswith("PT_car_") or col.startswith("t_health_car_") or col.startswith("t_school_car_") or col.startswith("within_15_car_"):
                hexes[col] = prev_car[col].to_numpy()
        print("reused car grade columns from previous hex file", flush=True)
    elif with_car:
        try:
            car = car_dual_access(hexes_wgs, health, schools, city, n=N_DUAL_NONSUBSTITUTABLE)
            for col, vals in car.items():
                hexes[col] = vals
            for grade in ("A", "B", "C"):
                hexes[f"within_15_car_{grade}"] = np.isfinite(hexes[f"PT_car_{grade}"]) & (
                    hexes[f"PT_car_{grade}"] <= 15
                )
        except Exception as exc:
            print(f"car network routing skipped for {city.name}: {exc}", flush=True)

    utm = hexes.estimate_utm_crs()
    centre = boundary.to_crs(utm).geometry.unary_union.centroid
    hexes["t_centre"] = hexes.to_crs(utm).geometry.centroid.distance(centre) / WALK_M_PER_MIN

    m = city_metrics(hexes)
    m.update(
        {
            "city": city.name,
            "slug": city.slug,
            "health_n": int(len(health)),
            "school_n": int(len(schools)),
            "health_source": health_source,
            "school_source": school_source,
            "pop_source": pop_source,
            "boundary": "geoBoundaries ADM2 metro LGAs (GHS UC stand-in)",
            "mode": WALK_LABEL if walk_ok else "foot Euclidean 5 km/h (OSM walk failed)",
            "mode_eucl": "foot Euclidean 5 km/h (sensitivity)",
            "hex_side_m": HEX_SIDE_M,
            "n_dual": N_DUAL_NONSUBSTITUTABLE,
        }
    )
    if "PT_eucl" in hexes.columns:
        eu = city_metrics(hexes, pt_col="PT_eucl")
        m["PT_city_eucl"] = eu["PT_city"]
        m["F15_eucl"] = eu["F15"]
        m["Gini_eucl"] = eu["Gini_PT"]
    for grade in ("A", "B", "C"):
        col = f"PT_car_{grade}"
        if col in hexes.columns:
            cm = city_metrics(hexes, pt_col=col)
            m[f"PT_city_car_{grade}"] = cm["PT_city"]
            m[f"F15_car_{grade}"] = cm["F15"]
            m[f"Gini_car_{grade}"] = cm["Gini_PT"]
            m[f"car_{grade}"] = GRADE_LABELS[grade]

    gpkg = DATA_PROCESSED / f"{city.slug}_hexes.gpkg"
    hexes.to_file(gpkg, driver="GPKG")
    boundary.to_crs(4326).to_file(DATA_PROCESSED / f"{city.slug}_study_boundary.gpkg", driver="GPKG")
    metro_path = DATA_PROCESSED / f"{city.slug}_metro_lgas.gpkg"
    metro_lga_polygons(city).to_file(metro_path, driver="GPKG")
    embed_metro_lga_style(metro_path)
    health.to_file(DATA_PROCESSED / f"{city.slug}_health_points.gpkg", driver="GPKG")
    schools.to_file(DATA_PROCESSED / f"{city.slug}_school_points.gpkg", driver="GPKG")
    vintage = (
        f"{pop_source} · {health_source} · {school_source} · hex side {HEX_SIDE_M} m"
    )
    png = None
    if write_maps:
        png = framed_choropleth(
            hexes,
            "PT_k",
            title="Proximity time (health + education)",
            city_name=city.name,
            units="minutes",
            mode=f"{WALK_LABEL if walk_ok else 'foot Euclidean'} · n={N_DUAL_NONSUBSTITUTABLE}",
            vintage=vintage,
            boundary_def=m["boundary"],
            outfile=MAPS / f"{city.slug}_PT_k.png",
        )
        framed_choropleth(
            hexes,
            "pop",
            title="Population weight on 200 m hexes",
            city_name=city.name,
            units="people" if pop_raster else "hex count weight",
            mode=pop_source,
            vintage=vintage,
            boundary_def=m["boundary"],
            outfile=MAPS / f"{city.slug}_population.png",
        )
        framed_choropleth(
            hexes,
            "t_centre",
            title="Walk minutes to geometric centre",
            city_name=city.name,
            units="minutes",
            mode="grid check · not a service metric",
            vintage=vintage,
            boundary_def=m["boundary"],
            outfile=MAPS / f"{city.slug}_centre_minutes.png",
        )
    m["map_pt"] = str(png) if png else ""
    # Written here, not batched in run(): a later city dying must not discard this one.
    metrics_table([m]).to_csv(DATA_PROCESSED / f"{city.slug}_metrics.csv", index=False)
    return {"metrics": m, "hexes": hexes, "boundary": boundary, "health": health, "schools": schools}


def run(
    cities: list[str] | None = None,
    pop_layer: int = 2,
    write_maps: bool = False,
    try_hdx: bool = False,
    with_car: bool = False,
    reuse_hexes: bool = True,
) -> pd.DataFrame:
    keys = cities or list(CITIES)
    link_local_rasters()
    if try_hdx:
        ensure_inputs(
            [
                "geoboundaries_adm2",
                "grid3_health_v3",
                "grid3_schools",
                "hotosm_health",
                "hotosm_education",
                "cod_ab",
            ]
        )
    pop_raster = resolve_population_raster(pop_layer)
    rows = []
    for slug in keys:
        city = CITIES[slug]
        facilities = load_local_facilities(city)
        if try_hdx:
            facilities.update(load_facility_layers())
        result = analyse_city(
            city,
            facilities,
            pop_raster,
            pop_layer=pop_layer,
            write_maps=write_maps,
            with_car=with_car,
            reuse_hexes=reuse_hexes,
        )
        rows.append(result["metrics"])
        merge_city_metrics()
    return metrics_table(rows)


def merge_city_metrics() -> pd.DataFrame:
    """Rebuild city_metrics.csv from per-city files so single-city runs never clobber it."""
    frames = []
    for slug in CITIES:
        path = DATA_PROCESSED / f"{slug}_metrics.csv"
        if path.exists():
            frames.append(pd.read_csv(path))
    if not frames:
        return pd.DataFrame()
    table = pd.concat(frames, ignore_index=True)
    table.to_csv(DATA_PROCESSED / "city_metrics.csv", index=False)
    return table


if __name__ == "__main__":
    import sys

    print(run(sys.argv[1:] or None, write_maps=True).to_string(index=False))
