"""Completeness mask — where "no access" may really mean "not mapped".

The pipeline's existing flags are vacuous: `pop_unmapped_share` and the share of people
who cannot reach n facilities both come out at 0, because they only catch hexagons cut
off from the graph entirely. Two signals that actually discriminate:

1. **Street network** — how far a hexagon centroid sits from the nearest walk-graph
   node. People live where there is no mapped path, so a large snap distance means the
   routing engine invented a detour, not that the walk is genuinely long.
2. **POI inventory** — OSM facility counts against GRID3's administrative counts for the
   same area. A low ratio means OSM under-records that city.

   Count OSM through Overpass `nwr`, never through the HOT points export on HDX. That
   export holds 2,847 points for all of Nigeria and keeps only node-tagged facilities,
   so it finds 67 Lagos schools against the 630 actually in OSM. Schools are mapped as
   building polygons in the south and as points in the north — Lagos is 47% nodes,
   Kano 87% — so a points-only count ranks the best-mapped city last and inverts the
   very bias this signal exists to detect.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .car_access import ensure_osm_graph
from .cities import CITIES
from .facilities import filter_state, load_local_facilities
from .overpass import count_amenities
from .paths import DATA_PROCESSED
from .pipeline import urban_boundary_lgas

SNAP_WARN_M = 250.0


def network_completeness(slug: str, persist: bool = True) -> dict:
    city = CITIES[slug]
    path = DATA_PROCESSED / f"{slug}_hexes.gpkg"
    hexes = gpd.read_file(path).to_crs(4326)
    pop = hexes["pop"].fillna(0).to_numpy(dtype=float)

    G = ensure_osm_graph(city, "walk")
    node_xy = np.array([(d["x"], d["y"]) for _, d in G.nodes(data=True)])
    nodes = gpd.GeoSeries(gpd.points_from_xy(node_xy[:, 0], node_xy[:, 1]), crs=4326)

    utm = hexes.estimate_utm_crs()
    centroids = hexes.to_crs(utm).geometry.representative_point()
    tree = cKDTree(np.column_stack([nodes.to_crs(utm).x, nodes.to_crs(utm).y]))
    snap_m, _ = tree.query(np.column_stack([centroids.x, centroids.y]))

    far = snap_m > SNAP_WARN_M
    if persist:
        # The maps need the mask per hexagon, and re-deriving it means reloading the graph.
        hexes["snap_m"] = snap_m
        hexes["off_network"] = far
        hexes.to_file(path, driver="GPKG")
    return {
        "city": city.name,
        "slug": slug,
        "median_snap_m": float(np.median(snap_m)),
        "p90_snap_m": float(np.percentile(snap_m, 90)),
        "pop_share_offnetwork": float(pop[far].sum() / pop.sum()) if pop.sum() else np.nan,
        "hex_share_offnetwork": float(far.mean()),
    }


OSM_SCHOOL_AMENITIES = ["school", "college", "university", "kindergarten"]


def poi_completeness(slug: str) -> dict:
    """OSM against GRID3 for the same metro. Below 1.0 means OSM under-records.

    Both sides are counted over the city **bbox**, not the metro polygon: Overpass
    counts cheaply over a bbox but not over a many-vertex boundary, and a ratio only
    means anything if numerator and denominator cover identical ground. The
    metro-clipped GRID3 total is reported separately as `grid3_schools_metro`.
    """
    city = CITIES[slug]
    west, south, east, north = city.bbox
    frame = urban_boundary_lgas(city).to_crs(4326).union_all()
    layers = load_local_facilities(city)

    grid3_gdf = layers.get("education_grid3")
    grid3_bbox = grid3_metro = 0
    if grid3_gdf is not None and not grid3_gdf.empty:
        g = grid3_gdf.to_crs(4326)
        grid3_bbox = int(len(g.cx[west:east, south:north]))
        inside = g[g.intersects(frame)]
        grid3_metro = int(len(filter_state(inside, city))) if len(inside) else 0

    try:
        osm_bbox = count_amenities(city, OSM_SCHOOL_AMENITIES)
    except Exception as exc:
        print(f"    Overpass school count failed for {slug}: {exc}", flush=True)
        osm_bbox = None

    return {
        "city": city.name,
        "slug": slug,
        "grid3_schools_metro": grid3_metro,
        "grid3_schools_bbox": grid3_bbox,
        "osm_schools_bbox": osm_bbox if osm_bbox is not None else np.nan,
        "osm_to_grid3_ratio": (osm_bbox / grid3_bbox)
        if (osm_bbox is not None and grid3_bbox)
        else np.nan,
    }


def build(slugs: list[str] | None = None) -> pd.DataFrame:
    rows = []
    for slug in slugs or list(CITIES):
        if not (DATA_PROCESSED / f"{slug}_hexes.gpkg").exists():
            continue
        print(f"  {slug} …", flush=True)
        row = network_completeness(slug)
        row.update({k: v for k, v in poi_completeness(slug).items() if k not in row})
        rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(DATA_PROCESSED / "completeness.csv", index=False)
    return table


if __name__ == "__main__":
    import sys

    print(build(sys.argv[1:] or None).to_string(index=False))
