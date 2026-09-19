"""Dual-access proximity times. Euclidean 5 km/h until OSRM is wired."""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from .cities import N_DUAL_DEFAULT, WALK_M_PER_MIN


def projected_xy(gdf) -> np.ndarray:
    utm = gdf.estimate_utm_crs()
    c = gdf.to_crs(utm).geometry.centroid
    return np.column_stack([c.x.to_numpy(), c.y.to_numpy()])


def mean_time_to_n(
    origins,
    destinations,
    n: int = N_DUAL_DEFAULT,
    walk_m_per_min: float = WALK_M_PER_MIN,
) -> tuple[np.ndarray, np.ndarray]:
    """Mean walk minutes to the n nearest destinations (Bruno dual access).

    Returns (minutes, k_found). k_found < n is a completeness flag, not a drop.
    """
    ox = projected_xy(origins)
    if destinations is None or len(destinations) == 0:
        empty = np.full(len(origins), np.nan)
        return empty, np.zeros(len(origins), dtype=int)

    dests = destinations.copy()
    dests = dests[~dests.geometry.is_empty]
    if dests.geom_type.isin(["Polygon", "MultiPolygon"]).any():
        dests = dests.copy()
        dests.geometry = dests.geometry.centroid

    dx = projected_xy(dests.to_crs(origins.crs) if dests.crs else dests)
    if len(dx) == 0:
        empty = np.full(len(origins), np.nan)
        return empty, np.zeros(len(origins), dtype=int)

    tree = cKDTree(dx)
    k = int(min(n, len(dx)))
    dists, _ = tree.query(ox, k=k, workers=-1)
    dists = np.atleast_2d(dists)
    if k == 1:
        dists = dists.T
    minutes = dists / walk_m_per_min
    return minutes.mean(axis=1), np.full(len(origins), k, dtype=int)
