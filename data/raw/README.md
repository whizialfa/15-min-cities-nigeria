# Raw inputs

Keep downloads here. They are gitignored.

This pass:

- WorldPop 2020 constrained 100 m (`nga_ppp_2020_constrained.tif`) — optional comparison
  raster, symlink from `Documents/GeoDev Lab/data/raw/fct_fetch/`. National raster despite
  the FCT folder name.
- GRID3 / WorldPop NGA v3.0 (`NGA_population_v3_0_gridded.tif`) — headline
  people layer (NMEP 2022–23, UN WPP July 2025). Download:
  `https://data.worldpop.org/repo/wopr/NGA/population/v3.0/NGA_population_v3_0_gridded.zip`
- GRID3 / WorldPop Research Group v1.2 — legacy fallback only.
- WorldPop 100 m UN-adjusted 2020 (`nga_ppp_2020_UNadj.tif`) — **not local**. Pipeline
  prefers it automatically if you add it later.
- GRID3 health facilities v3.0 — 24 operational states (not Lagos or Rivers)
- GRID3 health facilities v2.0 (Nov 2024, all states) — symlink from
  `Documents/Portfolio/Projects/Healthcare Demand Pressure/.../GRID3_NGA_health_facilities_v2_0.shp`.
  Default for Lagos and Port Harcourt.
- GRID3 education / schools (HDX)
- Water Point Data Exchange Nigeria (`wpdx_water_points_nga.csv`) — HDX `wpdx_nga`.
  Rural wells/springs/tapstands with functional status. Clip to metro LGAs before using.
- NMIS water facilities (`nmis_water_facilities.csv`) — surveys 2009–2012, functional flag.
  Denser than WPdx in most metros but stale; completeness overlay, not a headline layer.
- GRID3 national POI caches (`grid3_markets.gpkg` 11,129 · `grid3_churches.gpkg` 33,103 ·
  `grid3_mosques.gpkg` 22,379) — paged from the GRID3 ArcGIS feature services by
  `proximity.grid3_poi`. Delete a file to force a refresh. Churches and mosques are only
  ever used merged as *worship*; separately they track religious composition, not access.
  GRID3 police (802), fire (44) and post offices (225) are collection gaps, not censuses.
- Overture Maps places (`overture_food_retail.gpkg` 2,661 · `overture_pharmacy.gpkg`) —
  release 2026-07-22.0, streamed from S3 by `proximity.overture` via DuckDB. CDLA-Permissive
  with per-record `confidence` (median 0.61) and source attribution, so these may ship.
- GRID3 operational/vaccination wards — symlinked from `Documents/Portfolio/Data`; see
  `proximity.wards` for the `ward_label` / `name_quality` handling of Rivers placeholders.
- OCHA COD-AB Nigeria (locator / admin clip)

Not downloaded (too large for this pass):

- GRID3 settlement extents v4.1 (~2 GB)
- Full GHS-UCDB R2024A (~1.7 GB)

Urban extent is the metro-LGA dissolve in `cities.py`. GHS Urban Centre polygons are not on disk and are not the headline boundary.
