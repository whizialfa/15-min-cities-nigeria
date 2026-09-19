# QGIS

Double-click `{city}_so_far.qgz` — all five cities are built: Lagos, Kano, Ibadan, Abuja, Port Harcourt.

Layers (bottom to top): OSM, state LGAs, population hexes, walk `PT_k`, Euclidean `PT_k` (off), wards, study outline, GRID3 schools, GRID3 health. Metro LGA polygons and the off-network hatch are not built into the project.

Health is labelled by its actual source, so the TOC title differs by city: GRID3 v2 for Lagos and Port Harcourt, v3 for Kano, Ibadan and Abuja. Abuja is built `sparse`: larger point markers, and population rather than `PT_k` visible on open, because its 1,476 km² of mostly-empty AMAC swamps the hex layer.

Print plates label OSM named places (`{city}_places.gpkg`: suburb / quarter / neighbourhood, Helvetica 14 pt) rather than every ward name. Ward polygons stay as outlines. Abuja draws only seven wards (Gwarinpa, Wuse, Nyanya, Karu, City Centre, Garki, Kabusa) as the outline and hex clip — not the rest of AMAC. Lagos draws seven LGAs (Eti-Osa, Lagos Island, Apapa, Lagos Mainland, Surulere, Mushin, Shomolu) — not the 16-LGA metro.

`{city}_state_lgas.gpkg` carries every LGA in the state as canvas context (Rivers 23, Lagos 20, Kano 44, Oyo 33, FCT 6); the metro LGA names are excluded by a subset string so they are not labelled on the leftover ring. Build with:

```bash
PYTHONPATH="src:.pydeps" python3.12 -m proximity.wards port_harcourt
```

Headline is **OSM walk** `PT_k`, with Euclidean kept in the TOC as an off sensitivity layer. Car grades are not built into projects; pass `with_car=True` to `run()` if you ever need them back.

## Classification

Two different rules, because the two layers answer different questions.

`PT_k` uses **six fixed classes, identical in every city**, defined once in `src/proximity/classes.py` and shared with the PNG plates so the two deliverables cannot drift:

| Class | Range | Colour |
|---|---|---|
| Very close | ≤ 5 min | dark green |
| Close | 5–10 min | green |
| Moderate | 10–15 min | lime |
| Far | 15–30 min | amber |
| Very far | 30–60 min | red |
| Extremely far | 60+ min | dark maroon |

Do **not** switch this to natural breaks. Per-city Jenks gives every city its own edges, which is exactly what makes two cities unreadable side by side — and the range genuinely does differ per city, from a Lagos median of 11.5 min to an Abuja median of 57.6. Fixed classes are the answer to that, not a symptom of ignoring it. 15 is a class edge, so classes 1–3 sum to `F15` by construction: the green block *is* the 15-minute city, and it reproduces the reported F15 for all five cities exactly.

The 60 edge is there for Abuja and Port Harcourt. Collapsing everything above 30 min into one class gave Abuja a single bucket holding 45.3% of its people and spanning a half-hour walk to a four-hour one — least informative in the two cities whose access failure is the point. Split, Abuja reads 36.0% / 9.3% and Port Harcourt 13.6% / 2.2%. The top class is near-empty in the dense cities (Lagos 0.4%, Kano 0.0%) and that is deliberate: in a fixed cross-city scheme, "nobody in Kano is more than an hour's walk from a clinic" is a finding. Do not prune it to suit the best-served city — that is the opposite of the `pop` case below, where classes fitted to Lagos left Ibadan with two empty rungs and no information gained.

`pop` uses **Jenks fitted per city, then rounded** (`_rounded_jenks`, 6 classes), coloured with the original ColorBrewer YlOrRd yellow-to-red. Pretty breaks space on the value *range*, so Lagos (max ~9,000) jumped in 2,000s and the map went uniformly pale. Jenks follows the data; rounding the cuts (422→400, 954→1,000) is what makes the legend readable. Do not share one ladder across cities — that is what emptied Ibadan's top classes.

Each `.qgz` also carries two print layouts that do **not** restyle the layers: **Walk PT_k** and **Population**. Furniture is a boxed title (`WALKING ACCESS IN …` / `POPULATION IN …`), a bold 12 pt three-sentence footnote, a white spear north arrow, boxed swatch legend, a longer scale bar, haloed `©Wisdom Akpabio` credit, and a neatline. The city outline is zoomed to the largest size that still clears the title, legend, footnote, north arrow and scale — empty water or bush in the bounding-box corners may sit under furniture; the filled city may not. PT and population fills are **80%** opaque. Open *Project → Layouts* or use the exported `maps/{city}_PT_k_plate.png` / `{city}_pop_plate.png`.

Rebuild after a pipeline run:

```bash
Q=/Applications/QGIS.app/Contents/MacOS/bin/python3.9
for c in lagos kano ibadan abuja port_harcourt; do $Q qgis/build_city_project.py $c; done
```

Rebuild **every** city, not just the one that changed. Layout export adds a few seconds; staleness is still silent. `GeoPackage user_version ... may only be partially supported` on stdout is benign: the GeoPackages are written by a newer GDAL than QGIS 3.9 ships.
