"""Overture Maps places — everyday food retail and pharmacies, merged with GRID3.

GRID3 counts *formal marketplaces* (big, lumpy, few). Overture counts *shops* (small,
many). They answer different questions, so they are typed, deduplicated, and reported
both merged and separately:

- `food` = GRID3 markets + Overture food retail, Overture points within DEDUPE_M of a
  GRID3 market dropped as the same place counted twice.
- `pharmacy` = Overture only; GRID3 has no chemist layer.

Overture is CDLA-Permissive with per-record source attribution, so unlike Google Places
the points can ship with the repo and the pipeline stays reproducible.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from .cities import CITIES, City
from .grid3_poi import clip_to_metro, load_layer
from .paths import DATA_PROCESSED, DATA_RAW

RELEASE = "2026-07-22.0"
S3_PLACES = (
    f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*.parquet"
)

# Daily food shopping. Restaurants, delivery services and anything matching "marketing"
# are deliberately out — a text filter on "market" sweeps in marketing agencies.
FOOD_CATEGORIES = (
    "grocery_store",
    "supermarket",
    "convenience_store",
    "farmers_market",
    "organic_grocery_store",
    "specialty_grocery_store",
    "butcher_shop",
    "flea_market",
)
PHARMACY_CATEGORIES = ("pharmacy",)
MARKET_LIKE = ("farmers_market", "flea_market")

NIGERIA_BBOX = (2.6, 4.2, 14.7, 13.9)
DEDUPE_M = 150.0


def _cache(name: str) -> Path:
    return DATA_RAW / f"overture_{name}.gpkg"


def fetch_places(name: str, categories: tuple[str, ...], refresh: bool = False) -> Path:
    """Pull one national category set into data/raw. Point geometry lives in bbox."""
    out = _cache(name)
    if out.exists() and not refresh:
        return out
    import duckdb

    west, south, east, north = NIGERIA_BBOX
    quoted = ",".join(f"'{c}'" for c in categories)
    con = duckdb.connect()
    con.execute("LOAD httpfs; SET s3_region='us-west-2';")
    df = con.execute(
        f"""
        SELECT id,
               names.primary AS name,
               categories.primary AS category,
               confidence,
               bbox.xmin AS lon,
               bbox.ymin AS lat
        FROM read_parquet('{S3_PLACES}')
        WHERE bbox.xmin BETWEEN {west} AND {east}
          AND bbox.ymin BETWEEN {south} AND {north}
          AND categories.primary IN ({quoted})
        """
    ).df()
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["lon", "lat"]),
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs=4326,
    )
    gdf.to_file(out, driver="GPKG")
    return out


def load_places(name: str, categories: tuple[str, ...]) -> gpd.GeoDataFrame:
    return gpd.read_file(fetch_places(name, categories)).to_crs(4326)


def dedupe_against_grid3(
    overture: gpd.GeoDataFrame, grid3_markets: gpd.GeoDataFrame, utm
) -> gpd.GeoDataFrame:
    """Drop Overture market-like points that sit on top of a GRID3 marketplace."""
    if overture.empty or grid3_markets.empty:
        return overture.assign(dup_of_grid3=False)
    market_like = overture["category"].isin(MARKET_LIKE)
    if not market_like.any():
        return overture.assign(dup_of_grid3=False)
    near = gpd.sjoin_nearest(
        overture[market_like].to_crs(utm),
        grid3_markets.to_crs(utm)[["geometry"]],
        max_distance=DEDUPE_M,
        how="inner",
    )
    overture = overture.assign(dup_of_grid3=False)
    overture.loc[overture.index.isin(near.index), "dup_of_grid3"] = True
    return overture


def city_food_and_pharmacy(city: City, cache: dict) -> dict[str, gpd.GeoDataFrame]:
    markets = clip_to_metro(cache["grid3_markets"], city)
    food_o = clip_to_metro(cache["food"], city)
    pharm = clip_to_metro(cache["pharmacy"], city)

    utm = markets.estimate_utm_crs() if len(markets) else food_o.estimate_utm_crs()
    food_o = dedupe_against_grid3(food_o, markets, utm)
    kept = food_o[~food_o["dup_of_grid3"]].copy()

    markets = markets.assign(source="grid3_market", category="marketplace")
    kept = kept.assign(source="overture")
    food = pd.concat(
        [markets[["source", "category", "geometry"]], kept[["source", "category", "name", "geometry"]]],
        ignore_index=True,
    )
    return {
        "food": gpd.GeoDataFrame(food, geometry="geometry", crs=4326),
        "pharmacy": pharm.assign(source="overture"),
        "_dupes": int(food_o["dup_of_grid3"].sum()),
        "_grid3": int(len(markets)),
        "_overture": int(len(kept)),
    }


def build(slugs: list[str] | None = None, n: int = 5) -> pd.DataFrame:
    import numpy as np

    from .access import mean_time_to_n

    cache = {
        "grid3_markets": load_layer("markets"),
        "food": load_places("food_retail", FOOD_CATEGORIES),
        "pharmacy": load_places("pharmacy", PHARMACY_CATEGORIES),
    }
    rows = []
    for slug in slugs or list(CITIES):
        city = CITIES[slug]
        parts = city_food_and_pharmacy(city, cache)
        for name in ("food", "pharmacy"):
            pts = parts[name]
            if len(pts):
                pts.to_file(DATA_PROCESSED / f"{slug}_{name}_points.gpkg", driver="GPKG")
        hex_path = DATA_PROCESSED / f"{slug}_hexes.gpkg"
        row = {
            "city": city.name,
            "grid3_markets": parts["_grid3"],
            "overture_food": parts["_overture"],
            "dupes_dropped": parts["_dupes"],
            "food_total": int(len(parts["food"])),
            "pharmacy": int(len(parts["pharmacy"])),
        }
        if hex_path.exists():
            hexes = gpd.read_file(hex_path).to_crs(4326)
            pop = hexes["pop"].fillna(0).to_numpy(dtype=float)
            for name in ("food", "pharmacy"):
                minutes, _ = mean_time_to_n(hexes, parts[name], n=n)
                ok = np.isfinite(minutes)
                row[f"{name}_median_min"] = float(np.nanmedian(minutes)) if ok.any() else float("nan")
                row[f"{name}_F15"] = float(pop[ok & (minutes <= 15)].sum() / pop.sum())
        rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(DATA_PROCESSED / "overture_grid3_food_reach.csv", index=False)
    return table


if __name__ == "__main__":
    print(build().to_string(index=False))
