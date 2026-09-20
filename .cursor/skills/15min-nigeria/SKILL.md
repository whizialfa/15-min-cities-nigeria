---
name: 15min-nigeria
description: >-
  Adapts Bruno et al. 2024 PT/F15/Gini/N* metrics to Nigerian urban centres. Not
  a replication. Use when computing proximity time, F15, Gini(PT), N*, hex maps,
  OSM completeness, or Lagos/Kano/Ibadan/Abuja/Port Harcourt accessibility.
---

# 15-minute cities — Nigeria (adaptation)

## Default stance

This is **not** a Nature Cities clone. GRID3 health/education on metro LGAs, dual access **n = 5**, OSM walk at 5 km/h. Quote F15 from `city_metrics.csv` walk rows (`network=walk`, `n_required=5`). Plate cuts (Lagos seven LGAs; Abuja seven AMAC wards plus Kubwa, Dutse and Usuma) live in `plate_metrics.csv` and are never the metro headline. Never quote Euclidean F15 as a result. Never drop no-POI hexes silently. Do not add the rest of Bwari (Kawu, Igu, Shere).

The Sony CSL atlas is a **baseline**, not the finding. Observed F15 is **mapped** 15-minuteness. Lead with density / N\* when POI data are thin.

Write-up: `notes/results.md`. Summary: `notes/brief.md` (PDF: `notes/fifteen_minutes_on_foot.pdf`). Colour PDF: `notes/fifteen_minute_access_nigeria.pdf`. All five cities on the walk graph (`data/processed/city_metrics.csv`): Lagos F15 85.4% (PT 10.25), Ibadan 82.1% (10.91), Kano 67.2% (13.45), Port Harcourt 30.7% (21.22), Abuja 21.5% (29.77). F15 tracks population density almost everywhere — the three cities above 8,900 people/km² all clear 67%, Abuja at 1,556/km² sits last. **Port Harcourt is the one city that breaks the pattern** and is therefore the interesting case: 6,946 people/km² but only 30.7%, because it carries 75 health facilities per million against Ibadan's 364. That is inventory and siting, not density. Area and density are measured on `{slug}_study_boundary.gpkg` (Lagos 969 km², Ibadan 126 km², Kano 573 km², Port Harcourt 336 km², Abuja 1,658 km²).

## This is not a replication

Bruno’s published protocol (GHS urban centres, nine OSM categories, dual access at n = 20, OSRM) is **not feasible** here and is not the claim. OSM is not a POI census; n = 20 assumes dense substitutable amenities; GHS-UCDB is not on disk. Keep this repo titled and described as an **adaptation**. Do not put the analysis in `~/paper-replications`. Do not rename the GitHub slug (`15-min-cities-nigeria`).

## Headline protocol

- Boundary: metro LGAs in `cities.py` (Ibadan is the **core 5** LGAs, not 11). Abuja is AMAC plus the built-up Bwari wards Kubwa, Dutse and Usuma (`EXTRA_STUDY_WARDS`), not the rest of Bwari. GHS Urban Centre is a missing sensitivity, not a clone of Bruno.
- Grid: hexagons, 200 m side (`hexgrid.py`) — same geometry Bruno used.
- `PT_k`: unweighted mean of the category dual-access times that exist in that hex
- `PT_city`: population-weighted mean of `PT_k`
- `F15`: population share with `PT_k ≤ 15`
- Sensitivity: do **not** drop hexagons with no nearby POIs without reporting how many people that removes
- Population: GRID3 / WorldPop `NGA_population_v3.0` (NMEP 2022–23, scaled to UN WPP July 2025). WorldPop 2020 constrained is an optional comparison raster (`pop_layer=1`), not a Bruno clone.
- Dual access **n = 5** for schools/clinics (headline). n = 1 primal and n = 20 Bruno stress test stay available.
- Walk headline: OSM **walk** graph at 5 km/h (not Euclidean). Euclidean stays as `PT_eucl`. Euclidean overstates F15 everywhere, and worst where the street network is most broken: Lagos 95.5% → 85.4%, Ibadan 92.8% → 82.1%, Kano 82.2% → 67.2%, Abuja 47.1% → 21.5%, Port Harcourt 68.5% → 30.7%. Never quote `F15_eucl` as a result.
- Walk `PT_k` is the only headline result. Car grades A/B/C are **off by default** (`run(..., with_car=True)` to revive) and are not map layers: POIs are dense enough that car time barely discriminates. Never mix car into walk `PT_k`.
- Health: GRID3 v3 where it exists (Kano, Ibadan, Abuja); GRID3 v2 for Lagos and Port Harcourt. OSM is a last-resort overlay.
- Add markets, water, worship, chemist/primary care, POS, danfo/BRT
- Paratransit time surface in addition to walking
- Quote completeness with every F15. Do not hatch or tint the plates for it.

