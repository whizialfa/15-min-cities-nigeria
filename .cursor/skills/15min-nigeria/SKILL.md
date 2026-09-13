---
name: 15min-nigeria
description: >-
  Replicates and adapts Bruno et al. 2024 inclusive 15-minute cities for Nigerian
  urban centres. Use when computing proximity time, F15, Gini(PT), N*, hex maps,
  OSM completeness, or Lagos/Kano/Ibadan/Abuja/Port Harcourt accessibility.
---

# 15-minute cities — Nigeria

## Default stance

The Sony CSL atlas is a **baseline**, not the finding. Observed F15 from OSM is **mapped** 15-minuteness. Lead with density / N\* when POI data are thin.

## Layer 1 (faithful)

- Boundary: GHS Urban Centre (not whole Lagos State unless it is a robustness run)
- Population: WorldPop 100 m UN-adjusted
- Grid: hexagons, 200 m side
- Dual access: mean OSRM walk time to **n = 20** POIs per category
- `PT_k`: unweighted mean of 9 categories
- `PT_city`: population-weighted mean of `PT_k`
- `F15`: population share with `PT_k ≤ 15`
- Sensitivity: do **not** drop hexagons with no nearby POIs without reporting how many people that removes

## Layer 2 (Nigeria-adjusted)

- Smaller n for non-substitutable services (schools, clinics)
- Add markets, water, worship, chemist/primary care, POS, danfo/BRT
- Paratransit time surface in addition to walking
- Completeness mask on every F15 map

## Maps

Every hex choropleth: metric name, units (minutes), mode (foot/bike/danfo), data vintage, city boundary definition. Export under `maps/`.

## Do not

- Treat atlas red Lagos cells as proof of no local services
- Commit raw OSM/WorldPop rasters
- Put this analysis in `~/paper-replications`
