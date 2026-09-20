# 15-minute cities — Nigeria

**Map:** [whizialfa.github.io/15-min-cities-nigeria](https://whizialfa.github.io/15-min-cities-nigeria/)

Adaptation of [Bruno, Melo, Campanelli & Loreto’s](https://doi.org/10.1038/s44284-024-00119-4) metrics (PT, F15, Gini, N\*) to five Nigerian urban centres. *Nature Cities* (2024). **This is not a replication.** Bruno’s protocol (GHS urban centres, nine OSM categories, dual access at n = 20, OSRM) is not a feasible headline here: OSM is not a POI census, n = 20 assumes dense substitutable amenities, and GHS-UCDB is not on disk. The atlas remains a baseline, not the result.

## Goal

Show which parts of the 15-minute metric survive in Lagos, Kano, Ibadan, Abuja and Port Harcourt once POIs, n, and the walk graph are local. Headline: GRID3 health and schools, dual access **n = 5**, OSM walk at 5 km/h, metro LGAs, completeness as a table. Bruno’s n = 20 is a stress test in `robustness.csv`, not a clone of their paper.

## Headline metrics

- `PT_k`: hexagon proximity time (mean of category dual-access times)
- `PT_city`: population-weighted mean of `PT_k`
- `F15`: share of population with `PT_k ≤ 15`
- `Gini(PT)`: inequality of person-level PT
- `N*`: facilities, optimally sited, to reach 90% coverage

Never report F15 without quoting `completeness.csv`. Print plates do not hatch the off-network region.

## Results

The write-up is [`notes/results.md`](notes/results.md). Colour PDF with the plates and charts: [`web/paper/fifteen_minute_access_nigeria.pdf`](web/paper/fifteen_minute_access_nigeria.pdf). Summary: [`notes/brief.md`](notes/brief.md). Five cities, OSM walk graph at 5 km/h, dual access to **n = 5** health and education POIs, GRID3/WorldPop NGA v3.0 population on 200 m hexes. Metro LGAs are the study boundary (not GHS urban centres); Abuja also includes Kubwa, Dutse and Usuma in Bwari. Area and density are measured on `{slug}_study_boundary.gpkg`.

| City | Area | Population | Density | PT_city | F15 | Gini | F15 health | F15 schools |
|---|---|---|---|---|---|---|---|---|
| Lagos | 969 km² | 8.69M | 8,965 /km² | 10.3 min | 85.4% | 0.346 | 75.2% | 91.2% |
| Ibadan | 126 km² | 1.22M | 9,659 /km² | 10.9 min | 82.1% | 0.310 | 81.9% | 79.5% |
| Kano | 573 km² | 5.78M | 10,092 /km² | 13.5 min | 67.2% | 0.291 | 55.9% | 74.4% |
| Port Harcourt | 336 km² | 2.33M | 6,946 /km² | 21.2 min | 30.7% | 0.272 | 24.7% | 47.1% |
| Abuja | 1,658 km² | 2.58M | 1,556 /km² | 29.8 min | 21.5% | 0.325 | 17.8% | 31.9% |

**F15 tracks density, and Port Harcourt is the exception that carries the argument.** The three cities above 8,900 people/km² all clear 67%. Abuja, at 1,556, comes last. Port Harcourt has respectable density at 6,946 and still reaches only 30.7%, because it holds 75 clinics per million people against Ibadan's 364.

**Four of five cities already own more clinics than an optimal layout needs.** `N*` is the number of optimally sited facilities required for 90% coverage on a 15-minute single-destination walk.

| City | N\* | Per 100k | Clinics held | What they cover |
|---|---|---|---|---|
| Ibadan | 58 | 4.7 | 445 | 92.4% |
| Port Harcourt | 115 | 4.9 | 175 | 66.1% |
| Kano | 119 | 2.1 | 465 | 89.2% |
| Abuja | 345 | 13.4 | 307 | 55.0% |
| Lagos | 327 | 3.8 | 2,303 | 90.0% |

Lagos spends 2,303 clinics to reach the same 90% that 327 well-placed ones would deliver. Port Harcourt's 175 reach 66% where 115 sited well would reach 90%. Where coverage fails, the binding constraint is siting, not scarcity — Abuja excepted, the only city where `N*` exceeds the existing stock.

**Health access is worse than school access in four of five cities**, so averaging the two into `PT_k` hides the weaker service. About **1.2 million under-5s across the five cities live beyond a 15-minute walk of a clinic** (Kano 426k, Abuja 313k, Lagos 233k, Port Harcourt 228k, Ibadan 31k).

**The choice-set size `n` dominates every other parameter.** At Bruno's n = 20, Abuja scores 0.1% and Port Harcourt 1.1%. That is a statement about the parameter, not the city, and the reason this repo is an adaptation rather than a replication. The manuscript is [`notes/results.md`](notes/results.md); the colour PDF with plates and charts is [`web/paper/fifteen_minute_access_nigeria.pdf`](web/paper/fifteen_minute_access_nigeria.pdf). Charts: `charts/f15_vs_density.png`, `charts/f15_by_n.png`, `charts/nstar_curves.png`.

| City | n=1 | n=5 | n=20 |
|---|---|---|---|
| Lagos | 94.9% | 85.4% | 49.1% |
| Ibadan | 93.9% | 82.1% | 43.6% |
| Kano | 92.0% | 67.2% | 20.7% |
| Port Harcourt | 74.4% | 30.7% | 1.1% |
| Abuja | 57.6% | 21.5% | 0.1% |

Walking speed matters nearly as much: at 3.5 km/h instead of 5, Kano falls from 67.2% to 43.0%. Quote `n` and the speed with any F15.

### Read these with the completeness table

"No access" and "not mapped" are different claims. Distance from each hexagon to the nearest walk-graph node:

| City | Median snap | Hexes off-network | Population off-network |
|---|---|---|---|
| Ibadan | 47 m | 0.7% | 0.1% |
| Port Harcourt | 56 m | 13.3% | 0.5% |
| Lagos | 67 m | 24.8% | 2.8% |
| Kano | 71 m | 18.6% | 0.9% |
| Abuja | 198 m | 45.2% | 3.1% |

**Abuja still has the farthest typical neighbourhood (198 m),** with 45.2% of hexagons off the mapped network holding 3.1% of people. Its 21.5% is part genuine sprawl and part missing street data. Lagos looks bad on hex share, but those hexagons are lagoon and hold 2.8% of people. Separately, OSM records under a fifth of GRID3's schools in every city, which is why GRID3 is primary and OSM a last-resort overlay.

## Reproducing

```bash
export PYTHONPATH="$PWD/.pydeps:$PWD/src"
export MPLCONFIGDIR="$PWD/.mplconfig"
P=/opt/anaconda3/bin/python3.12

$P -m proximity.pipeline                 # PT_k, F15, Gini, maps   → city_metrics.csv
$P -m proximity.completeness             # snap + POI mask         → completeness.csv
$P -m proximity.nstar lagos kano         # optimal siting          → nstar.csv
$P -m proximity.robustness               # n and speed sweeps      → robustness.csv
$P -m proximity.demographics             # underserved headcounts  → inclusive_f15_by_subgroup.csv
$P -m proximity.cartography              # re-render maps, no routing
$P -m proximity.charts                   # chart plates → charts/
```

Walk graphs are cached under `data/raw/{slug}_osm_walk.graphml`, so only the first run needs Overpass. Each module writes per city as it finishes rather than batching at the end — a long run that dies on the last city keeps the earlier ones.

## Layout

```
src/           analysis code
web/           MapLibre map (GitHub Pages root)
data/raw/      downloaded inputs (gitignored)
data/processed/ derived layers (gitignored unless tiny)
maps/          QGIS print plates
charts/        cross-city figures
notes/         paper and summary
notebooks/     exploration only; promote stable code into src/
references/    notes and citation keys — not copyrighted PDFs
```

## Environment

```bash
# packages currently live in .pydeps (venv creation is blocked on this Mac's sandbox)
export PYTHONPATH="$PWD/.pydeps:$PWD/src"
export MPLCONFIGDIR="$PWD/.mplconfig"
/opt/anaconda3/bin/python3.12 -m proximity.pipeline
/opt/anaconda3/bin/python3.12 -m proximity.web_layers   # GeoJSON for web/
cd web && python3 -m http.server 5173
```

Or open `notebooks/01_five_cities_hdx.ipynb`. HDX / WorldPop downloads need an unrestricted network (run that cell in Terminal or Jupyter on your machine).

Geospatial extras (`geopandas`, `rasterio`, osmnx) live in `.pydeps`. Headline population is GRID3–WorldPop **NGA v3.0** (`data/raw/NGA_population_v3_0_gridded.zip`). WorldPop 2020 constrained is an optional comparison raster (`pop_layer=1`), not a Bruno clone. Rasters are not committed.

HDX / Overpass still need an unrestricted network on your machine. The pipeline no longer tries to fetch WorldPop.org on every run.

## Source of the metrics

Bruno et al. (2024) is the source of PT, F15, Gini and N\*, not the protocol we run. [doi:10.1038/s44284-024-00119-4](https://doi.org/10.1038/s44284-024-00119-4) · [arXiv:2408.03794](https://arxiv.org/abs/2408.03794) · [atlas](https://whatif.sonycsl.it/15mincity/) (Lagos idcity=4800).
