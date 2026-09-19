"""OSM network dual access: walk (headline) and car grades A/B/C."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from .cities import City, N_DUAL_NONSUBSTITUTABLE, WALK_M_PER_MIN
from .paths import DATA_RAW

HIGHWAY_KMH_A = {
    "motorway": 80,
    "motorway_link": 50,
    "trunk": 60,
    "trunk_link": 40,
    "primary": 50,
    "primary_link": 35,
    "secondary": 40,
    "secondary_link": 30,
    "tertiary": 35,
    "tertiary_link": 25,
    "unclassified": 30,
    "residential": 25,
    "living_street": 15,
    "service": 15,
    "road": 30,
}

GRADE_B_KMH = 20.0
GRADE_C_KMH = 12.0

GRADE_LABELS = {
    "A": "car A · OSM free-flow speeds",
    "B": "car B · 20 km/h congested urban",
    "C": "car C · 12 km/h peak proxy (no live traffic)",
}

WALK_LABEL = "foot · OSM walk graph · 5 km/h"


def _highway_key(raw) -> str:
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    return str(raw or "").split(";")[0]


def _edge_minutes(length_m: float, kmh: float) -> float:
    return float(length_m) / (kmh * 1000.0 / 60.0)


def graph_cache_path(city: City, network_type: str) -> Path:
    return DATA_RAW / f"{city.slug}_osm_{network_type}.graphml"


OVERPASS_MIRRORS = (
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
    "https://overpass.private.coffee/api",
)


def ensure_osm_graph(city: City, network_type: str, pad: float = 0.04):
    import osmnx as ox

    ox.settings.timeout = 300
    cache = graph_cache_path(city, network_type)
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    if cache.exists() and cache.stat().st_size > 1000:
        print(f"OSM {network_type} graph cache {cache.name}", flush=True)
        return ox.load_graphml(cache)

    west, south, east, north = city.bbox
    bbox = (west - pad, south - pad, east + pad, north + pad)
    last: Exception | None = None
    # The default endpoint refuses connections under load; mirrors serve the same data.
    for url in OVERPASS_MIRRORS:
        ox.settings.overpass_url = url
        print(f"Downloading OSM {network_type} graph for {city.name} via {url} …", flush=True)
        try:
            try:
                G = ox.graph_from_bbox(bbox=bbox, network_type=network_type, simplify=True)
            except TypeError:
                G = ox.graph_from_bbox(
                    north + pad, south - pad, east + pad, west - pad, network_type=network_type
                )
            ox.save_graphml(G, cache)
            return G
        except Exception as exc:
            last = exc
            print(f"  {url} failed: {exc}", flush=True)
    raise RuntimeError(f"all Overpass mirrors failed for {city.name}") from last


def ensure_drive_graph(city: City, pad: float = 0.04):
    return ensure_osm_graph(city, "drive", pad=pad)


def _annotate_drive_times(G):
    for _u, _v, _k, data in G.edges(keys=True, data=True):
        length = float(data.get("length") or 0.0)
        kmh_a = HIGHWAY_KMH_A.get(_highway_key(data.get("highway")), 30.0)
        data["t_A"] = _edge_minutes(length, kmh_a)
        data["t_B"] = _edge_minutes(length, GRADE_B_KMH)
        data["t_C"] = _edge_minutes(length, GRADE_C_KMH)
    return G


def _annotate_walk_times(G):
    kmh = WALK_M_PER_MIN * 60.0 / 1000.0
    for _u, _v, _k, data in G.edges(keys=True, data=True):
        data["t_walk"] = _edge_minutes(float(data.get("length") or 0.0), kmh)
    return G


def _simple_digraph(G, weight: str) -> nx.DiGraph:
    H = nx.DiGraph()
    for u, v, data in G.edges(data=True):
        t = float(data.get(weight) or np.inf)
        if H.has_edge(u, v):
            H[u][v][weight] = min(H[u][v][weight], t)
        else:
            H.add_edge(u, v, **{weight: t})
    return H


def _as_points(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    pts = gdf.to_crs(4326)
    if pts.geom_type.isin(["Polygon", "MultiPolygon"]).any():
        pts = pts.copy()
        utm = pts.estimate_utm_crs()
        pts.geometry = pts.to_crs(utm).geometry.centroid.to_crs(4326)
    return pts


def _nearest_nodes(G, gdf: gpd.GeoDataFrame) -> np.ndarray:
    import osmnx as ox

    pts = _as_points(gdf)
    x = pts.geometry.x.to_numpy()
    y = pts.geometry.y.to_numpy()
    try:
        return np.asarray(ox.nearest_nodes(G, x, y))
    except Exception:
        node_ids = np.array(list(G.nodes))
        coords = np.array([(G.nodes[n]["x"], G.nodes[n]["y"]) for n in node_ids])
        _, ix = cKDTree(coords).query(np.column_stack([x, y]))
        return node_ids[ix]


def _mean_k(dist_row: np.ndarray, dest_idx: np.ndarray, n: int) -> tuple[float, int]:
    if dest_idx.size == 0:
        return float("nan"), 0
    poi = dist_row[dest_idx]
    poi = poi[np.isfinite(poi)]
    if poi.size == 0:
        return float("nan"), 0
    take = min(n, poi.size)
    return float(np.mean(np.partition(poi, take - 1)[:take])), take


def dual_access_on_graph(
    origins: gpd.GeoDataFrame,
    health: gpd.GeoDataFrame,
    schools: gpd.GeoDataFrame,
    G,
    weight: str,
    n: int = N_DUAL_NONSUBSTITUTABLE,
    batch: int = 250,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    orig_nodes = _nearest_nodes(G, origins)
    health_nodes = (
        _nearest_nodes(G, health) if health is not None and len(health) else np.array([], dtype=int)
    )
    school_nodes = (
        _nearest_nodes(G, schools) if schools is not None and len(schools) else np.array([], dtype=int)
    )
    unique_orig, inverse = np.unique(orig_nodes.astype(np.int64), return_inverse=True)
    H = _simple_digraph(G, weight)
    nodes = list(H.nodes)
    index = {node: i for i, node in enumerate(nodes)}
    mat = nx.to_scipy_sparse_array(H, nodelist=nodes, weight=weight, format="csr", dtype=float)
    dest_h = np.array([index[int(d)] for d in health_nodes if int(d) in index], dtype=int)
    dest_s = np.array([index[int(d)] for d in school_nodes if int(d) in index], dtype=int)
    orig_idx = np.array([index.get(int(n_), -1) for n_ in unique_orig])

    t_h_u = np.full(len(unique_orig), np.nan)
    t_s_u = np.full(len(unique_orig), np.nan)
    k_h_u = np.zeros(len(unique_orig), dtype=int)
    k_s_u = np.zeros(len(unique_orig), dtype=int)
    valid = np.where(orig_idx >= 0)[0]
    for start in range(0, len(valid), batch):
        chunk = valid[start : start + batch]
        src = orig_idx[chunk]
        dist = dijkstra(mat, directed=True, indices=src, unweighted=False)
        if dist.ndim == 1:
            dist = dist.reshape(1, -1)
        for row, ui in enumerate(chunk):
            t_h_u[ui], k_h_u[ui] = _mean_k(dist[row], dest_h, n)
            t_s_u[ui], k_s_u[ui] = _mean_k(dist[row], dest_s, n)
        print(f"    routed {min(start + batch, len(valid))}/{len(valid)} origin nodes", flush=True)

    return t_h_u[inverse], k_h_u[inverse], t_s_u[inverse], k_s_u[inverse]


def walk_dual_access(
    origins: gpd.GeoDataFrame,
    health: gpd.GeoDataFrame,
    schools: gpd.GeoDataFrame,
    city: City,
    n: int = N_DUAL_NONSUBSTITUTABLE,
) -> dict[str, np.ndarray]:
    G = _annotate_walk_times(ensure_osm_graph(city, "walk"))
    print(f"  routing {WALK_LABEL} …", flush=True)
    t_h, k_h, t_s, k_s = dual_access_on_graph(origins, health, schools, G, "t_walk", n=n)
    stacked = np.vstack([t_h, t_s])
    with np.errstate(all="ignore"):
        pt = np.nanmean(stacked, axis=0)
    pt[~np.isfinite(t_h) & ~np.isfinite(t_s)] = np.nan
    print(f"    median PT_walk={np.nanmedian(pt):.1f} min", flush=True)
    return {
        "t_health_walk": t_h,
        "k_health_walk": k_h,
        "t_school_walk": t_s,
        "k_school_walk": k_s,
        "PT_walk": pt,
    }


def car_dual_access(
    origins: gpd.GeoDataFrame,
    health: gpd.GeoDataFrame,
    schools: gpd.GeoDataFrame,
    city: City,
    n: int = N_DUAL_NONSUBSTITUTABLE,
    batch: int = 250,
) -> dict[str, np.ndarray]:
    G = _annotate_drive_times(ensure_drive_graph(city))
    out: dict[str, np.ndarray] = {}
    for grade, weight in (("A", "t_A"), ("B", "t_B"), ("C", "t_C")):
        print(f"  routing car grade {grade} ({GRADE_LABELS[grade]}) …", flush=True)
        t_h, _, t_s, _ = dual_access_on_graph(
            origins, health, schools, G, weight, n=n, batch=batch
        )
        stacked = np.vstack([t_h, t_s])
        with np.errstate(all="ignore"):
            pt = np.nanmean(stacked, axis=0)
        pt[~np.isfinite(t_h) & ~np.isfinite(t_s)] = np.nan
        out[f"t_health_car_{grade}"] = t_h
        out[f"t_school_car_{grade}"] = t_s
        out[f"PT_car_{grade}"] = pt
        print(f"    median PT_car_{grade}={np.nanmedian(pt):.1f} min", flush=True)
    return out
