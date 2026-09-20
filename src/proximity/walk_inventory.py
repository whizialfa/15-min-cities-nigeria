"""Walk-graph lines and sidewalk tagging for inventory plates.

Writes `{slug}_walk_edges.gpkg` (gitignored) and `walk_network_stats.csv`.
The score still uses the graph; this is only cartography and a table.
"""

from __future__ import annotations

from collections import Counter

import geopandas as gpd
import pandas as pd

from .car_access import ensure_osm_graph
from .cities import CITIES
from .paths import DATA_PROCESSED


def _tag(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip().lower()


def _sidewalk_bucket(raw) -> str:
    v = _tag(raw)
    if v in {"", "none", "no", "nan"}:
        return "none"
    if v in {"yes", "both", "left", "right", "separate"}:
        return "named"
    return "other"


def export_walk_edges(slug: str) -> gpd.GeoDataFrame:
    import osmnx as ox

    city = CITIES[slug]
    G = ensure_osm_graph(city, "walk")
    edges = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
    if edges.crs is None:
        edges = edges.set_crs(4326)
    else:
        edges = edges.to_crs(4326)
    bound = gpd.read_file(DATA_PROCESSED / f"{slug}_study_boundary.gpkg").to_crs(4326)
    mask = bound.union_all() if hasattr(bound, "union_all") else bound.unary_union
    clipped = gpd.clip(edges, mask)
    clipped = clipped[~clipped.geometry.is_empty & clipped.geometry.notna()].copy()
    clipped["geometry"] = clipped.geometry.simplify(0.00008, preserve_topology=True)
    clipped = clipped.explode(index_parts=False)
    keep = [c for c in ("highway", "sidewalk", "footway", "name", "length", "geometry") if c in clipped.columns]
    out = clipped[keep].reset_index(drop=True)
    path = DATA_PROCESSED / f"{slug}_walk_edges.gpkg"
    out.to_file(path, layer=f"{slug}_walk_edges", driver="GPKG")
    print(f"  {slug} walk edges {len(out):,} → {path.name}", flush=True)
    return out


def _network_stats(slug: str, edges: gpd.GeoDataFrame) -> dict:
    import osmnx as ox

    city = CITIES[slug]
    G = ensure_osm_graph(city, "walk")
    undirected = ox.convert.to_undirected(G) if hasattr(ox, "convert") else G.to_undirected()
    degrees = [d for _, d in undirected.degree()]
    n_nodes = len(degrees)
    deadends = sum(1 for d in degrees if d == 1)
    sidewalks = Counter(_sidewalk_bucket(v) for v in edges["sidewalk"]) if "sidewalk" in edges.columns else Counter({"none": len(edges)})
    n = max(len(edges), 1)
    proj = edges.to_crs(city.utm_epsg)
    km = float(proj.geometry.length.sum() / 1000.0)
    return {
        "city": city.name,
        "slug": slug,
        "walk_km": round(km, 1),
        "walk_edges": int(len(edges)),
        "nodes": int(n_nodes),
        "deadend_share": round(deadends / n_nodes, 4) if n_nodes else None,
        "sidewalk_named_share": round(sidewalks.get("named", 0) / n, 4),
        "sidewalk_none_share": round(sidewalks.get("none", 0) / n, 4),
    }


def rebuild(slugs: tuple[str, ...] | None = None) -> pd.DataFrame:
    slugs = slugs or tuple(CITIES)
    rows = []
    for slug in slugs:
        print(f"Walk inventory {slug} …", flush=True)
        edges = export_walk_edges(slug)
        rows.append(_network_stats(slug, edges))
    table = pd.DataFrame(rows)
    out = DATA_PROCESSED / "walk_network_stats.csv"
    table.to_csv(out, index=False)
    print(table.to_string(index=False), flush=True)
    return table


if __name__ == "__main__":
    import sys

    args = [a for a in sys.argv[1:] if a in CITIES]
    rebuild(tuple(args) if args else None)
