# Named settlements in the study outlines

Coordinate list of populated places inside each city’s **study boundary**, not the print-plate clip. Points only. They are not drawn on the QGIS plates. Nearest name is attached to the web-map hex and ward popups. The live map **Find a ward, village or place** box indexes every stored point and flies to it.

Source: GRID3 settlement points (eHealth Africa / GRID3, 2021; CC BY 4.0), clipped to `{slug}_study_boundary.gpkg`. OSM `place=town|village|hamlet|locality` is a fill where Overpass answered. Rebuild: `python -m proximity.settlements`.

Tables: `data/processed/settlements.csv` (all five), `{slug}_settlements.csv`, `settlements_summary.csv`. Points: `{slug}_settlements.gpkg` (gitignored) and `web/data/cities/{slug}/settlements.geojson` (not a map layer). Search index: `web/data/settlements_search.json`.

| City | Study points | GRID3 | OSM | On the printed plate |
|---|---:|---:|---:|---:|
| Lagos | 1,094 | 1,035 | 59 | 461 (seven LGAs) |
| Kano | 5,085 | 5,034 | 51 | 5,085 |
| Ibadan | 324 | 323 | 1 | 324 |
| Port Harcourt | 197 | 163 | 34 | 197 |
| Abuja | 379 | 358 | 21 | 271 (ten wards) |

Kano’s count is the GRID3 named-settlement census, so it includes every named compound in the eight metro LGAs, not only villages. Ibadan’s OSM fill is thin because Overpass 504’d; GRID3 still covers the core five LGAs.

## Abuja north-west (the populated place on the plate)

The unnamed mark on the top-left of the Abuja study-area / ten-ward plate is **Dakwa** and **Dei-Dei**, inside Kubwa ward in Bwari, not extra Bwari land (Kawu, Igu, Shere stay out). Esri’s light-gray basemap prints **Gwari** on that same lobe; there is no GRID3 point named only “Gwari” on the outline. **Gwarinpa** is the district. Gbagyi/Gwari is the ethnic name.

| Name | Ward | Lon | Lat | On plate |
|---|---|---:|---:|---|
| Dakwa | Kubwa | 7.237283 | 9.114223 | yes |
| Dakwa 1 | Kubwa | 7.238500 | 9.113970 | yes |
| Dakwa 2 | Kubwa | 7.233440 | 9.112010 | yes |
| Rinjin Dakwa | Kubwa | 7.220070 | 9.096290 | yes |
| Deidei | Kubwa | 7.258950 | 9.114460 | yes |
| Old Dei Dei | Kubwa | 7.259555 | 9.115299 | yes |
| Dei Dei Shagari Quarters | Kubwa | 7.253198 | 9.114467 | yes |
| Jibi Dei Dei | Kubwa | 7.254777 | 9.145027 | yes |
| Jibi Poweye | Kubwa | 7.258730 | 9.120120 | yes |
| Kagini | Kubwa | 7.300606 | 9.138880 | yes |
| Dakwa Village | Jiwa | 7.256213 | 9.078695 | no (AMAC, off plate) |
| Dakwa I / Dantata | Jiwa | 7.2457 | 9.099 | no |
| Gwarinpa | Gwarinpa | 7.401971 | 9.111039 | yes |

Use the CSV for any other name. Hex popups say “Place: Dakwa” or “Near Dakwa” when the tile centre is more than 400 m from the point.
