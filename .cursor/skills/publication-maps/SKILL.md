---
name: publication-maps
description: >-
  Wisdom's publication cartography for print map plates: A3 furniture (title,
  legend, footnote, north, scale, credit), no overlap, furniture-aware zoom,
  snug legends with even insets, plain-language titles. Use when building QGIS
  print layouts, choropleth hex maps, map plates, legends, north arrows, scale
  bars, or exporting PNG/PDF maps.
---

# Publication maps (Wisdom)

How Wisdom makes print plates. Apply in every project that exports choropleth maps, QGIS layouts, or PNG/PDF map figures. Iterate by looking at the plate, not by arguing from layout coordinates.

## What you show him

A map he is asked to look at is a landscape A3 plate. A QGIS canvas dump, a matplotlib figure, or a legend painted onto a screenshot is not a map in this workshop. The Los Angeles and Lagos "so far" images failed this test: grey or bare canvas, no title box, no north arrow, no scale, no three-sentence footnote, no `©Wisdom Akpabio`, and a legend that did not sit in the furniture.

Thematic plates sit on Carto Positron so the city is recognisable: roads, names and water, without the OpenStreetMap colour noise. In QGIS this is an XYZ layer, `https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png`. Do not substitute OpenStreetMap or Esri World Topo. Do not fall back to the bare light-grey canvas. Esri light grey is only for study-area figures. If he cannot tell what the colours mean from the legend alone, the plate is not done. Positron is built on OpenStreetMap data, so a small `© OpenStreetMap contributors © CARTO` sits with the Wisdom credit, not in its own box.

When he corrects a plate, write the correction into this skill before the next city. Then copy this file into that project's `.cursor/skills/publication-maps/SKILL.md`. Read the project copy before drawing.

## Page

Landscape A3. Thin black neatline. White paper. Carto Positron under the choropleth so the city sits in geography, not on a blank canvas.

Furniture lives **inside** the neatline, never overlapping each other or the drawn city:

| Item | Place | Treatment |
|---|---|---|
| Title | top-left white box | Two short lines, non-technical, Arial 15 Bold, centered in the box |
| North | top-right | White compass SVG, grid north, no letter N |
| Legend | bottom-left | Snug to content; even inset; intuitive header; range-only classes |
| Footnote | bottom-center | Three sentences, 12 pt Bold, what the map shows |
| Scale | bottom-right | Line Ticks Up, kilometres, long enough to read |
| Credit | above the scale | `©Wisdom Akpabio`, small, white-buffered, no box |

White boxes: fill 255, thin black stroke (~0.45 mm). Match the title box — that is the visual family.

## Overlap is a defect

No furniture on the city. No ward label under the title. No coast eating the legend. No scale sitting on hexes.

Zoom **in** as far as the furniture allows, then center: take the city up, down, left, or right. Zooming out “to be safe” is the usual failure. Round cities on landscape A3 will show Positron left and right — that is the page, not a reason to shrink the city.

Collision must use the **real** item box, not a reserved empty slot. A 90 mm legend frame with 40 mm of content will hold the whole city off the south coast.

For a wide coastal city, a shorter legend is what lets the shoreline drop. Grow the title’s collision box if northern labels sit above the hexes (Lagos: Alagbado / Alakuko).

## Title and footnote

Title names the phenomenon, not the field:

- `POPULATION IN LAGOS` / `People in each neighbourhood`
- `WALKING ACCESS IN LAGOS` / `To clinics and schools`

Not `PT_k`, `pop`, `n=5`, or a file name.

Footnote: three sentences a non-specialist can read. What the map shows, the cell size, how to read the colour. 12 pt Bold — smaller is illegible in print.

## Legend

Keep the font size; change the box.

- Header in plain language: `People per hexagon`, `Minutes on foot`
- Class labels are the range only (`≤ 5 min`, `5–400`), not `Very close (≤ 5 min)`
- Title ~13 pt Bold, classes ~12 pt, Arial
- Inset ~2.5 mm between type and frame — not glued to the stroke, not a padded void
- Row spacing stays tight. Empty white **inside** the box is the defect, not a short box
- Size from content. If the layout engine reports ~0 mm, give the item a real rect first; do **not** floor height to 90 mm of air

## Geography on the plate

- Study boundary: bold black, the strongest line
- Internal units (wards): visible, thinner and greyer than the study edge (~0.22 mm). Hyphenated names stay on **one** line (non-breaking hyphen)
- Choropleth fill ~80% opacity (alpha 204) so the base map reads through. 70% washes sequential greens into each other
- No extra admin layer the reader does not need
- No hatch or veil that recodes the ramp. Completeness belongs in a table or a separate mask figure, not as a tint on the access map

## Colour

- **Minute metrics:** one shared nominal ladder across every city in the panel. 15 must be an edge (so the first classes sum to F15). Keep a 60 edge — otherwise everything above 30 min is one class
- **Counts / density:** Jenks **per city**, then round the cuts, on a sequential ramp (ColorBrewer YlOrRd). Pretty breaks on the value range flatten a skewed city. A shared ladder empties classes in compact cities

## Study-area figures (in the paper)

Same family as the A3 plates. QGIS, Esri light-grey base, furniture inside the neatline. Not a matplotlib blob on cream.

- Title `STUDY AREA` / city name, Nigeria locator, scale, grid-north compass SVG, snug legend, three-sentence footnote, `©Wisdom Akpabio`
- Study outline is the strongest line. Wards thinner and greyer. Place labels Helvetica, no overlap
- If the analysis splits the city (old city / fringe, rural ring), those fills sit on the grey base at ~80% or less so streets still read
- Caption says what the outline is, why, and the people / area count
- Same city, same outline: reuse the plate Wisdom already signed off (Kano heat copies `15-min-cities-nigeria/maps/kano_study_area.png`). A later analytical cut (old city / fringe / ring) lives in the prose, not a second study-area style
- Rebuild with QGIS's `python3.9` and `env -u PYTHONPATH`

## Rebuild and look

After any furniture or style change, rebuild the plate and inspect it. Stale maps are silent.

QGIS print layouts: run **QGIS’s** Python, with `env -u PYTHONPATH`, so a project venv (numpy built for a newer CPython) cannot load.

Export PNG (~200 dpi) and PDF. Do not commit rasters or plates unless asked.

## Do not

- Show a progress map that is not a plate
- Paint a legend onto a rendered image instead of laying it out
- Tiny footnotes
- Technical legend titles
- Overlap “just this corner”
- Zoom out to keep furniture happy
- Stretch a legend to a fixed slot
- Metro / LGA fills on top of a hex choropleth
- Drop no-data cells to make the map prettier
- A second colour language that copies the previous project's ramp. Built-up on the heat plates is a dull red because he asked for that, and it must not be the walking-access red
