# Inclusive 15-minute cities — Nigeria

Child repo for replicating (then adapting) Bruno, Melo, Campanelli & Loreto, *A universal framework for inclusive 15-minute cities*, Nature Cities (2024).

Parent catalog: `~/paper-replications`.

## Goal

1. **Layer 1 — faithful clone.** Same hexes, dual-access PT, F15, Gini, N\* on GHS urban centres (Lagos, Kano, Ibadan, Abuja, Port Harcourt). Treat the authors’ [atlas](https://whatif.sonycsl.it/15mincity/) as a baseline, not the result.
2. **Layer 2 — Nigeria-adjusted.** Local POI layers, smaller choice sets for non-substitutable services, paratransit times, category weights. Report mapped access separately from lived access.

## Headline metrics

- `PT_k`: hexagon proximity time (mean of category dual-access times)
- `PT_city`: population-weighted mean of `PT_k`
- `F15`: share of population with `PT_k ≤ 15`
- `Gini(PT)`: inequality of person-level PT
- `N*`: POIs per 1,000 people, optimally sited, to reach F15 = 90%

Never report F15 without a completeness / unmapped-hexagon layer.

## Layout

```
src/           analysis code
data/raw/      downloaded inputs (gitignored)
data/processed/ derived layers (gitignored unless tiny)
maps/          figure exports
notebooks/     exploration only; promote stable code into src/
references/    notes and citation keys — not copyrighted PDFs
```

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Geospatial extras (`geopandas`, `rasterio`, OSRM) land in later commits once Layer 1 starts.

## Source paper

Bruno et al. (2024). [doi:10.1038/s44284-024-00119-4](https://doi.org/10.1038/s44284-024-00119-4) · [arXiv:2408.03794](https://arxiv.org/abs/2408.03794)
