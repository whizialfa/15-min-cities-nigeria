"""Headline metrics from Bruno et al. 2024."""

from __future__ import annotations

import numpy as np
import pandas as pd


def gini(values: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Population-weighted Gini of proximity time."""
    x = np.asarray(values, dtype=float)
    w = np.ones_like(x) if weights is None else np.asarray(weights, dtype=float)
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x, w = x[ok], w[ok]
    if x.size == 0 or w.sum() == 0:
        return float("nan")
    order = np.argsort(x)
    x, w = x[order], w[order]
    if x[-1] == 0:
        return 0.0
    cumw = np.cumsum(w)
    cumxw = np.cumsum(w * x)
    # Discrete weighted Gini (Lorenz)
    return float(np.sum(cumxw[1:] * cumw[:-1] - cumxw[:-1] * cumw[1:]) / (cumxw[-1] * cumw[-1]))


def city_metrics(hexes, pt_col: str = "PT_k", pop_col: str = "pop") -> dict:
    """PT_city, F15, Gini(PT). Never drop no-POI hexes silently."""
    df = hexes.drop(columns="geometry", errors="ignore")
    pop = df[pop_col].fillna(0).to_numpy(dtype=float)
    pt = df[pt_col].to_numpy(dtype=float)
    mapped = np.isfinite(pt)
    pop_total = float(pop.sum())
    pop_mapped = float(pop[mapped].sum())
    pt_city = float(np.average(pt[mapped], weights=pop[mapped])) if pop_mapped else float("nan")
    f15 = float(pop[mapped & (pt <= 15)].sum() / pop_mapped) if pop_mapped else float("nan")
    return {
        "n_hex": int(len(df)),
        "n_hex_mapped": int(mapped.sum()),
        "pop_total": pop_total,
        "pop_mapped": pop_mapped,
        "pop_unmapped_share": 1 - (pop_mapped / pop_total) if pop_total else float("nan"),
        "PT_city": pt_city,
        "F15": f15,
        "Gini_PT": gini(pt, pop),
    }


def metrics_table(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)
