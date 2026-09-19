"""Download HDX and WorldPop inputs. Files stay gitignored under data/raw."""

from __future__ import annotations

import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from .paths import DATA_RAW

USER_AGENT = "15-min-cities-nigeria/0.1 (research adaptation; HDX)"

DATASETS: dict[str, dict] = {
    "grid3_health_v3": {
        "url": (
            "https://data.humdata.org/dataset/a1e3e4bc-3699-4fe1-bd17-b38f4e7108d2/"
            "resource/f45c9266-0458-4160-a902-32661a6a67ed/download/"
            "grid3_nga_health_facilities_v3_0.gpkg"
        ),
        "filename": "grid3_nga_health_facilities_v3_0.gpkg",
        "source": "GRID3 / HDX",
        "vintage": "2018–2025 (v3.0, published 2026-08)",
        "note": "Operational; 24 states — Lagos and Rivers are absent.",
    },
    "grid3_schools": {
        "url": (
            "https://data.humdata.org/dataset/ec228c18-8edc-4f3c-94c9-a6b946af7229/"
            "resource/8dcb7188-16f2-447a-b006-1895e450bf11/download/nigeria_-_schools.zip"
        ),
        "filename": "nigeria_-_schools.zip",
        "source": "GRID3 / NMIS / HDX",
        "vintage": "2020-12",
        "note": "National school points extracted for government of Nigeria.",
    },
    "hotosm_health": {
        "url": (
            "https://production-raw-data-api.s3.amazonaws.com/ISO3/NGA/"
            "health_facilities/hotosm_nga_health_facilities_osm_gpkg.zip"
        ),
        "filename": "hotosm_nga_health_facilities_osm_gpkg.zip",
        "source": "HOT OSM export on HDX",
        "vintage": "2026-09",
        "note": "Completeness overlay, not the primary facility layer.",
    },
    "hotosm_education": {
        "url": (
            "https://production-raw-data-api.s3.amazonaws.com/ISO3/NGA/"
            "education_facilities/hotosm_nga_education_facilities_osm_gpkg.zip"
        ),
        "filename": "hotosm_nga_education_facilities_osm_gpkg.zip",
        "source": "HOT OSM export on HDX",
        "vintage": "2026-09",
        "note": "Completeness overlay for schools.",
    },
    "cod_ab": {
        "url": (
            "https://data.humdata.org/dataset/81ac1d38-f603-4a98-804d-325c658599a3/"
            "resource/01c65fd9-bd0c-4608-aa1e-2e86bbccf3e5/download/"
            "nga_admin_boundaries.shp.zip"
        ),
        "filename": "nga_admin_boundaries.shp.zip",
        "source": "UN OCHA COD-AB / HDX",
        "vintage": "COD-AB Nigeria",
        "note": "Admin clip and locator inset, not the urban-centre definition.",
    },
    "geoboundaries_adm2": {
        "url": (
            "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/"
            "main/releaseData/gbOpen/NGA/ADM2/geoBoundaries-NGA-ADM2.geojson"
        ),
        "filename": "geoBoundaries-NGA-ADM2.geojson",
        "source": "geoBoundaries gbOpen (GitHub LFS)",
        "vintage": "ADM2 Nigeria",
        "note": "Operational metro-LGA dissolve. Headline boundary; not GHS Urban Centre.",
    },
    "worldpop_2020": {
        "url": (
            "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/NGA/"
            "nga_ppp_2020_UNadj.tif"
        ),
        "filename": "nga_ppp_2020_UNadj.tif",
        "source": "WorldPop (also listed on HDX)",
        "vintage": "2020 UN-adjusted, 100 m",
        "note": (
            "WorldPop UN-adjusted 2020. Not on disk locally; pipeline uses "
            "nga_ppp_2020_constrained.tif from Documents as a comparison raster."
        ),
    },
    "wpdx_nga": {
        "url": (
            "https://data.humdata.org/dataset/29677a2d-1fb2-48a3-a06a-9c66800c418b/"
            "resource/1fdb9a0c-d145-49e5-a502-6a3bc63626e8/download/wpdx_enhanced.csv"
        ),
        "filename": "wpdx_water_points_nga.csv",
        "source": "Water Point Data Exchange / HDX",
        "vintage": "2010-01-01 to 2025-06-21 (HDX package wpdx_nga)",
        "note": (
            "Rural-oriented wells/springs/tapstands. Filter status_id==Yes for functional. "
            "Not a GRID3 urban inventory."
        ),
    },
    "nmis_water": {
        "url": (
            "https://energydata.info/dataset/33cbdf76-db76-447b-a02d-779a4b562147/"
            "resource/f9d82d17-72b0-49de-80c3-53af06e6e98b/download/"
            "watermopupandbaselinenmisfacility.csv"
        ),
        "filename": "nmis_water_facilities.csv",
        "source": "NMIS / OSSAP-MDGs + Columbia (energydata.info)",
        "vintage": "surveys 2009–2012",
        "note": (
            "132,510 national water facilities with a functional flag. Denser than WPdx in "
            "Lagos/Ibadan/Abuja but too old for a headline; completeness overlay only."
        ),
    },
    "nga_population_v3": {
        "url": (
            "https://data.worldpop.org/repo/wopr/NGA/population/v3.0/"
            "NGA_population_v3_0_gridded.zip"
        ),
        "filename": "NGA_population_v3_0_gridded.zip",
        "source": "GRID3 Phase 2 / WorldPop WOPR NGA v3.0",
        "vintage": "2025 (NMEP 2022–23, scaled to UN WPP July 2025)",
        "note": "Default people layer for Nigeria-adjusted F15. ~100 m.",
    },
}


def fetch(url: str, dest: Path, timeout: int = 600) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 200:
        return dest
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
    return dest


def unzip_if_needed(archive: Path, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or archive.with_name(archive.stem)
    if out_dir.exists() and any(out_dir.iterdir()):
        return out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(out_dir)
    return out_dir


def ensure_inputs(keys: list[str] | None = None, skip_errors: bool = True) -> dict[str, Path]:
    chosen = keys or list(DATASETS)
    paths: dict[str, Path] = {}
    for key in chosen:
        meta = DATASETS[key]
        dest = DATA_RAW / meta["filename"]
        try:
            fetch(meta["url"], dest)
        except Exception as exc:
            if dest.exists() and dest.stat().st_size > 200:
                paths[key] = dest
                continue
            if not skip_errors:
                raise
            print(f"skip {key}: {exc}")
            continue
        paths[key] = dest
        if dest.suffix == ".zip":
            unzip_if_needed(dest)
    return paths
