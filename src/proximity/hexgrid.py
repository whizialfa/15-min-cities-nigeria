"""200 m side hexagonal grid (same geometry as Bruno et al. 2024)."""

from __future__ import annotations

import math

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .cities import HEX_SIDE_M, POP_URBAN_THRESHOLD, City


def hexagon(cx: float, cy: float, side: float) -> Polygon:
    """Pointy-top hexagon centred at (cx, cy)."""
    angles = np.deg2rad(np.arange(30, 360, 60))
    return Polygon([(cx + side * math.cos(a), cy + side * math.sin(a)) for a in angles])


def hex_grid(boundary: gpd.GeoDataFrame, side_m: float = HEX_SIDE_M) -> gpd.GeoDataFrame:
    """Fill `boundary` (any CRS) with hexes of side `side_m` metres."""
    utm = boundary.estimate_utm_crs()
    geom = unary_union(boundary.to_crs(utm).geometry)
    minx, miny, maxx, maxy = geom.bounds
    w = math.sqrt(3) * side_m
    h = 1.5 * side_m
    hexes = []
    row = 0
    y = miny - side_m
    while y <= maxy + side_m:
        x = minx - w + (0.5 * w if row % 2 else 0.0)
        while x <= maxx + w:
            poly = hexagon(x, y, side_m)
            if poly.intersects(geom):
                hexes.append(poly)
            x += w
        y += h
        row += 1
    gdf = gpd.GeoDataFrame({"hex_id": np.arange(len(hexes))}, geometry=hexes, crs=utm)
    return gdf.loc[gdf.intersects(geom)].copy()


def urban_mask_from_population(
    city: City,
    pop_raster,
    threshold: float = POP_URBAN_THRESHOLD,
) -> gpd.GeoDataFrame:
    """Largest blob of WorldPop cells above `threshold` inside the city bbox.

    Stand-in for GHS Urban Centre until the UCDB polygons are cached locally.
    """
    import rasterio
    from rasterio.features import shapes
    from shapely.geometry import shape

    west, south, east, north = city.bbox
    with rasterio.open(pop_raster) as src:
        window = rasterio.windows.from_bounds(west, south, east, north, transform=src.transform)
        data = src.read(1, window=window, boundless=True, filled=True)
        transform = src.window_transform(window)
        nodata = src.nodata
        crs = src.crs
    arr = np.array(data, dtype=float)
    if nodata is not None:
        arr[arr == nodata] = np.nan
    mask = np.isfinite(arr) & (arr >= threshold)
    geoms = [
        shape(g)
        for g, val in shapes(mask.astype(np.uint8), mask=mask, transform=transform)
        if val == 1
    ]
    if not geoms:
        raise RuntimeError(f"No urban cells found for {city.name}")
    gdf = gpd.GeoDataFrame(geometry=geoms, crs=crs).to_crs(4326)
    gdf["area_m2"] = gdf.to_crs(gdf.estimate_utm_crs()).area
    biggest = gdf.sort_values("area_m2", ascending=False).head(1)
    return gpd.GeoDataFrame(geometry=[unary_union(biggest.geometry)], crs=4326)
