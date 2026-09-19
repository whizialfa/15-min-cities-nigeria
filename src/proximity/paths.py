"""Project paths. Bulk rasters stay under data/ and are gitignored."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
MAPS = ROOT / "maps"
CHARTS = ROOT / "charts"
NOTEBOOKS = ROOT / "notebooks"
WEB = ROOT / "web"
WEB_DATA = WEB / "data"

for _p in (DATA_RAW, DATA_PROCESSED, MAPS, CHARTS, WEB_DATA):
    _p.mkdir(parents=True, exist_ok=True)