## N*

`proximity.nstar` needs only population + walk graph, so it is immune to POI completeness — lead with it where inventories are thin. Candidates are hex centroids snapped to the walk graph; coverage is a 15-minute single-destination walk; the set is chosen greedily (within 1 - 1/e of optimal, so N* is an **upper bound** on the true minimum). Compare it against `observed_coverage()`, never against F15 — F15 is the n=5 dual-access mean and is not the same rule.

All five cities, health, 90% target (`data/processed/nstar.csv`). `N*/have` is the optimal count over the existing stock:

| City | N\* | per 100k | existing | they cover | N\*/have |
|---|---|---|---|---|---|
| Ibadan | 58 | 4.7 | 445 | 92.4% | 0.13 |
| Port Harcourt | 115 | 4.9 | 175 | 66.1% | 0.66 |
| Kano | 119 | 2.1 | 465 | 89.2% | 0.26 |
| Abuja | 345 | 13.4 | 307 | 55.0% | **1.12** |
| Lagos | 327 | 3.8 | 2,303 | 90.0% | 0.14 |

**Four of the five cities already own more clinics than an optimal plan needs** — Lagos reaches the same 90% with 327 sites that it currently spends 2,303 on. Where coverage still fails, the cause is siting, not scarcity. Port Harcourt is the sharpest case: 115 well-placed clinics would beat the 175 it has, which reach only 66%.

**Abuja is the sole exception and the only city where N\* exceeds the existing stock.** It needs 345 against 307 held, at 13.4 per 100k — nearly three times any other city — because population is spread over 1,658 km². Read that number next to the completeness mask: 45.2% of Abuja's hexes are off the mapped walk network, so part of the gap is unmapped street, not absent clinic.

N\* per 100k is an inverse density reading: Kano 2.1 (compact) through to Abuja 13.4 (sprawled). It assumes a facility can be sited at any hex centroid on the walk graph, so it ignores land, cost and catchment capacity — it is a floor on siting efficiency, not a build plan.

## Robustness

`proximity.robustness` → `data/processed/robustness.csv`. One unbounded Dijkstra per city serves every n; five cities in 12 minutes.

**Choice-set size `n` dominates every other parameter.** F15 at 5 km/h:

| City | n=1 | n=5 | n=20 |
|---|---|---|---|
| Lagos | 94.9% | 85.4% | 49.1% |
| Ibadan | 93.9% | 82.1% | 43.6% |
| Kano | 92.0% | 67.2% | 20.7% |
| Port Harcourt | 74.4% | 30.7% | 1.1% |
| Abuja | 57.6% | 21.5% | 0.1% |

**At Bruno's n = 20, Abuja scores 0.1% and Port Harcourt 1.1%.** That is a statement about the parameter, not the city: n = 20 presumes dense substitutable amenities and does not transfer. This is the empirical case for the n = 5 headline — make the argument with this table, not by assertion. Do not present n = 20 as the result.

