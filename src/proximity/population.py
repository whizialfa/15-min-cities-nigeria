"""Local WorldPop / GRID3 rasters. Files stay outside git; we only symlink."""

from __future__ import annotations

import tempfile
from pathlib import Path

import geopandas as gpd

from .download import unzip_if_needed
from .paths import DATA_RAW

DOCUMENTS = Path.home() / "Documents"

# Optional comparison raster: WorldPop 2020 constrained 100 m (national).
# Stand-in until UN-adjusted unconstrained (`nga_ppp_2020_UNadj.tif`) is on disk.
LAYER1_NAME = "nga_ppp_2020_constrained.tif"
LAYER1_SOURCES = (
    DOCUMENTS / "GeoDev Lab" / "data" / "raw" / "fct_fetch" / LAYER1_NAME,
)

# Headline people layer: GRID3 Phase 2 / WorldPop bottom-up v3.0 (national, ~100 m).
LAYER2_NAME = "NGA_population_v3_0_gridded.tif"
LAYER2_SOURCES = (
    DATA_RAW / "NGA_population_v3_0_gridded" / LAYER2_NAME,
    DOCUMENTS / "Portfolio" / "Data" / "NGA_population_v3_0_gridded" / LAYER2_NAME,
)
LAYER2_LEGACY = (
    DATA_RAW / "NGA_population_v1_2_gridded.tif",
    DOCUMENTS / "Portfolio" / "Data" / "NGA_population_v1_2_gridded" / "NGA_population_v1_2_gridded.tif",
)

LAYER_LABELS = {
    1: "WorldPop 2020 constrained 100 m (national)",
    2: "GRID3 / WorldPop NGA population v3.0 100 m (UN WPP July 2025)",
}


def _first_existing(candidates: tuple[Path, ...]) -> Path | None:
    for path in candidates:
        if path.exists() and path.stat().st_size > 1000:
            return path
    return None


def _extract_nga_v3_zip(archive: Path) -> Path | None:
    out_dir = DATA_RAW / "NGA_population_v3_0_gridded"
    unzip_if_needed(archive, out_dir)
    hits = list(out_dir.rglob("*.tif"))
    if not hits:
        return None
    tif = next((p for p in hits if "gridded" in p.name.lower() and "uncert" not in p.name.lower()), hits[0])
    dest = DATA_RAW / LAYER2_NAME
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    dest.symlink_to(tif.resolve())
    return dest


def ensure_nga_v3() -> Path | None:
    """Use a local v3.0 tif, or unpack the WOPR zip if it is already in data/raw."""
    dest = DATA_RAW / LAYER2_NAME
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    found = _first_existing(LAYER2_SOURCES)
    if found is not None:
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        dest.symlink_to(found)
        return dest
    archive = DATA_RAW / "NGA_population_v3_0_gridded.zip"
    if archive.exists() and archive.stat().st_size > 1000:
        return _extract_nga_v3_zip(archive)
    return None


def link_local_rasters() -> dict[int, Path]:
    """Symlink known Documents copies into data/raw/. Does not copy bytes."""
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    linked: dict[int, Path] = {}
    for layer, name, sources in (
        (1, LAYER1_NAME, LAYER1_SOURCES),
        (2, LAYER2_NAME, LAYER2_SOURCES),
    ):
        dest = DATA_RAW / name
        src = _first_existing(sources)
        if src is None:
            if dest.exists() and dest.stat().st_size > 1000:
                linked[layer] = dest
            continue
        if dest.exists() and dest.resolve() == src.resolve():
            linked[layer] = dest
            continue
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        dest.symlink_to(src)
        linked[layer] = dest
    v3 = ensure_nga_v3()
    if v3 is not None:
        linked[2] = v3
    return linked


def resolve_population_raster(layer: int = 1) -> Path | None:
    """Prefer data/raw symlink, then the original Documents path."""
    if layer == 1:
        name, sources = LAYER1_NAME, LAYER1_SOURCES
        unadj = DATA_RAW / "nga_ppp_2020_UNadj.tif"
        if unadj.exists() and unadj.stat().st_size > 1000:
            return unadj
    elif layer == 2:
        v3 = ensure_nga_v3()
        if v3 is not None:
            return v3
        print("NGA population v3.0 not on disk; falling back to v1.2 if present")
        return _first_existing(LAYER2_LEGACY)
    else:
        raise ValueError(f"layer must be 1 or 2, got {layer}")
    dest = DATA_RAW / name
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    return _first_existing(sources)


def population_label(path: Path | None, layer: int = 1) -> str:
    if path is None:
        return "unweighted hexes (population raster not on disk)"
    if path.name == "nga_ppp_2020_UNadj.tif":
        return "WorldPop 2020 UN-adjusted 100 m"
    if "v1_2" in path.name:
        return "GRID3 / WorldPop NGA population v1.2 100 m (legacy fallback)"
    return LAYER_LABELS.get(layer, path.name)


def populate_hexes(hexes: gpd.GeoDataFrame, raster_path: Path, pop_col: str = "pop") -> gpd.GeoDataFrame:
    import rasterio
    from rasterio.windows import from_bounds
    from rasterstats import zonal_stats

    hex_wgs = hexes.to_crs(4326)
    minx, miny, maxx, maxy = hex_wgs.total_bounds
    with rasterio.open(raster_path) as src:
        nodata = src.nodata
        window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
        data = src.read(1, window=window, boundless=True)
        transform = src.window_transform(window)
        profile = src.profile.copy()
        profile.update(
            driver="GTiff",
            height=int(data.shape[0]),
            width=int(data.shape[1]),
            transform=transform,
            compress="lzw",
            tiled=False,
        )
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
            clip_path = tmp.name
        with rasterio.open(clip_path, "w", **profile) as dst:
            dst.write(data, 1)

    stats = zonal_stats(hex_wgs, clip_path, stats=["sum"], nodata=nodata, geojson_out=False)
    Path(clip_path).unlink(missing_ok=True)
    out = hexes.copy()
    out[pop_col] = [s["sum"] if s["sum"] is not None else 0.0 for s in stats]
    out.loc[out[pop_col] < 0, pop_col] = 0.0
    return out
