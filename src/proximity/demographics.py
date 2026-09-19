"""Inclusive access: who is left outside the 15-minute walk.

Bruno's framing is *inclusive* 15-minute cities, but a single population weight treats
a toddler and a working adult as the same person with the same errands. Each subgroup is
scored against the service it actually needs: children under 15 against schools,
under-5s / women 15-49 / over-65s against clinics.

**Subgroup F15 rates are not identifiable from GRID3/WorldPop NGA v3.0.** Its age-sex
grids are the total population grid multiplied by a constant applied at state level, so
inside any one city the subgroup share of a pixel is the same everywhere: measured over
the metro polygons the ratio has min == max and a standard deviation around 1e-9. A
constant re-weighting cannot move a population-weighted mean, so subgroup F15 comes back
exactly equal to total-population F15 for the same service — the first run of this module
returned 0.24666757 for under-5s, women 15-49 and over-65s alike, which is arithmetic,
not a finding. Reporting those as subgroup differences would be fabrication.

What the age-sex grids *can* support is headcounts. "Port Harcourt's clinic F15 is 24.7%"
and "176,000 of its under-5s live beyond a 15-minute walk of a clinic" carry the same
rate but the second is the one that means something. So this module reports the
underserved **count** per subgroup and states the shared rate once. Genuine subgroup
rates would need sub-city age structure — DHS clusters or ward-level census — which is a
separate data acquisition, not a re-weighting.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from .cities import CITIES
from .paths import DATA_PROCESSED, DATA_RAW
from .population import populate_hexes

DOCUMENTS = Path.home() / "Documents"
AGESEX_DIRS = (
    DATA_RAW / "NGA_population_v3_0_agesex",
    DOCUMENTS / "Portfolio" / "Data" / "NGA_population_v3_0_agesex",
)
PREFIX = "NGA_population_v3_0_agesex_"

# subgroup -> (raster stem, travel-time column, why this service)
SUBGROUPS: dict[str, tuple[str, str, str]] = {
    "under5": ("under5", "t_health", "child health / immunisation"),
    "under15": ("under15", "t_school", "school age"),
    "women15_49": ("f15_49", "t_health", "maternal health"),
    "over65": ("over65", "t_health", "elderly care"),
}
THRESHOLD_MIN = 15.0


def agesex_dir() -> Path:
    for path in AGESEX_DIRS:
        if path.is_dir():
            return path
    raise FileNotFoundError("NGA v3.0 age-sex rasters not found")


def raster_for(stem: str) -> Path:
    path = agesex_dir() / f"{PREFIX}{stem}.tif"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


SHARE_SPREAD_TOL = 1e-6


def subgroup_share(slug: str, stem: str) -> tuple[float, float]:
    """Subgroup share of population inside the metro, and how much it varies in space.

    Returns (share, spread). Because the grids are a state-level constant times the
    total, `spread` is ~1e-9 and the share is one number for the whole city, so a
    hexagon-by-hexagon zonal pass spends two minutes to rediscover a scalar. The spread
    is returned, not discarded, so a future vintage that genuinely varies trips the
    caller's fallback instead of being silently flattened.
    """
    import rasterio
    from rasterio.mask import mask

    from .pipeline import urban_boundary_lgas

    geom = [urban_boundary_lgas(CITIES[slug]).to_crs(4326).geometry.iloc[0]]
    with rasterio.open(DATA_RAW / "NGA_population_v3_0_gridded.tif") as src:
        total, _ = mask(src, geom, crop=True, filled=True, nodata=0)
    with rasterio.open(raster_for(stem)) as src:
        sub, _ = mask(src, geom, crop=True, filled=True, nodata=0)
    total, sub = total[0].astype(float), sub[0].astype(float)
    ok = (total > 0.5) & np.isfinite(total) & np.isfinite(sub)
    if not ok.any():
        return float("nan"), float("nan")
    ratio = sub[ok] / total[ok]
    return float(ratio.mean()), float(ratio.std())


def city_subgroups(slug: str) -> pd.DataFrame:
    hexes = gpd.read_file(DATA_PROCESSED / f"{slug}_hexes.gpkg")
    total_pop = hexes["pop"].fillna(0).to_numpy(dtype=float)
    rows = []

    def _f15(time_col: str, weights: np.ndarray) -> float:
        t = hexes[time_col].to_numpy(dtype=float)
        ok = np.isfinite(t)
        return float(weights[ok & (t <= THRESHOLD_MIN)].sum() / weights.sum())

    for label, time_col, why in (
        ("all", "PT_k", "health + schools (PT_k)"),
        ("all", "t_health", "health only"),
        ("all", "t_school", "schools only"),
    ):
        if time_col not in hexes.columns:
            continue
        f15 = _f15(time_col, total_pop)
        rows.append(
            {
                "city": CITIES[slug].name,
                "subgroup": label,
                "service": why,
                "people": float(total_pop.sum()),
                "F15": f15,
                "people_underserved": float(total_pop.sum() * (1 - f15)),
                "share_of_total": 1.0,
                "rate_source": "measured",
            }
        )

    for name, (stem, time_col, why) in SUBGROUPS.items():
        if time_col not in hexes.columns:
            continue
        share, spread = subgroup_share(slug, stem)
        if not np.isfinite(share):
            continue
        if spread > SHARE_SPREAD_TOL:
            # A vintage with real spatial age structure: fall back to the honest zonal pass.
            w = populate_hexes(hexes[["geometry"]].copy(), raster_for(stem), pop_col=name)
            weights = w[name].fillna(0).to_numpy(dtype=float)
            source = "measured"
        else:
            weights = total_pop * share
            source = "inherited from total (constant state-level share)"
        f15 = _f15(time_col, weights)
        rows.append(
            {
                "city": CITIES[slug].name,
                "subgroup": name,
                "service": why,
                "people": float(weights.sum()),
                "F15": f15,
                "people_underserved": float(weights.sum() * (1 - f15)),
                "share_of_total": share,
                "rate_source": source,
            }
        )
    return pd.DataFrame(rows)


def build(slugs: list[str] | None = None) -> pd.DataFrame:
    path = DATA_PROCESSED / "inclusive_f15_by_subgroup.csv"
    table = pd.read_csv(path) if path.exists() else pd.DataFrame()
    for slug in slugs or list(CITIES):
        if not (DATA_PROCESSED / f"{slug}_hexes.gpkg").exists():
            continue
        print(f"  {slug} …", flush=True)
        frame = city_subgroups(slug)
        if len(table):
            table = table[table["city"] != CITIES[slug].name]
        table = pd.concat([table, frame], ignore_index=True)
        table.to_csv(path, index=False)
    return table


if __name__ == "__main__":
    import sys

    print(build(sys.argv[1:] or None).to_string(index=False))
