"""Ward-level F15 — who inside the city is excluded, not just how much.

Gini compresses the whole distribution into one number. Aggregating the same hexagons
to wards says *where* the excluded people are, which is what a siting argument needs.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from .cities import CITIES
from .paths import DATA_PROCESSED

THRESHOLD_MIN = 15.0
# Ignore almost-empty wards when naming a city's worst/best.
MIN_WARD_POP = 2000.0


def ward_f15(slug: str) -> gpd.GeoDataFrame:
    hexes = gpd.read_file(DATA_PROCESSED / f"{slug}_hexes.gpkg").to_crs(4326)
    wards = gpd.read_file(DATA_PROCESSED / f"{slug}_wards.gpkg").to_crs(4326)

    pts = hexes.copy()
    pts["pop"] = pts["pop"].fillna(0)
    pts["within"] = np.isfinite(pts["PT_k"]) & (pts["PT_k"] <= THRESHOLD_MIN)
    if "t_health" in pts.columns:
        pts["within_health"] = np.isfinite(pts["t_health"]) & (pts["t_health"] <= THRESHOLD_MIN)
    else:
        pts["within_health"] = pts["within"]
    pts.geometry = pts.geometry.representative_point()

    keep = [c for c in ("locator", "lganame", "geometry") if c in wards.columns]
    joined = gpd.sjoin(pts, wards[keep], predicate="within", how="inner")

    def _row(g: pd.DataFrame) -> pd.Series:
        pop = float(g["pop"].sum())
        if pop <= 0:
            return pd.Series(
                {"pop": 0.0, "PT_city": np.nan, "F15": np.nan, "F15_health": np.nan, "n_hex": len(g)}
            )
        return pd.Series(
            {
                "pop": pop,
                "PT_city": float(np.average(g["PT_k"], weights=g["pop"])),
                "F15": float(g.loc[g["within"], "pop"].sum() / pop),
                "F15_health": float(g.loc[g["within_health"], "pop"].sum() / pop),
                "n_hex": len(g),
            }
        )

    grouped = joined.groupby(["locator", "lganame"], dropna=False).apply(_row).reset_index()
    out = wards.merge(grouped, on=["locator", "lganame"], how="left")
    out["city"] = CITIES[slug].name
    path = DATA_PROCESSED / f"{slug}_ward_f15.gpkg"
    out.to_file(path, driver="GPKG")
    return out


def _notable(g: gpd.GeoDataFrame, n: int = 4) -> pd.DataFrame:
    ok = g["F15"].notna() & (g["pop"].fillna(0) >= MIN_WARD_POP)
    if not ok.any():
        ok = g["F15"].notna()
    sub = g.loc[ok].copy()
    worst = sub.sort_values(["F15", "pop"], ascending=[True, False]).head(n)
    best = sub.sort_values(["F15", "pop"], ascending=[False, True]).head(n)
    far = sub.sort_values(["PT_city", "pop"], ascending=[False, False]).head(n)
    rows = []
    for kind, block in (("worst_F15", worst), ("best_F15", best), ("longest_walk", far)):
        for _, r in block.iterrows():
            rows.append(
                {
                    "city": r["city"],
                    "kind": kind,
                    "ward": r["locator"],
                    "lga": r.get("lganame"),
                    "pop": r["pop"],
                    "F15": r["F15"],
                    "F15_health": r.get("F15_health"),
                    "PT_city": r["PT_city"],
                }
            )
    return pd.DataFrame(rows)


def build(slugs: list[str] | None = None) -> pd.DataFrame:
    path = DATA_PROCESSED / "ward_f15_summary.csv"
    notes_path = DATA_PROCESSED / "ward_f15_notable.csv"
    table = pd.read_csv(path) if path.exists() else pd.DataFrame()
    notes = pd.read_csv(notes_path) if notes_path.exists() else pd.DataFrame()
    for slug in slugs or list(CITIES):
        if not (DATA_PROCESSED / f"{slug}_wards.gpkg").exists():
            continue
        if not (DATA_PROCESSED / f"{slug}_hexes.gpkg").exists():
            continue
        print(f"  {slug} …", flush=True)
        g = ward_f15(slug)
        ok = g["F15"].notna()
        populated = ok & (g["pop"].fillna(0) >= MIN_WARD_POP)
        use = g.loc[populated] if populated.any() else g.loc[ok]
        row = {
            "city": CITIES[slug].name,
            "wards": int(ok.sum()),
            "worst_ward": None if use.empty else use.loc[use["F15"].idxmin(), "locator"],
            "worst_F15": float(use["F15"].min()) if not use.empty else np.nan,
            "best_ward": None if use.empty else use.loc[use["F15"].idxmax(), "locator"],
            "best_F15": float(use["F15"].max()) if not use.empty else np.nan,
            "wards_under_50pct": int((g.loc[ok, "F15"] < 0.5).sum()),
        }
        if len(table):
            table = table[table["city"] != CITIES[slug].name]
        table = pd.concat([table, pd.DataFrame([row])], ignore_index=True)
        notable = _notable(g)
        if len(notes):
            notes = notes[notes["city"] != CITIES[slug].name]
        notes = pd.concat([notes, notable], ignore_index=True)
        table.to_csv(path, index=False)
        notes.to_csv(notes_path, index=False)
    return table


if __name__ == "__main__":
    import sys

    print(build(sys.argv[1:] or None).to_string(index=False))
