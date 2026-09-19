"""Local GRID3 / HOT OSM facility files under Documents. Not committed."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from .cities import City
from .paths import DATA_RAW

DOCUMENTS = Path.home() / "Documents"

# v3 is operational (24 states). Lagos and Rivers are only in v2.
LOCAL_FILES: dict[str, tuple[Path, ...]] = {
    "grid3_health_v3": (
        DOCUMENTS / "GeoDev Lab" / "data" / "raw" / "fct_fetch" / "grid3_nga_health_facilities_v3_0.gpkg",
    ),
    "grid3_health_v2": (
        DOCUMENTS
        / "Portfolio"
        / "Projects"
        / "Healthcare Demand Pressure"
        / "GRID3_NGA_health_facilities_v2_0_-7782622226219335882"
        / "GRID3_NGA_health_facilities_v2_0.shp",
    ),
    "grid3_schools": (
        DOCUMENTS
        / "Portfolio"
        / "Data"
        / "Schools_in_Nigeria_7578708651186362965"
        / "grid3_nga_poi_school.shp",
    ),
    "hotosm_education": (
        DOCUMENTS
        / "Portfolio"
        / "Data"
        / "hotosm_nga_education_facilities_points_shp"
        / "hotosm_nga_education_facilities_points_shp.shp",
    ),
}

STATE_ALIASES: dict[str, tuple[str, ...]] = {
    "Federal Capital Territory": ("federal capital territory", "fct", "abuja"),
}

STATE_COLUMNS = ("state_standard", "state_name", "statename", "state")


def _as_points(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    if gdf.geom_type.isin(["Polygon", "MultiPolygon"]).any():
        gdf = gdf.copy()
        gdf.geometry = gdf.geometry.centroid
    return gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()


def filter_state(gdf: gpd.GeoDataFrame, city: City) -> gpd.GeoDataFrame:
    col = next((c for c in STATE_COLUMNS if c in gdf.columns), None)
    if col is None:
        return gdf
    needles = STATE_ALIASES.get(city.state, (city.state.lower(),))
    series = gdf[col].astype(str).str.lower()
    mask = False
    for needle in needles:
        mask = mask | series.str.contains(needle, case=False, na=False, regex=False)
    return gdf[mask].copy()


def link_local_facilities() -> dict[str, Path]:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    linked: dict[str, Path] = {}
    for key, sources in LOCAL_FILES.items():
        src = next((p for p in sources if p.exists() and p.stat().st_size > 200), None)
        if src is None:
            continue
        dest = DATA_RAW / src.name
        if dest.is_symlink() or dest.exists():
            if dest.resolve() != src.resolve():
                dest.unlink()
                dest.symlink_to(src)
        else:
            dest.symlink_to(src)
        if src.suffix == ".shp":
            for ext in (".dbf", ".shx", ".prj", ".cpg"):
                side = src.with_suffix(ext)
                side_dest = dest.with_suffix(ext)
                if side.exists() and not side_dest.exists():
                    side_dest.symlink_to(side)
        linked[key] = dest
    return linked


def load_local_facilities(city: City | None = None) -> dict[str, gpd.GeoDataFrame]:
    link_local_facilities()
    if city is None:
        bbox = (2.5, 4.0, 15.0, 14.0)
    else:
        west, south, east, north = city.bbox
        pad = 0.05
        bbox = (west - pad, south - pad, east + pad, north + pad)
    out: dict[str, gpd.GeoDataFrame] = {}
    mapping = {
        "grid3_health_v3": "health_grid3_v3",
        "grid3_health_v2": "health_grid3_v2",
        "grid3_schools": "education_grid3",
        "hotosm_education": "education_osm",
    }
    for key, kind in mapping.items():
        src = next((p for p in LOCAL_FILES[key] if p.exists()), None)
        if src is None:
            continue
        try:
            gdf = gpd.read_file(src, bbox=bbox)
            out[kind] = _as_points(gdf)
        except Exception as exc:
            print(f"could not read {key}: {exc}")
    return out


def clip_to_city(gdf: gpd.GeoDataFrame, city: City) -> gpd.GeoDataFrame:
    west, south, east, north = city.bbox
    return gdf.cx[west:east, south:north].copy()
