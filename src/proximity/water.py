"""Clip WPdx Nigeria water points to metro LGAs. Rural-biased; count before using in PT_k."""

from __future__ import annotations

import pandas as pd
import geopandas as gpd

from .cities import CITIES, City
from .download import DATASETS, ensure_inputs
from .paths import DATA_PROCESSED, DATA_RAW
from .pipeline import metro_lga_polygons


def _status_yes(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.lower()
    return s.isin({"yes", "y", "true", "1", "functional", "functioning"})


def load_wpdx() -> gpd.GeoDataFrame:
    ensure_inputs(["wpdx_nga", "geoboundaries_adm2"], skip_errors=False)
    path = DATA_RAW / DATASETS["wpdx_nga"]["filename"]
    df = pd.read_csv(path, low_memory=False)
    lon_col = next(c for c in ("lon_deg", "longitude", "lon") if c in df.columns)
    lat_col = next(c for c in ("lat_deg", "latitude", "lat") if c in df.columns)
    df = df[~df[lat_col].astype(str).str.startswith("#")]
    lon = pd.to_numeric(df[lon_col], errors="coerce")
    lat = pd.to_numeric(df[lat_col], errors="coerce")
    df = df.loc[lon.notna() & lat.notna()].copy()
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(lon.loc[df.index], lat.loc[df.index]),
        crs=4326,
    )
    if "status_id" in gdf.columns:
        gdf["functional"] = _status_yes(gdf["status_id"])
    elif "status_clean" in gdf.columns:
        gdf["functional"] = _status_yes(gdf["status_clean"])
    else:
        gdf["functional"] = False
    return gdf


def clip_wpdx_to_metro(city: City, wpdx: gpd.GeoDataFrame | None = None) -> gpd.GeoDataFrame:
    if wpdx is None:
        wpdx = load_wpdx()
    metro = metro_lga_polygons(city).to_crs(4326)
    west, south, east, north = city.bbox
    box = wpdx.cx[west:east, south:north]
    if box.empty:
        return box.iloc[0:0].copy()
    clipped = gpd.sjoin(box, metro[["geometry"]], predicate="within", how="inner")
    return clipped.drop(columns=[c for c in clipped.columns if c.startswith("index_")], errors="ignore")


def metro_wpdx_counts(write: bool = True) -> pd.DataFrame:
    wpdx = load_wpdx()
    rows = []
    for slug, city in CITIES.items():
        pts = clip_wpdx_to_metro(city, wpdx)
        n = int(len(pts))
        n_yes = int(pts["functional"].sum()) if n and "functional" in pts.columns else 0
        n_urban = 0
        if n and "is_urban" in pts.columns:
            urban = pts["is_urban"].astype(str).str.lower().isin({"true", "1", "yes"})
            n_urban = int(urban.sum())
        rows.append(
            {
                "city": city.name,
                "slug": slug,
                "n_wpdx": n,
                "n_functional": n_yes,
                "n_not_functional": n - n_yes,
                "n_urban_flag": n_urban,
                "citywide_n5_possible": n_yes >= 5,
            }
        )
        if write and n:
            out = DATA_PROCESSED / f"{slug}_wpdx_water.gpkg"
            cols = [
                c
                for c in (
                    "wpdx_id",
                    "status_id",
                    "status_clean",
                    "functional",
                    "water_source_clean",
                    "water_tech_clean",
                    "report_date",
                    "clean_adm1",
                    "clean_adm2",
                    "is_urban",
                    "geometry",
                )
                if c in pts.columns
            ]
            pts[cols].to_file(out, driver="GPKG")
    table = pd.DataFrame(rows)
    if write:
        table.to_csv(DATA_PROCESSED / "wpdx_metro_counts.csv", index=False)
    return table


if __name__ == "__main__":
    t = metro_wpdx_counts()
    print(t.to_string(index=False))
