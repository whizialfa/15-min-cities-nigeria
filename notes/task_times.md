# Task times

Wall-clock times for work Wisdom asked for. Local time on this machine. Stage seconds are `time.perf_counter` unless noted.

Earlier ships in this repo (plates, academic paper, streets layer) were not timed. Timing starts here.

## 2026-09-20 — Kubwa on the Abuja plate

Cut is AMAC plus Kubwa, Dutse and Usuma only. Not the rest of Bwari (Kawu, Igu, Shere).

- `2026-09-20 20:38 WAT` start **Kubwa plate rebuild** — code cut, hexes, walk graph, N*, QGIS plates, study-area map, paper numbers

### Pipeline
- `2026-09-20 20:46:24 WAT` start **abuja cut check**
- `2026-09-20 20:46:25 WAT` done **abuja cut check** in **0.0 min** (1 s) — 1658 km², wards ['Usuma', 'Kubwa', 'Dutse']
- `2026-09-20 20:46:25 WAT` start **abuja wards**
- `2026-09-20 20:46:25 WAT` done **abuja wards** in **0.0 min** (1 s) — 14 wards
- `2026-09-20 20:46:25 WAT` start **abuja pipeline** — reuse_hexes=False, OSM walk refetch
- `2026-09-20 21:09:52 WAT` done **abuja pipeline** in **10.2 min** (612 s analyse_city; **23.4 min** wall including GRID3 load)
  - 16,412 hexes (4.6 s); population 30.6 s; OSM walk graph 99 MB; walk dual access 568.9 s
  - headline F15 **21.5%**, PT 29.8 min, 2.58M people, 307 clinics, 582 schools
  - Euclidean F15 47.1% (sensitivity only; do not quote)


### Scores after hexes
- `2026-09-20 21:11:30 WAT` start **abuja plate_metrics**
- `2026-09-20 21:11:31 WAT` done **abuja plate_metrics** in **0.0 min** (1 s)
  - plate 10 wards: 2.02M, F15 **24.7%**, PT 26.3 min
  - AMAC only: 2.10M, F15 17.0%
  - metro AMAC+Kubwa+Dutse+Usuma: 2.58M, F15 **21.5%**

- `2026-09-20 21:11:31 WAT` start **abuja completeness**
- `2026-09-20 21:15:00 WAT` done **abuja completeness** in **3.5 min** (209 s)
- `2026-09-20 21:15:00 WAT` start **abuja walk inventory**
- `2026-09-20 21:16:50 WAT` done **abuja walk inventory** in **1.8 min** (110 s)
- `2026-09-20 21:16:50 WAT` start **abuja places** — Overpass refresh
- `2026-09-20 21:21:32 WAT` done **abuja places** in **3.0 min** (181 s)

### QGIS plates
- `2026-09-20 21:23:08 WAT` start **abuja QGIS PT+pop plates** — furniture-aware centre on 10 wards
- `2026-09-20 21:24:54 WAT` done **abuja QGIS PT+pop plates** in **1.8 min** (106 s)
- `2026-09-20 21:24:54 WAT` start **abuja QGIS study-area plate**
- `2026-09-20 21:31:30 WAT` done **abuja QGIS study-area plate** in **6.6 min** (396 s)

### Robustness and N*
- `2026-09-20 21:23:12 WAT` start **abuja robustness**
- `2026-09-20 21:31:27 WAT` done **abuja robustness** in **8.3 min** (499 s) — n=5 F15 21.5%; n=20 F15 0.1%; 3.5 km/h F15 8.7%
- `2026-09-20 21:33:30 WAT` start **abuja N***
- `2026-09-20 21:36:12 WAT` done **abuja N*** in **2.0 min** (120 s) — N* **345** against 307 clinics (13.4 per 100k, cover 55.0%)

