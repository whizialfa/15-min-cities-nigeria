"""N* — how many optimally sited facilities would it take to reach F15 = 90%?

Unlike PT_k and F15, N* does not depend on the POI inventory, only on where people
live and how the street network connects them. That makes it the honest headline when
OSM/GRID3 coverage is thin: we stop asking "what is mapped" and ask "how much is needed".

Method: candidate sites are hexagon centroids snapped to the walk graph. A candidate
covers a hexagon if the walk is <= THRESHOLD_MIN. Choosing the smallest covering set is
NP-hard (maximum coverage), so this uses the standard greedy algorithm, which is within
1 - 1/e (~63%) of optimal and in practice much closer. N* is therefore an upper bound on
the true minimum.

This is single-destination (n = 1) coverage, not Bruno's n = 5 dual access: it answers
"could you reach one of these in 15 minutes", which is the right question for a facility
that does not yet exist.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from .car_access import _annotate_walk_times, _nearest_nodes, _simple_digraph, ensure_osm_graph
from .cities import CITIES, City
from .paths import DATA_PROCESSED

THRESHOLD_MIN = 15.0
TARGET_F15 = 0.90


def coverage_matrix(city: City, hexes: gpd.GeoDataFrame, batch: int = 250):
    """Sparse candidate x hexagon matrix, True where the walk is within the threshold."""
    import networkx as nx

    G = _annotate_walk_times(ensure_osm_graph(city, "walk"))
    H = _simple_digraph(G, "t_walk")
    nodes = list(H.nodes)
    index = {node: i for i, node in enumerate(nodes)}
    mat = nx.to_scipy_sparse_array(H, nodelist=nodes, weight="t_walk", format="csr", dtype=float)

    hex_nodes = _nearest_nodes(G, hexes)
    unique_nodes, inverse = np.unique(hex_nodes.astype(np.int64), return_inverse=True)
    node_idx = np.array([index.get(int(n), -1) for n in unique_nodes])
    valid = np.where(node_idx >= 0)[0]
    # Hexagons sharing each snapped node, so coverage expands without rescanning.
    order = np.argsort(inverse, kind="stable")
    bounds = np.searchsorted(inverse[order], np.arange(len(unique_nodes) + 1))
    hexes_of_node = [order[bounds[u] : bounds[u + 1]] for u in range(len(unique_nodes))]

    rows, cols = [], []
    for start in range(0, len(valid), batch):
        chunk = valid[start : start + batch]
        dist = dijkstra(mat, directed=True, indices=node_idx[chunk], limit=THRESHOLD_MIN)
        dist = np.atleast_2d(dist)
        for row, ui in enumerate(chunk):
            reachable = valid[np.isfinite(dist[row][node_idx[valid]])]
            if reachable.size == 0:
                continue
            hit = np.concatenate([hexes_of_node[u] for u in reachable])
            rows.append(np.full(hit.size, ui, dtype=np.int32))
            cols.append(hit.astype(np.int32))
        print(f"    coverage {min(start + batch, len(valid))}/{len(valid)} candidates", flush=True)

    r = np.concatenate(rows)
    c = np.concatenate(cols)
    cover = csr_matrix((np.ones(r.size, dtype=bool), (r, c)), shape=(len(unique_nodes), len(hexes)))
    site_hex = np.array([h[0] if len(h) else -1 for h in hexes_of_node])
    return cover, site_hex


def greedy_cover(cover: csr_matrix, pop: np.ndarray, target: float = TARGET_F15) -> dict:
    """Pick sites one at a time, each time taking the largest uncovered population."""
    total = pop.sum()
    uncovered = np.ones(len(pop), dtype=bool)
    chosen: list[int] = []
    curve: list[float] = []
    while (total - pop[uncovered].sum()) / total < target:
        gains = cover @ (pop * uncovered)
        best = int(np.argmax(gains))
        if gains[best] <= 0:
            print("    no candidate adds coverage — stopping short of target", flush=True)
            break
        chosen.append(best)
        uncovered[cover[best].indices] = False
        curve.append(float((total - pop[uncovered].sum()) / total))
    return {"sites": chosen, "curve": curve, "covered": curve[-1] if curve else 0.0}


def nstar_city(slug: str, target: float = TARGET_F15) -> dict:
    city = CITIES[slug]
    hexes = gpd.read_file(DATA_PROCESSED / f"{slug}_hexes.gpkg").to_crs(4326)
    pop = hexes["pop"].fillna(0).to_numpy(dtype=float)
    print(f"{city.name}: {len(hexes)} hexes, {pop.sum():,.0f} people", flush=True)

    cover, site_hex = coverage_matrix(city, hexes)
    result = greedy_cover(cover, pop, target=target)
    n = len(result["sites"])
    out = {
        "city": city.name,
        "slug": slug,
        "pop": float(pop.sum()),
        "N_star": n,
        "N_star_per_100k": n / (pop.sum() / 1e5),
        "coverage_reached": result["covered"],
        "target": target,
    }
    chosen = site_hex[result["sites"]]
    sites = hexes.iloc[chosen[chosen >= 0]].copy()
    sites["rank"] = range(1, len(sites) + 1)
    sites.geometry = sites.geometry.representative_point()
    sites[["rank", "geometry"]].to_file(DATA_PROCESSED / f"{slug}_nstar_sites.gpkg", driver="GPKG")
    pd.DataFrame({"n_sites": range(1, n + 1), "pop_covered": result["curve"]}).to_csv(
        DATA_PROCESSED / f"{slug}_nstar_curve.csv", index=False
    )
    return out


def observed_coverage(slug: str, layer: str) -> dict:
    """Population within THRESHOLD_MIN walk of at least one existing facility.

    Same single-destination rule as N*, so the two are directly comparable — unlike
    F15, which uses the n = 5 dual-access mean.
    """
    import networkx as nx

    city = CITIES[slug]
    hexes = gpd.read_file(DATA_PROCESSED / f"{slug}_hexes.gpkg").to_crs(4326)
    pts = gpd.read_file(DATA_PROCESSED / f"{slug}_{layer}_points.gpkg").to_crs(4326)
    pop = hexes["pop"].fillna(0).to_numpy(dtype=float)

    G = _annotate_walk_times(ensure_osm_graph(city, "walk"))
    H = _simple_digraph(G, "t_walk")
    nodes = list(H.nodes)
    index = {node: i for i, node in enumerate(nodes)}
    mat = nx.to_scipy_sparse_array(H, nodelist=nodes, weight="t_walk", format="csr", dtype=float)

    hex_nodes = _nearest_nodes(G, hexes)
    unique_nodes, inverse = np.unique(hex_nodes.astype(np.int64), return_inverse=True)
    node_idx = np.array([index.get(int(n), -1) for n in unique_nodes])

    src = np.array([index[int(n)] for n in _nearest_nodes(G, pts) if int(n) in index])
    dist = np.atleast_2d(dijkstra(mat, directed=True, indices=src, limit=THRESHOLD_MIN))
    best = np.nanmin(np.where(np.isfinite(dist), dist, np.inf), axis=0)

    node_ok = np.isfinite(best[node_idx]) & (node_idx >= 0)
    covered = node_ok[inverse]
    return {
        "city": city.name,
        "layer": layer,
        "n_facilities": int(len(pts)),
        "pop_covered": float(pop[covered].sum() / pop.sum()),
    }


def build(slugs: list[str] | None = None) -> pd.DataFrame:
    path = DATA_PROCESSED / "nstar.csv"
    table = pd.read_csv(path) if path.exists() else pd.DataFrame()
    for slug in slugs or ["port_harcourt"]:
        row = nstar_city(slug)
        obs = observed_coverage(slug, "health")
        row["n_facilities"] = obs["n_facilities"]
        row["pop_covered"] = obs["pop_covered"]
        have = obs["n_facilities"]
        row["sites_vs_existing"] = (row["N_star"] / have) if have else float("nan")
        frame = pd.DataFrame([row])
        if len(table):
            table = table[table["slug"] != slug]
        table = pd.concat([table, frame], ignore_index=True)
        # Per city, and merged rather than replaced: the coverage pass runs for hours and
        # a kill on city four must not take the first three with it.
        table.to_csv(path, index=False)
    return table


if __name__ == "__main__":
    import sys

    print(build(sys.argv[1:] or None).to_string(index=False))
