# Walking access map

Live: [whizialfa.github.io/15-min-cities-nigeria](https://whizialfa.github.io/15-min-cities-nigeria/)

Esri-style dashboard for the five-city walking scores. Calcite chrome, Esri and OpenFreeMap Liberty basemaps, MapLibre for the hexes. Colours, opacity, ward strokes, clinic crosses and school marks follow the QGIS plates. GitHub Pages serves this `web/` folder from `main`.

```bash
# from repo root — rewrite the city GeoJSON after a pipeline run
export PYTHONPATH="$PWD/.pydeps:$PWD/src"
/opt/anaconda3/bin/python3.12 -m proximity.web_map

cd web && python3 -m http.server 5173
```

Open http://127.0.0.1:5173/

Lagos shows seven inner local government areas and Abuja shows seven AMAC wards. Panel scores match that frame. The paper headline is still the metro.

Ward outlines keep the original shared edges. Independently simplifying each ward opens gap slivers along the boundaries, so that step is skipped.

Click a neighbourhood tile for the walk from that cell and the ward it sits in. Every ward popup carries people, F15, clinic/school split, people still beyond 15 minutes, GRID3 counts, and a short reading against the city score. The glossary and a PDF download live in the documentation accordion.

Optional: `npm install && npm run dev`.
