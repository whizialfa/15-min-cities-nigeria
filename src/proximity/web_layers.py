"""Export simplified metro LGA GeoJSON for the story map in web/."""

from __future__ import annotations

import json

import pandas as pd
import geopandas as gpd
import numpy as np
from rasterio.mask import mask
from shapely.geometry import mapping

from .cities import CITIES
from .download import DATASETS
from .paths import DATA_RAW, WEB_DATA
from .population import link_local_rasters, resolve_population_raster

# Cameras are fit-to-bounds in the client; these are overview fallbacks.
OVERVIEW = {"center": [8.1, 9.2], "zoom": 5.35, "bearing": 0, "pitch": 0}


def _write_geojson(gdf: gpd.GeoDataFrame, path) -> None:
    payload = json.loads(gdf.to_json())
    payload.pop("crs", None)
    path.write_text(json.dumps(payload))


def _adm2() -> gpd.GeoDataFrame:
    path = DATA_RAW / DATASETS["geoboundaries_adm2"]["filename"]
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326)


def _city_lgas(adm: gpd.GeoDataFrame, slug: str) -> gpd.GeoDataFrame:
    city = CITIES[slug]
    west, south, east, north = city.bbox
    gdf = adm[adm["shapeName"].isin(city.metro_lgas)].cx[west:east, south:north].copy()
    if gdf.empty:
        raise RuntimeError(f"No LGAs for {slug}")
    gdf["city"] = city.name
    gdf["slug"] = slug
    gdf["lga"] = gdf["shapeName"]
    return gdf


def _zonal_pop(gdf: gpd.GeoDataFrame, raster_path) -> gpd.GeoDataFrame:
    import rasterio

    pops, dens, areas = [], [], []
    with rasterio.open(raster_path) as src:
        nodata = src.nodata
        utm = gdf.estimate_utm_crs()
        for geom in gdf.geometry:
            area_km2 = gpd.GeoSeries([geom], crs=4326).to_crs(utm).area.iloc[0] / 1e6
            try:
                data, _ = mask(src, [mapping(geom)], crop=True, nodata=nodata, filled=True)
            except ValueError:
                pops.append(0.0)
                dens.append(0.0)
                areas.append(float(area_km2))
                continue
            arr = data[0].astype("float64")
            if nodata is not None:
                arr[arr == nodata] = np.nan
            arr[arr < 0] = np.nan
            pop = float(np.nansum(arr))
            pops.append(pop)
            areas.append(float(area_km2))
            dens.append(pop / area_km2 if area_km2 > 0 else 0.0)
    out = gdf.copy()
    out["pop"] = np.round(pops).astype(int)
    out["area_km2"] = np.round(areas, 2)
    out["people_per_km2"] = np.round(dens).astype(int)
    return out


def export_story_layers() -> dict:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    link_local_rasters()
    adm = _adm2()
    raster = resolve_population_raster(2)
    parts = [_city_lgas(adm, slug) for slug in CITIES]
    lgas = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=4326)
    if raster is not None:
        lgas = _zonal_pop(lgas, raster)
    else:
        lgas["pop"] = 0
        lgas["area_km2"] = 0.0
        lgas["people_per_km2"] = 0

    lgas.geometry = lgas.simplify(0.0015, preserve_topology=True)
    keep = ["city", "slug", "lga", "pop", "area_km2", "people_per_km2", "geometry"]
    lgas = lgas[keep]

    lga_path = WEB_DATA / "metro_lgas.geojson"
    _write_geojson(lgas, lga_path)

    outlines = (
        lgas.dissolve(by="slug", as_index=False)
        .assign(geometry=lambda d: d.geometry.buffer(0).simplify(0.002, preserve_topology=True))
    )
    outlines["name"] = outlines["slug"].map(lambda s: CITIES[s].name)
    outline_path = WEB_DATA / "city_outlines.geojson"
    _write_geojson(outlines[["slug", "name", "geometry"]], outline_path)

    totals = {}
    for slug, city in CITIES.items():
        sub = lgas[lgas["slug"] == slug]
        totals[slug] = {
            "name": city.name,
            "state": city.state,
            "pop": int(sub["pop"].sum()),
            "area_km2": round(float(sub["area_km2"].sum()), 1),
            "people_per_km2": int(round(sub["pop"].sum() / sub["area_km2"].sum()))
            if sub["area_km2"].sum()
            else 0,
            "n_lga": int(len(sub)),
            "atlas_id": city.atlas_id,
            "notes": city.notes,
            "bbox": list(city.bbox),
        }

    meta = {
        "population": "WorldPop 2020 constrained 100 m, zonal sum on metro LGAs",
        "boundary": "geoBoundaries ADM2 metro LGAs (not GHS Urban Centre)",
        "overview": OVERVIEW,
        "cities": totals,
    }
    meta_path = WEB_DATA / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    return {"lgas": lga_path, "outlines": outline_path, "meta": meta_path, "n": len(lgas)}


if __name__ == "__main__":
    print(export_story_layers())
