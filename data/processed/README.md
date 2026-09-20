# Processed layers

Hex grids, travel-time matrices, and metric tables. Gitignored until a small derived table is worth versioning.

`plate_metrics.csv` is F15 on the Lagos seven-LGA plate and the Abuja ten-ward plate, plus the areas those plates omit. Headline scores stay in `city_metrics.csv`.

`settlements.csv` is named GRID3 (and OSM village/hamlet) points clipped to each `{slug}_study_boundary.gpkg`. Coordinates only. Not drawn on the print plates. Per-city files are `{slug}_settlements.csv`.

`wpdx_metro_counts.csv` is WPdx water points clipped to metro LGAs (all vs `status_id=Yes`). Not a GRID3-quality urban inventory.
