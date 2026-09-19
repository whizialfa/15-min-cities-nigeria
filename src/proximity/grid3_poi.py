"""GRID3 national POI layers from the ArcGIS feature services, cached under data/raw.

Markets and worship (churches + mosques merged) are extra-basket candidates beyond
health and schools. Police, fire and post offices are deliberately excluded: their
national counts are collection gaps, not censuses.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import geopandas as gpd
import pandas as pd

from .cities import CITIES, City
from .paths import DATA_PROCESSED, DATA_RAW
from .pipeline import metro_lga_polygons

SERVICE = "https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/{}/FeatureServer/0/query"
USER_AGENT = "15-min-cities-nigeria/0.1 (research adaptation; GRID3)"
PAGE = 2000

LAYERS: dict[str, str] = {
    "markets": "Markets_in_Nigeria",
    "churches": "Churches_in_Nigeria",
    "mosques": "Mosques_in_Nigeria",
}
WORSHIP = ("churches", "mosques")


def _get(url: str, timeout: int = 120) -> dict:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def fetch_layer(key: str, refresh: bool = False) -> Path:
    """Page a national GRID3 layer into data/raw/grid3_{key}.gpkg."""
    out = DATA_RAW / f"grid3_{key}.gpkg"
    if out.exists() and not refresh:
        return out
    url = SERVICE.format(LAYERS[key])
    frames, offset = [], 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": PAGE,
        }
        page = _get(f"{url}?{urlencode(params)}")
        feats = page.get("features") or []
        if not feats:
            break
        frames.append(gpd.GeoDataFrame.from_features(feats, crs=4326))
        offset += len(feats)
        print(f"  {key}: {offset} features", flush=True)
        if len(feats) < PAGE:
            break
        time.sleep(0.2)
    if not frames:
        raise RuntimeError(f"no features returned for {key}")
    gdf = pd.concat(frames, ignore_index=True)
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs=4326)
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
    gdf.to_file(out, driver="GPKG")
    return out


def load_layer(key: str) -> gpd.GeoDataFrame:
    return gpd.read_file(fetch_layer(key)).to_crs(4326)


def clip_to_metro(gdf: gpd.GeoDataFrame, city: City) -> gpd.GeoDataFrame:
    """Polygon clip to the metro LGA union — not a bounding box."""
    west, south, east, north = city.bbox
    box = gdf.cx[west:east, south:north]
    if box.empty:
        return box.copy()
    union = metro_lga_polygons(city).to_crs(4326).union_all()
    return box[box.geometry.within(union)].copy()


def city_category_points(city: City, cache: dict[str, gpd.GeoDataFrame]) -> dict[str, gpd.GeoDataFrame]:
    markets = clip_to_metro(cache["markets"], city)
    worship = pd.concat(
        [clip_to_metro(cache[k], city).assign(worship_type=k) for k in WORSHIP],
        ignore_index=True,
    )
    worship = gpd.GeoDataFrame(worship, geometry="geometry", crs=4326)
    return {"markets": markets, "worship": worship}


def write_city_points(slug: str, cache: dict[str, gpd.GeoDataFrame]) -> dict[str, int]:
    city = CITIES[slug]
    counts = {}
    for name, pts in city_category_points(city, cache).items():
        counts[name] = int(len(pts))
        if len(pts):
            keep = [c for c in ("name", "alt_name", "wardname", "lganame", "statename",
                                "water_typ", "worship_type", "source", "geometry") if c in pts.columns]
            pts[keep].to_file(DATA_PROCESSED / f"{slug}_{name}_points.gpkg", driver="GPKG")
    return counts


def build(slugs: list[str] | None = None) -> pd.DataFrame:
    cache = {key: load_layer(key) for key in LAYERS}
    for key, gdf in cache.items():
        print(f"{key:<10} national {len(gdf):>6}", flush=True)
    rows = []
    for slug in slugs or list(CITIES):
        counts = write_city_points(slug, cache)
        rows.append({"city": CITIES[slug].name, "slug": slug, **counts})
    table = pd.DataFrame(rows)
    table.to_csv(DATA_PROCESSED / "grid3_poi_metro_counts.csv", index=False)
    return table


def reach_report(slugs: list[str] | None = None, n: int = 5) -> pd.DataFrame:
    """Can hexes actually reach n of each category? Euclidean = optimistic upper bound."""
    import numpy as np

    from .access import mean_time_to_n

    cache = {key: load_layer(key) for key in LAYERS}
    rows = []
    for slug in slugs or list(CITIES):
        city = CITIES[slug]
        hex_path = DATA_PROCESSED / f"{slug}_hexes.gpkg"
        if not hex_path.exists():
            continue
        hexes = gpd.read_file(hex_path).to_crs(4326)
        pop = hexes["pop"].fillna(0).to_numpy(dtype=float) if "pop" in hexes else np.ones(len(hexes))
        for name, pts in city_category_points(city, cache).items():
            minutes, k_found = mean_time_to_n(hexes, pts, n=n)
            reachable = np.isfinite(minutes) & (k_found >= n)
            within = reachable & (minutes <= 15)
            rows.append(
                {
                    "city": city.name,
                    "category": name,
                    "n_points": int(len(pts)),
                    "k_available": int(k_found.max()) if len(k_found) else 0,
                    "median_min": float(np.nanmedian(minutes)) if reachable.any() else float("nan"),
                    "F15_eucl": float(pop[within].sum() / pop.sum()) if pop.sum() else float("nan"),
                    "pop_share_unreached": float(pop[~reachable].sum() / pop.sum()) if pop.sum() else float("nan"),
                }
            )
    table = pd.DataFrame(rows)
    table.to_csv(DATA_PROCESSED / "grid3_poi_reach.csv", index=False)
    return table


if __name__ == "__main__":
    import sys

    if "--reach" in sys.argv:
        print(reach_report().to_string(index=False))
    else:
        print(build().to_string(index=False))