**5 km/h is an optimistic walk.** Dropping to 3.5 km/h costs Lagos 17 points, Abuja 13, Port Harcourt 21, Kano 24 (67.2% → 43.0%). Given heat, footpath quality and flooding, quote the speed with every F15 and treat 3.5–4.5 km/h as the honest lower band.

Euclidean bias widens with n where the network is good (Lagos +3.8 / +10.2 / +31.0 points at n = 1/5/20). It appears to *shrink* at n = 20 in Port Harcourt and Abuja only because both measures are pinned near zero — a floor artefact, not agreement.

## Inclusive access

`proximity.demographics` → `data/processed/inclusive_f15_by_subgroup.csv`.

**Do not report subgroup F15 rates from GRID3/WorldPop v3.0.** Its age-sex grids are the total grid times a constant applied at *state* level, so inside a metro polygon the subgroup share of a pixel has min == max and a standard deviation near 1e-9. A constant re-weighting cannot shift a population-weighted mean, so subgroup F15 is identically equal to total F15 for the same service. The first version of this module reported 0.24666757 for Port Harcourt's under-5s, women 15–49 and over-65s alike and read like a finding; it was arithmetic. Between-city shares are real and usable (under-5s are 16.7% of Kano against 10.8% of Lagos) — only the within-city gradient is missing. Real subgroup rates need DHS clusters or ward-level census.

What the grids do support is **underserved headcounts**, which is the more useful framing anyway. Roughly **1.2 million under-5s across the five cities live beyond a 15-minute walk of a clinic** (Kano 426k, Abuja 313k, Lagos 233k, Port Harcourt 228k, Ibadan 31k).

Splitting `PT_k` into its two services is where the real signal was hiding — **health is worse than schools in four of five cities**:

| City | PT_k | health only | schools only |
|---|---|---|---|
| Lagos | 85.4% | 75.2% | 91.2% |
| Ibadan | 82.1% | 81.9% | 79.5% |
| Kano | 67.2% | 55.9% | 74.4% |
| Port Harcourt | 30.7% | 24.7% | 47.1% |
| Abuja | 21.5% | 17.8% | 31.9% |

Port Harcourt has the widest gap at 22 points. Ibadan is the only city where schools are the weaker service, and it is also the only one holding roughly as many clinics as schools (445 vs 453). Averaging the two into `PT_k` hides all of this — quote the split.

## Completeness

`proximity.completeness` writes `data/processed/completeness.csv`. Two signals, both needed before any F15 is quoted.

**Street network** — distance from hex centroid to the nearest walk-graph node (`SNAP_WARN_M = 250`). Ibadan is the cleanest mapped city (median 47 m, p90 121 m, 0.7% of hexes off-network). Lagos looks bad by hex share (24.8%) but those hexes hold 2.8% of people — lagoon and empty land, not a mapping gap. **Abuja is still the warning: median snap 198 m, p90 15.6 km, 45.2% of hexes off-network holding 3.1% of the population.** Abuja's F15 of 21.5% is therefore part genuine sprawl and part unmapped street network, and must never be quoted bare.

**POI inventory** — OSM under-records schools everywhere: ratios against GRID3 over the same bbox run 0.066 (Ibadan), 0.079 (Lagos), 0.119 (Abuja), 0.173 (Port Harcourt), 0.193 (Kano). OSM is under a fifth of GRID3 in every city, which confirms the existing policy — GRID3 primary, OSM last-resort overlay — rather than showing a north–south bias. If anything the ratio runs the other way, because GRID3 itself records far more (largely private) schools in the south.

## Maps

Print plates follow the personal `publication-maps` skill (A3 furniture, no overlap, snug legend with even inset, plain-language title/footnote). This section is the Nigeria-specific colour and rebuild protocol.

