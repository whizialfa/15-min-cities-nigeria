"""F15 on the Lagos-7 and Abuja-7 print clips. Headline scores stay the metro."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .cities import ABUJA_PLATE_WARDS, CITIES, LAGOS_PLATE_LGAS
from .metrics import city_metrics
from .paths import DATA_PROCESSED


def _hexes(slug: str) -> gpd.GeoDataFrame:
    return gpd.read_file(DATA_PROCESSED / f"{slug}_hexes.gpkg").to_crs(4326)


def _points(hexes: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    pts = hexes.copy()
    pts.geometry = pts.geometry.representative_point()
    return pts


def _service_f15(hexes: gpd.GeoDataFrame, col: str) -> float:
    if col not in hexes.columns:
        return float("nan")
    m = city_metrics(hexes, pt_col=col)
    return m["F15"]


def _row(city: str, cut: str, units: str, hexes: gpd.GeoDataFrame) -> dict:
    m = city_metrics(hexes)
    return {
        "city": city,
        "cut": cut,
        "units": units,
        "n_hex": m["n_hex"],
        "pop": m["pop_total"],
        "PT_city": m["PT_city"],
        "F15": m["F15"],
        "Gini_PT": m["Gini_PT"],
        "F15_health": _service_f15(hexes, "t_health"),
        "F15_schools": _service_f15(hexes, "t_school"),
    }


def lagos_cuts(hexes: gpd.GeoDataFrame | None = None) -> list[dict]:
    city = CITIES["lagos"]
    hexes = _hexes("lagos") if hexes is None else hexes.to_crs(4326)
    lgas = gpd.read_file(DATA_PROCESSED / "lagos_metro_lgas.gpkg", layer="lagos_metro_lgas").to_crs(4326)
    joined = gpd.sjoin(
        _points(hexes)[["geometry"]],
        lgas[["shapeName", "geometry"]],
        predicate="within",
        how="inner",
    )
    plate_ix = joined.index[joined["shapeName"].isin(LAGOS_PLATE_LGAS)].unique()
    rest_ix = joined.index[~joined["shapeName"].isin(LAGOS_PLATE_LGAS)].unique()
    n_plate = len(LAGOS_PLATE_LGAS)
    n_rest = len(set(joined.loc[rest_ix, "shapeName"])) if len(rest_ix) else 0
    return [
        _row(city.name, "plate", f"{n_plate} local government areas", hexes.loc[plate_ix]),
        _row(city.name, "omitted", f"{n_rest} local government areas", hexes.loc[rest_ix]),
        _row(city.name, "metro", "16 local government areas", hexes),
    ]


def abuja_cuts(hexes: gpd.GeoDataFrame | None = None) -> list[dict]:
    city = CITIES["abuja"]
    hexes = _hexes("abuja") if hexes is None else hexes.to_crs(4326)
    wards = gpd.read_file(DATA_PROCESSED / "abuja_wards.gpkg", layer="abuja_wards").to_crs(4326)
    joined = gpd.sjoin(
        _points(hexes)[["geometry"]],
        wards[["locator", "geometry"]],
        predicate="within",
        how="inner",
    )
    plate_ix = joined.index[joined["locator"].isin(ABUJA_PLATE_WARDS)].unique()
    rest_ix = joined.index[~joined["locator"].isin(ABUJA_PLATE_WARDS)].unique()
    n_plate = len(ABUJA_PLATE_WARDS)
    n_rest = len(set(joined.loc[rest_ix, "locator"])) if len(rest_ix) else 0
    return [
        _row(city.name, "plate", f"{n_plate} wards", hexes.loc[plate_ix]),
        _row(city.name, "omitted", f"{n_rest} wards", hexes.loc[rest_ix]),
        _row(city.name, "metro", "AMAC", hexes),
    ]


def build() -> pd.DataFrame:
    rows = lagos_cuts() + abuja_cuts()
    table = pd.DataFrame(rows)
    path = DATA_PROCESSED / "plate_metrics.csv"
    table.to_csv(path, index=False)
    return table


if __name__ == "__main__":
    print(build().to_string(index=False))
