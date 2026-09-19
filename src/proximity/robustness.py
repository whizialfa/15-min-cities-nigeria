"""Robustness — is the headline an artefact of a parameter choice?

Three sweeps:

- **n** (choice-set size): 1, 5, 20. Recomputed from a single Dijkstra pass per city, so
  the walk network is respected rather than approximated by straight lines.
- **walking speed**: free. On a fixed path, time scales inversely with speed, so a 5 km/h
  result converts exactly to 3.5 or 4.5 km/h without re-routing.
- **Euclidean vs network**: the gap already known to cost Lagos ~10 points and Port
  Harcourt ~38, reported per city so the straight-line bias is explicit.

Hexagon size is deliberately not swept: changing it means regridding population and
re-routing every origin, which is a rebuild rather than a sensitivity.
"""

from __future__ import annotations

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse.csgraph import dijkstra

from .access import mean_time_to_n
from .car_access import (
    _annotate_walk_times,
    _mean_k,
    _nearest_nodes,
    _simple_digraph,
    ensure_osm_graph,
)
from .cities import CITIES, WALK_M_PER_MIN
from .paths import DATA_PROCESSED

N_VALUES = (1, 5, 20)
SPEEDS_KMH = (3.5, 4.5, 5.0)
BASE_KMH = WALK_M_PER_MIN * 60.0 / 1000.0
THRESHOLD_MIN = 15.0


def _facilities(slug: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    health = gpd.read_file(DATA_PROCESSED / f"{slug}_health_points.gpkg").to_crs(4326)
    schools = gpd.read_file(DATA_PROCESSED / f"{slug}_school_points.gpkg").to_crs(4326)
    return health, schools


def walk_n_sweep(slug: str, batch: int = 250) -> pd.DataFrame:
    """One Dijkstra pass, every n. PT_k is the mean of the health and school times."""
    city = CITIES[slug]
    hexes = gpd.read_file(DATA_PROCESSED / f"{slug}_hexes.gpkg").to_crs(4326)
    pop = hexes["pop"].fillna(0).to_numpy(dtype=float)
    health, schools = _facilities(slug)

    G = _annotate_walk_times(ensure_osm_graph(city, "walk"))
    H = _simple_digraph(G, "t_walk")
    nodes = list(H.nodes)
    index = {node: i for i, node in enumerate(nodes)}
    mat = nx.to_scipy_sparse_array(H, nodelist=nodes, weight="t_walk", format="csr", dtype=float)

    orig = _nearest_nodes(G, hexes)
    unique_nodes, inverse = np.unique(orig.astype(np.int64), return_inverse=True)
    node_idx = np.array([index.get(int(n), -1) for n in unique_nodes])
    dest_h = np.array([index[int(d)] for d in _nearest_nodes(G, health) if int(d) in index])
    dest_s = np.array([index[int(d)] for d in _nearest_nodes(G, schools) if int(d) in index])

    per_n = {n: {"h": np.full(len(unique_nodes), np.nan), "s": np.full(len(unique_nodes), np.nan)} for n in N_VALUES}
    valid = np.where(node_idx >= 0)[0]
    for start in range(0, len(valid), batch):
        chunk = valid[start : start + batch]
        dist = np.atleast_2d(dijkstra(mat, directed=True, indices=node_idx[chunk]))
        for row, ui in enumerate(chunk):
            for n in N_VALUES:
                per_n[n]["h"][ui] = _mean_k(dist[row], dest_h, n)[0]
                per_n[n]["s"][ui] = _mean_k(dist[row], dest_s, n)[0]
        print(f"    {slug} sweep {min(start + batch, len(valid))}/{len(valid)}", flush=True)

    rows = []
    for n in N_VALUES:
        t_h = per_n[n]["h"][inverse]
        t_s = per_n[n]["s"][inverse]
        with np.errstate(all="ignore"):
            pt = np.nanmean(np.vstack([t_h, t_s]), axis=0)
        for kmh in SPEEDS_KMH:
            scaled = pt * (BASE_KMH / kmh)
            ok = np.isfinite(scaled)
            rows.append(
                {
                    "city": city.name,
                    "mode": "walk network",
                    "n": n,
                    "kmh": kmh,
                    "PT_city": float(np.average(scaled[ok], weights=pop[ok])),
                    "F15": float(pop[ok & (scaled <= THRESHOLD_MIN)].sum() / pop.sum()),
                }
            )
        eu_h, _ = mean_time_to_n(hexes, health, n=n)
        eu_s, _ = mean_time_to_n(hexes, schools, n=n)
        with np.errstate(all="ignore"):
            eu = np.nanmean(np.vstack([eu_h, eu_s]), axis=0)
        ok = np.isfinite(eu)
        rows.append(
            {
                "city": city.name,
                "mode": "euclidean",
                "n": n,
                "kmh": BASE_KMH,
                "PT_city": float(np.average(eu[ok], weights=pop[ok])),
                "F15": float(pop[ok & (eu <= THRESHOLD_MIN)].sum() / pop.sum()),
            }
        )
    return pd.DataFrame(rows)


def build(slugs: list[str] | None = None) -> pd.DataFrame:
    path = DATA_PROCESSED / "robustness.csv"
    table = pd.read_csv(path) if path.exists() else pd.DataFrame()
    for slug in slugs or list(CITIES):
        if not (DATA_PROCESSED / f"{slug}_hexes.gpkg").exists():
            continue
        print(f"  {slug} …", flush=True)
        frame = walk_n_sweep(slug)
        if len(table):
            table = table[table["city"] != CITIES[slug].name]
        table = pd.concat([table, frame], ignore_index=True)
        # The sweep is a full unbounded Dijkstra per city; never batch the write.
        table.to_csv(path, index=False)
    return table


if __name__ == "__main__":
    import sys

    print(build(sys.argv[1:] or None).to_string(index=False))