QGIS plates (`qgis/build_city_project.py` → `maps/{slug}_PT_k_plate.png` and `{slug}_pop_plate.png`): landscape A3, OSM under the hexes, study boundary + wards only. No metro LGA fill, no completeness hatch. Titles are `WALKING ACCESS IN {CITY}` / `To clinics and schools` and `POPULATION IN {CITY}` / `People in each neighbourhood`. Legend headers `Minutes on foot` and `People per hexagon`; class labels are the range only. Footnote is three sentences, 12 pt Bold. Credit `©Wisdom Akpabio`. Rebuild with QGIS's `python3.9` and `env -u PYTHONPATH`. Rebuild **all five** after a furniture change.

Matplotlib hex choropleths still need: metric name, units (minutes), mode (foot/bike/danfo), data vintage, city boundary definition. Export under `maps/`.

Rebuild those with `proximity.cartography.rebuild_pt_maps()` — it reads the saved hexes and metrics and never re-routes, so map edits cost seconds, not hours. Three conventions are baked in and should not be undone:

- **Minute metrics use the six fixed nominal classes in `proximity.classes`**, never natural breaks: Very close (≤5) · Close (5–10) · Moderate (10–15) · Far (15–30) · Very far (30–60) · Extremely far (60+), green through amber and red to dark maroon. One definition, imported by both `cartography` and `qgis/build_city_project.py`. 15 is an edge, so classes 1–3 sum to F15. PT and population fills are **80%** opaque (alpha 204).
- **Keep the 60 edge.** Without it everything above 30 min is one class holding 45.3% of Abuja and spanning a half-hour walk to a four-hour one — least discriminating in the two cities whose access failure is the whole story. Split: Abuja 36.0/9.3, Port Harcourt 13.6/2.2. Near-empty in the dense cities (Lagos 0.4%, Kano 0.0%) **by design** — in a fixed cross-city scheme "nobody in Kano is over an hour from a clinic" is a result, not wasted resolution. This is the reverse of the `pop` case, where fixed classes fitted elsewhere left Ibadan two empty rungs and told you nothing.
- **Non-minute metrics use Jenks fitted per city, then rounded**, on the original ColorBrewer YlOrRd ramp in QGIS (`_rounded_jenks`). Pretty breaks space on the value range, so Lagos (max ~9,000) jumped in 2,000s and went uniformly pale. Rounding Jenks cuts (422→400) keeps a readable legend without that flattening. A shared ladder emptied classes (Ibadan had nothing above 3,000).
- **The completeness mask is texture, never tint — and not on the QGIS plates.** If a separate matplotlib mask figure is needed, hatch the dissolved off-network region (1 m buffer before union) rather than veiling the ramp. Quote `completeness.csv` with every F15; Abuja is the warning (45.2% of hexes off-network).
- The matplotlib colourbar label sits **above** the bar; its ticks used to collide with the vintage line.

Mask coverage as shipped: Ibadan 0.7% of hexes, Port Harcourt 13.3%, Kano 18.6%, Lagos 24.8% (Lekki and the lagoon fringe — 2.8% of people), Abuja 45.2%.

Plates do **not** draw metro LGAs. Wards stay as outlines: GRID3 operational/vaccination wards clipped to the metro LGAs (`{slug}_wards.gpkg` via `proximity.wards`). **Print labels are OSM named places** (`{slug}_places.gpkg` via `proximity.places`): `place=suburb|quarter|neighbourhood` plus named residential — Apo, Lokogoma, Ikoyi, Sangotedo, Kubwa. Helvetica 14 pt, `PreventOverlap`. Pinned names win PAL priority. A separate settlement inventory (`proximity.settlements` → `data/processed/settlements.csv`) lists GRID3 named settlements, OSM villages, and named OSM junctions as points for popups, prose and the live-map search box (Dakwa, Dei-Dei, Berger). Junctions are search-only: they do not become hex or ward Place names and they are not drawn on print plates. The Find-a-place control indexes `web/data/settlements_search.json` (every stored study-outline point) and flies to it. Do not draw those points on the print plates. **Abuja plates draw ten wards** — Gwarinpa, Wuse, Nyanya, Karu, City Centre, Garki, Kabusa, plus Kubwa, Dutse and Usuma in Bwari — as the black outline and the hex clip. Not AMAC, not Gui/Orozo/Gwagwa/Jiwa, not the rest of Bwari. **Lagos plates draw seven LGAs** — Eti-Osa, Lagos Island, Apapa, Lagos Mainland, Surulere, Mushin, Shomolu — not the 16-LGA metro. Stroke 0.22 mm, `90,84,78,165`. Rivers wards with no settlement name keep `PH 6` in the data.

