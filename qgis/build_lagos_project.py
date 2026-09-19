"""Build qgis/lagos_so_far.qgz. Thin wrapper around build_city_project."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_city_project import main

if __name__ == "__main__":
    print(main("lagos"))