### Equity, under-fives, web map
- `2026-09-20 21:33:36 WAT` start **abuja ward F15**
- `2026-09-20 21:33:37 WAT` done **abuja ward F15** in **0.0 min** (1 s)
- `2026-09-20 21:33:37 WAT` start **abuja under-five headcounts**
- `2026-09-20 21:33:47 WAT` done **abuja under-five headcounts** in **0.2 min** (10 s)
- `2026-09-20 21:33:47 WAT` start **abuja web map export**
- `2026-09-20 21:36:36 WAT` done **abuja web map export** in **2.1 min** (128 s)
- `2026-09-20 21:43:51 WAT` start **reprint colour paper PDF**
- `2026-09-20 21:44:25 WAT` done **reprint colour paper PDF** in **0.6 min** (34 s)
- `2026-09-20 21:44:25 WAT` start **reprint brief PDF**
- `2026-09-20 21:44:42 WAT` done **reprint brief PDF** in **0.3 min** (17 s)
- `2026-09-20 21:44 WAT` done **Kubwa plate rebuild** — headline F15 21.5%, plate 24.7%, N* 345, Kubwa on the maps

- `2026-09-20 21:43:53 WAT` start **reprint colour paper PDF**
- `2026-09-20 21:44:25 WAT` done **reprint colour paper PDF** in **0.5 min** (33 s)
- `2026-09-20 21:44:25 WAT` start **reprint brief PDF**
- `2026-09-20 21:44:42 WAT` done **reprint brief PDF** in **0.3 min** (17 s)
- `2026-09-20 22:50:47 WAT` start **settlement inventory** — GRID3 points plus OSM villages, clipped to study outlines
- `2026-09-20 22:54:14 WAT` done **settlement inventory** in **3.4 min** (207 s) — slug; abuja             379; ibadan            324; kano             5085; lagos            1094; port_harcourt     197
- `2026-09-20 22:55:13 WAT` start **web map settlements** — attach nearest settlement names to hex/ward popups
- `2026-09-20 22:58:50 WAT` done **web map settlements** in **3.6 min** (216 s) — /Users/atimakaduh/Documents/Portfolio/Paper replicas/15-min-cities-nigeria/web/data/metrics.json

- `2026-09-20 23:14:31 WAT` start **reprint PDFs with villages** — Dakwa, Dei-Dei, Banana Island, Eneka in colour paper and brief
- `2026-09-20 23:14:40 WAT` start **reprint colour paper PDF**
- `2026-09-20 23:15:03 WAT` done **reprint colour paper PDF** in **0.4 min** (23 s) — copied to web/paper/
- `2026-09-20 23:15:16 WAT` start **reprint brief PDF**
- `2026-09-20 23:15:35 WAT` done **reprint brief PDF** in **0.3 min** (19 s)
- `2026-09-20 23:15:35 WAT` done **reprint PDFs with villages** in **1.1 min** (64 s from pandoc)

- `2026-09-20 23:27:00 WAT` start **search settlements** — Find a place indexes every stored village
- `2026-09-20 23:32:24 WAT` done **settlements_search.json** — 7,079 points
- `2026-09-20 23:42:22 WAT` done **search settlements** — Dakwa, Dei-Dei, Eneka fly the map
- `2026-09-21 00:24:16 WAT` start **settlement inventory** — GRID3 points plus OSM villages, clipped to study outlines
- `2026-09-21 00:25:05 WAT` done **settlement inventory** in **0.8 min** (50 s) — slug; abuja             431; ibadan            332; kano             5089; lagos            1125; port_harcourt     203
- `2026-09-21 00:25:30 WAT` start **settlement inventory** — GRID3 points plus OSM villages, clipped to study outlines
- `2026-09-21 00:25:38 WAT` done **settlement inventory** in **0.1 min** (7 s) — slug; abuja             431; ibadan            332; kano             5089; lagos            1125; port_harcourt     203
- `2026-09-21 00:24:16 WAT` start **OSM junctions** — named junctions and roundabouts into the search inventory
- `2026-09-21 00:25:38 WAT` done **OSM junctions fetch** — Lagos 31, Abuja 52, Ibadan 5, Port Harcourt 6, Kano 4
- `2026-09-21 00:27:17 WAT` start **settlement inventory** — drop plus-code and close/lane names
- `2026-09-21 00:27:23 WAT` done **settlement inventory** in **0.1 min** (6 s) — 7,174 points; junctions Lagos 28, Abuja 50, Ibadan 5, Port Harcourt 5, Kano 4
- `2026-09-21 00:27:17 WAT` start **settlement inventory** — GRID3 points plus OSM villages, clipped to study outlines
- `2026-09-21 00:27:23 WAT` done **settlement inventory** in **0.1 min** (6 s) — slug; abuja             429; ibadan            332; kano             5089; lagos            1122; port_harcourt     202
