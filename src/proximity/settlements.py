"""Named settlement points inside each study outline.

GRID3 settlement names (eHealth Africa / GRID3, 2021) clipped to
`{slug}_study_boundary.gpkg`. OSM `place=town|village|hamlet|locality` fills
names GRID3 missed. Points only. Not drawn on print plates. Nearest name is
attached to web-map hex and ward popups.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .cities import ABUJA_PLATE_WARDS, CITIES, LAGOS_PLATE_LGAS, City
from .overpass import VILLAGE_RANKS, fetch_villages
from .paths import DATA_PROCESSED, DATA_RAW, WEB_DATA
from .wards import PLACEHOLDER_LOOSE, settlement_gpkg, tidy_label

DEDUP_M = 250
OSM_MATCH_M = 400
NEAR_HEX_M = 3000
WARD_NAME_CAP = 8
OSM_NOISE = re.compile(
    r"\b(?:church|mosque|school|market|mall|hotel|plaza|clinic|hospital|"
    r"university|campus|junction|bus stop|filling|petrol|bridge|substation|"
    r"roundabout|apartments?|quarters?)\b",
    re.I,
)
CSV_COLS = (
    "city",
    "slug",
    "name",
    "alt_name",
    "kind",
    "source",
    "ward",
    "lga",
    "state",
    "is_primary",
    "in_plate",
    "lon",
    "lat",
)


def ensure_grid3_gpkg() -> Path:
    gpkg = DATA_RAW / "grid3_nga_settlementpt.gpkg"
    if gpkg.exists():
        return gpkg
    shp = settlement_gpkg()
    if shp.suffix == ".gpkg":
        return shp
    cmd = [
        "ogr2ogr",
        "-f",
        "GPKG",
        str(gpkg),
        str(shp),
        "-nln",
        "settlements",
        "-select",
        "set_name,set_altnam,is_primary,wardname,lganame,statename,source,set_id,uniq_id",
        "-lco",
        "SPATIAL_INDEX=YES",
        "-nlt",
        "POINT",
        "-a_srs",
        "EPSG:4326",
    ]
    subprocess.run(cmd, check=True)
    return gpkg


def _read_bbox(city: City) -> gpd.GeoDataFrame:
    """ogr2ogr spatial filter: geopandas bbox on the 44 MB national file is slow."""
    gpkg = ensure_grid3_gpkg()
    west, south, east, north = city.bbox
    pad = 0.05
    dest = DATA_PROCESSED / f"{city.slug}_grid3_bbox.gpkg"
    if dest.exists():
        dest.unlink()
    subprocess.run(
        [
            "ogr2ogr",
            "-f",
            "GPKG",
            str(dest),
            str(gpkg),
            "-spat",
            str(west - pad),
            str(south - pad),
            str(east + pad),
            str(north + pad),
            "-nln",
            "s",
        ],
        check=True,
    )
    gdf = gpd.read_file(dest)
    dest.unlink(missing_ok=True)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326)


def _study_union(slug: str):
    path = DATA_PROCESSED / f"{slug}_study_boundary.gpkg"
    if not path.exists():
        return None
    bound = gpd.read_file(path).to_crs(4326)
    if bound.empty:
        return None
    return bound.union_all()


def _plate_union(slug: str):
    if slug == "lagos":
        path = DATA_PROCESSED / f"{slug}_metro_lgas.gpkg"
        if path.exists():
            lgas = gpd.read_file(path).to_crs(4326)
            field = "shapeName" if "shapeName" in lgas.columns else "lganame"
            sub = lgas[lgas[field].isin(LAGOS_PLATE_LGAS)]
            if not sub.empty:
                return sub.union_all()
    if slug == "abuja":
        path = DATA_PROCESSED / f"{slug}_wards.gpkg"
        if path.exists():
            wards = gpd.read_file(path).to_crs(4326)
            if "locator" in wards.columns:
                sub = wards[wards["locator"].isin(ABUJA_PLATE_WARDS)]
                if not sub.empty:
                    return sub.union_all()
    return _study_union(slug)


def _clip(gdf: gpd.GeoDataFrame, union) -> gpd.GeoDataFrame:
    if gdf.empty or union is None:
        return gdf.iloc[0:0].copy() if gdf.empty else gdf
    return gdf[gdf.geometry.within(union) | gdf.geometry.intersects(union)].copy()


def _usable_name(name: object) -> bool:
    raw = str(name or "").strip()
    if len(raw) < 2:
        return False
    return not PLACEHOLDER_LOOSE.match(raw)


def _grid3_rows(city: City, union) -> gpd.GeoDataFrame:
    raw = _read_bbox(city)
    if raw.empty:
        return gpd.GeoDataFrame(columns=["name", "alt_name", "kind", "source", "is_primary", "geometry"], crs=4326)
    raw = _clip(raw, union)
    if raw.empty:
        return raw
    names = raw["set_name"].map(tidy_label) if "set_name" in raw.columns else pd.Series([""] * len(raw))
    keep = names.map(_usable_name)
    gdf = raw.loc[keep].copy()
    gdf["name"] = names.loc[keep].values
    alt = gdf["set_altnam"] if "set_altnam" in gdf.columns else ""
    gdf["alt_name"] = pd.Series(alt, index=gdf.index).fillna("").astype(str).str.strip()
    prim = gdf["is_primary"] if "is_primary" in gdf.columns else ""
    gdf["is_primary"] = pd.Series(prim, index=gdf.index).astype(str).str.lower().eq("yes").astype(int)
    gdf["kind"] = "settlement"
    gdf["source"] = "grid3"
    gdf["state"] = gdf["statename"].astype(str).map(tidy_label) if "statename" in gdf.columns else ""
    gdf["grid3_ward"] = gdf["wardname"].astype(str) if "wardname" in gdf.columns else ""
    gdf["grid3_lga"] = gdf["lganame"].astype(str) if "lganame" in gdf.columns else ""
    return gdf[
        ["name", "alt_name", "kind", "source", "is_primary", "state", "grid3_ward", "grid3_lga", "geometry"]
    ].reset_index(drop=True)


def _osm_cache(slug: str) -> Path:
    return DATA_RAW / f"{slug}_osm_villages.geojson"


def _osm_from_file(path: Path) -> gpd.GeoDataFrame:
    if not path.exists():
        return gpd.GeoDataFrame(columns=["osm_id", "place", "name", "geometry"], crs=4326)
    gdf = gpd.read_file(path)
    if gdf.empty:
        return gdf
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    ranks = {r.casefold() for r in VILLAGE_RANKS}
    if "place" in gdf.columns:
        gdf = gdf[gdf["place"].astype(str).str.casefold().isin(ranks)].copy()
    return gdf


def _osm_rows(city: City, union, *, refresh: bool) -> gpd.GeoDataFrame:
    frames = []
    districts = DATA_RAW / f"{city.slug}_osm_places.geojson"
    extra = _osm_from_file(districts)
    if extra is not None and not extra.empty:
        frames.append(extra)
    cache = _osm_cache(city.slug)
    if cache.exists() and not refresh:
        cached = _osm_from_file(cache)
        if not cached.empty:
            frames.append(cached)
    else:
        try:
            fetched = fetch_villages(city)
        except Exception as exc:
            print(f"{city.slug} OSM villages failed: {exc}", flush=True)
            fetched = gpd.GeoDataFrame(columns=["osm_id", "place", "name", "geometry"], crs=4326)
        if fetched is not None and not fetched.empty:
            fetched.to_file(cache, driver="GeoJSON")
            frames.append(fetched)
        elif cache.exists():
            frames.append(_osm_from_file(cache))
    if not frames:
        return gpd.GeoDataFrame(columns=["name", "alt_name", "kind", "source", "is_primary", "geometry"], crs=4326)
    gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=4326)
    gdf = _clip(gdf, union)
    if gdf.empty:
        return gdf
    gdf["name"] = gdf["name"].map(tidy_label)
    keep = [
        _usable_name(n)
        and not OSM_NOISE.search(str(n))
        and str(n).casefold() not in {city.name.casefold(), "nigeria", "fct"}
        for n in gdf["name"]
    ]
    gdf = gdf.loc[keep].copy()
    if gdf.empty:
        return gdf
    gdf["alt_name"] = ""
    gdf["kind"] = gdf["place"].astype(str).str.lower() if "place" in gdf.columns else "village"
    gdf["source"] = "osm"
    gdf["is_primary"] = 0
    gdf["state"] = city.state
    gdf["grid3_ward"] = ""
    gdf["grid3_lga"] = ""
    return gdf[
        ["name", "alt_name", "kind", "source", "is_primary", "state", "grid3_ward", "grid3_lga", "geometry"]
    ].reset_index(drop=True)


def _dedup(gdf: gpd.GeoDataFrame, metres: float) -> gpd.GeoDataFrame:
    if gdf.empty or len(gdf) == 1:
        return gdf
    utm = gdf.estimate_utm_crs()
    work = gdf.to_crs(utm).copy()
    work["_key"] = work["name"].astype(str).str.casefold()
    work["_rank"] = work["source"].map({"grid3": 0, "osm": 1}).fillna(2)
    work = work.sort_values(["_rank", "is_primary"], ascending=[True, False])
    keep_idx: list = []
    for _, chunk in work.groupby("_key", sort=False):
        kept = []
        for idx, row in chunk.iterrows():
            if any(row.geometry.distance(prev) <= metres for prev in kept):
                continue
            keep_idx.append(idx)
            kept.append(row.geometry)
    out = work.loc[keep_idx].drop(columns=["_key", "_rank"]).to_crs(4326)
    return out.reset_index(drop=True)


def _join_wards(city: City, pts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    pts = pts.copy()
    pts["ward"] = ""
    pts["lga"] = ""
    path = DATA_PROCESSED / f"{city.slug}_wards.gpkg"
    if pts.empty or not path.exists():
        if "grid3_ward" in pts.columns:
            pts["ward"] = pts["grid3_ward"].map(tidy_label)
        if "grid3_lga" in pts.columns:
            pts["lga"] = pts["grid3_lga"].map(tidy_label)
        return pts
    wards = gpd.read_file(path).to_crs(4326)
    keep = [c for c in ("locator", "lganame", "geometry") if c in wards.columns]
    if "locator" not in keep:
        return pts
    joined = gpd.sjoin(pts, wards[keep], predicate="within", how="left")
    joined = joined[~joined.index.duplicated(keep="first")]
    pts["ward"] = joined.reindex(pts.index)["locator"].fillna("").astype(str).map(tidy_label).values
    if "lganame" in joined.columns:
        pts["lga"] = joined.reindex(pts.index)["lganame"].fillna("").astype(str).map(tidy_label).values
    miss = pts["ward"].eq("")
    if miss.any() and "grid3_ward" in pts.columns:
        pts.loc[miss, "ward"] = pts.loc[miss, "grid3_ward"].map(tidy_label)
    miss_lga = pts["lga"].eq("")
    if miss_lga.any() and "grid3_lga" in pts.columns:
        pts.loc[miss_lga, "lga"] = pts.loc[miss_lga, "grid3_lga"].map(tidy_label)
    return pts


def _flag_plate(slug: str, pts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    pts = pts.copy()
    mask = _plate_union(slug)
    if mask is None or pts.empty:
        pts["in_plate"] = 1
        return pts
    poly = gpd.GeoDataFrame({"geometry": [mask]}, crs=4326)
    hit = gpd.sjoin(pts[["geometry"]], poly, predicate="within", how="left")
    hit = hit[~hit.index.duplicated(keep="first")]
    pts["in_plate"] = hit.reindex(pts.index)["index_right"].notna().astype(int).values
    return pts


def city_settlements(city: City, *, refresh_osm: bool = False) -> gpd.GeoDataFrame:
    union = _study_union(city.slug)
    if union is None:
        raise FileNotFoundError(f"{city.slug}_study_boundary.gpkg missing")
    grid3 = _grid3_rows(city, union)
    osm = _osm_rows(city, union, refresh=refresh_osm)
    frames = [f for f in (grid3, osm) if f is not None and not f.empty]
    if not frames:
        return gpd.GeoDataFrame(columns=list(CSV_COLS) + ["geometry"], crs=4326)
    gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=4326)
    gdf = _dedup(gdf, DEDUP_M)
    gdf = _join_wards(city, gdf)
    gdf = _flag_plate(city.slug, gdf)
    gdf["city"] = city.name
    gdf["slug"] = city.slug
    gdf["lon"] = gdf.geometry.x.round(6)
    gdf["lat"] = gdf.geometry.y.round(6)
    gdf["alt_name"] = gdf["alt_name"].fillna("").astype(str)
    gdf["kind"] = gdf["kind"].fillna("settlement").astype(str)
    gdf["source"] = gdf["source"].fillna("grid3").astype(str)
    gdf["state"] = gdf["state"].fillna("").astype(str)
    gdf["is_primary"] = pd.to_numeric(gdf["is_primary"], errors="coerce").fillna(0).astype(int)
    gdf["in_plate"] = pd.to_numeric(gdf["in_plate"], errors="coerce").fillna(0).astype(int)
    gdf = gdf.sort_values(["in_plate", "is_primary", "name"], ascending=[False, False, True]).reset_index(drop=True)
    keep = [c for c in CSV_COLS if c in gdf.columns] + ["geometry"]
    return gdf[keep]


def load_city(slug: str) -> gpd.GeoDataFrame | None:
    path = DATA_PROCESSED / f"{slug}_settlements.gpkg"
    if not path.exists():
        return None
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326)


def _as_table(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    cols = [c for c in CSV_COLS if c in gdf.columns]
    return pd.DataFrame(gdf[cols])


def write_city(city: City, *, refresh_osm: bool = False) -> gpd.GeoDataFrame:
    gdf = city_settlements(city, refresh_osm=refresh_osm)
    gpkg = DATA_PROCESSED / f"{city.slug}_settlements.gpkg"
    csv = DATA_PROCESSED / f"{city.slug}_settlements.csv"
    if gdf.empty:
        empty = gpd.GeoDataFrame(columns=list(CSV_COLS) + ["geometry"], crs=4326)
        empty.to_file(gpkg, driver="GPKG")
        pd.DataFrame(columns=CSV_COLS).to_csv(csv, index=False)
        print(f"{city.slug:<15} 0 settlements", flush=True)
        return empty
    gdf.to_file(gpkg, driver="GPKG")
    _as_table(gdf).to_csv(csv, index=False)
    n_grid3 = int((gdf["source"] == "grid3").sum())
    n_osm = int((gdf["source"] == "osm").sum())
    n_plate = int(gdf["in_plate"].sum())
    print(
        f"{city.slug:<15} {len(gdf):>5} settlements  grid3={n_grid3} osm={n_osm} on_plate={n_plate}",
        flush=True,
    )
    return gdf


def format_ward_places(names: list[str], cap: int = WARD_NAME_CAP) -> str:
    seen: list[str] = []
    for name in names:
        text = str(name or "").strip()
        if not text or text.casefold() in {s.casefold() for s in seen}:
            continue
        seen.append(text)
    if not seen:
        return ""
    if len(seen) <= cap:
        return ", ".join(seen)
    return ", ".join(seen[:cap]) + f" and {len(seen) - cap} others"


def attach_to_hexes(hexes: gpd.GeoDataFrame, settlements: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame:
    out = hexes.copy()
    out["place"] = ""
    out["place_m"] = None
    if settlements is None or settlements.empty or out.empty:
        return out
    utm = out.estimate_utm_crs()
    pts = out.to_crs(utm).copy()
    pts.geometry = pts.geometry.representative_point()
    named = settlements[settlements["name"].astype(str).str.strip().ne("")].to_crs(utm)
    if named.empty:
        return out
    joined = gpd.sjoin_nearest(
        pts[["geometry"]],
        named[["name", "geometry"]],
        how="left",
        max_distance=NEAR_HEX_M,
        distance_col="place_m",
    )
    joined = joined[~joined.index.duplicated(keep="first")]
    out["place"] = joined.reindex(out.index)["name"].fillna("").astype(str).values
    metres = pd.to_numeric(joined.reindex(out.index)["place_m"], errors="coerce")
    out["place_m"] = metres.round().astype("Int64")
    return out


def attach_to_wards(wards: gpd.GeoDataFrame, settlements: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame:
    out = wards.copy()
    out["places"] = ""
    out["place_n"] = 0
    if settlements is None or settlements.empty or out.empty:
        return out
    key = "locator" if "locator" in out.columns else ("name" if "name" in out.columns else None)
    if key is None:
        return out
    pts = settlements[settlements["name"].astype(str).str.strip().ne("")].copy()
    joined = gpd.sjoin(pts[["name", "is_primary", "geometry"]], out[[key, "geometry"]], predicate="within", how="inner")
    if joined.empty:
        return out
    joined = joined.sort_values(["is_primary", "name"], ascending=[False, True])
    grouped = joined.groupby(key)["name"].apply(lambda s: format_ward_places(list(s)))
    counts = joined.groupby(key).size()
    mapped = out[key].map(grouped).fillna("")
    out["places"] = mapped.values
    out["place_n"] = out[key].map(counts).fillna(0).astype(int).values
    return out


def build(slugs: list[str] | None = None, *, refresh_osm: bool = False) -> pd.DataFrame:
    keys = slugs or list(CITIES)
    frames = []
    for slug in keys:
        gdf = write_city(CITIES[slug], refresh_osm=refresh_osm)
        if not gdf.empty:
            frames.append(_as_table(gdf))
    if not frames:
        table = pd.DataFrame(columns=CSV_COLS)
    else:
        table = pd.concat(frames, ignore_index=True)
    table.to_csv(DATA_PROCESSED / "settlements.csv", index=False)
    summary = (
        table.groupby(["slug", "city"], dropna=False)
        .agg(
            n=("name", "size"),
            n_grid3=("source", lambda s: int((s == "grid3").sum())),
            n_osm=("source", lambda s: int((s == "osm").sum())),
            n_plate=("in_plate", "sum"),
        )
        .reset_index()
    )
    summary.to_csv(DATA_PROCESSED / "settlements_summary.csv", index=False)
    return table


def export_web_points(slug: str, gdf: gpd.GeoDataFrame | None = None) -> Path | None:
    """Write points into the city web folder. The map does not draw this layer."""
    if gdf is None:
        gdf = load_city(slug)
    if gdf is None or gdf.empty:
        return None
    from .web_map import _write_fc

    out = WEB_DATA / "cities" / slug / "settlements.geojson"
    _write_fc(
        gdf,
        out,
        ["name", "alt_name", "kind", "source", "ward", "lga", "is_primary", "in_plate"],
    )
    return out


if __name__ == "__main__":
    import sys

    from .timing import done, start

    args = [a for a in sys.argv[1:] if a != "--refresh-osm"]
    refresh = "--refresh-osm" in sys.argv[1:]
    t0 = start("settlement inventory", "GRID3 points plus OSM villages, clipped to study outlines")
    table = build(args or None, refresh_osm=refresh)
    note = table.groupby("slug").size().to_string() if not table.empty else "no settlements"
    print(note)
    done("settlement inventory", t0, note.replace("\n", "; "))