State LGAs (`{slug}_state_lgas.gpkg`) remain in the `.qgz` for the canvas, subset so metro names are not labelled twice. They are not print-plate overlays.

Rebuild **all five** `.qgz` after any pipeline run, never just the city that changed. Staleness is silent. Abuja went two days serving a project labelled `n=20` with labelling switched off entirely, while the data underneath had moved to walk `n=5`.

## POI basket evidence

GRID3 markets and worship (churches + mosques merged) are pulled nationally by `proximity.grid3_poi` and **polygon-clipped** to metro LGAs. Reach test (`--reach`, Euclidean upper bound): markets fail `n = 5` everywhere but Lagos (Kano F15 5%, PH 0%) because GRID3 markets are formal markets — lumpy, not substitutable. Worship holds at n=5 only in Lagos. Police, fire and post-office layers are collection gaps, not censuses — do not use.

`proximity.overture` merges GRID3 markets with Overture food retail (2,661 national: grocery, supermarket, convenience, farmers/flea market, butcher). The two sources barely overlap — only 9 duplicates in Lagos at 150 m — so they genuinely count different things and merging is additive. Combined **food** roughly doubles coverage (Lagos F15 46.8% to 76.3%, PH 0% to 44.8%) but still fails Kano (11.9%). Overture pharmacies are too thin outside Lagos to use. Overture is CDLA-Permissive and shippable; Google Places is not, at any project size.

Overture has an urban digital-footprint bias: Lagos 874 food points vs Kano 83, for 8.7M and 4.7M people. That gap is coverage, not reality — mask it, don't report it as access.

Hex grids must match the current metro boundary. Both stale grids are now rebuilt: Abuja on the current AMAC boundary (14,635 hexes, was 24,681) and Ibadan on the core-5 boundary (1,331 hexes, was 14,351). All five cities are routed on the OSM walk graph; graphs are cached as `data/raw/{slug}_osm_walk.graphml`, so a rerun never re-hits Overpass.

Ibadan is the **core 5 LGAs only** (126 km², 1.22M, 9,659 people/km²), not the 11-LGA metropolitan area. The 6 peri-urban LGAs add 2,746 km² of mostly bush at 1,455 people/km² and would drop the city to 1,790/km², recreating the Abuja dilution on a ~27,600-hex grid. Egbeda (2,985/km²) is the only defensible addition if the scope is ever revisited.

Abuja is the one city where the metro LGA is mostly not city: the study outline is AMAC plus Kubwa, Dutse and Usuma (1,658 km² at 1,556 people/km²), against 6,946 (Port Harcourt) to 10,092 (Kano). Empty AMAC hexes still dominate the choropleth. This does **not** bias `F15`, which is population-weighted, but it does dominate the hex map, so the Abuja plate is the ten lived-in wards. Treat that as cartography to fix, not a metric to correct. Do not add the rest of Bwari.

## Task times

Log wall-clock time for rebuilds and other work Wisdom asks for in `notes/task_times.md` (`proximity.timing`). Stage seconds on this machine, not estimates.

## Do not

- Call this a replication of Bruno et al. 2024
- Treat atlas red Lagos cells as proof of no local services
- Commit raw OSM/WorldPop rasters
- Put this analysis in `~/paper-replications`
