"""Embed QGIS default styles in GeoPackages we write.

Metro LGA layers always carry shapeName labels (Helvetica 10 pt, white halo); ward
layers carry the same treatment on wardname. QGIS loads these from the GeoPackage
`layer_styles` table when the layer is added.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .paths import ROOT

METRO_LGA_QML = ROOT / "qgis" / "styles" / "metro_lgas.qml"
WARD_QML = ROOT / "qgis" / "styles" / "wards.qml"
LGA_STYLE_NAME = "LGA shapeName labels"
WARD_STYLE_NAME = "Ward wardname labels"


def _geometry_column(con: sqlite3.Connection, layer_name: str) -> str:
    row = con.execute(
        "SELECT column_name FROM gpkg_geometry_columns WHERE table_name = ?",
        (layer_name,),
    ).fetchone()
    return row[0] if row else "geom"


def embed_qml(
    gpkg: Path,
    layer_name: str,
    qml_path: Path,
    *,
    style_name: str,
    description: str,
) -> None:
    qml_text = qml_path.read_text(encoding="utf-8")
    con = sqlite3.connect(gpkg)
    try:
        geom = _geometry_column(con, layer_name)
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS layer_styles (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                f_table_catalog TEXT(256),
                f_table_schema TEXT(256),
                f_table_name TEXT(256),
                f_geometry_column TEXT(256),
                styleName TEXT(30),
                styleQML TEXT,
                styleSLD TEXT,
                useAsDefault BOOLEAN,
                description TEXT,
                owner TEXT(30),
                ui TEXT(30),
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        con.execute("DELETE FROM layer_styles WHERE f_table_name = ?", (layer_name,))
        con.execute(
            """
            INSERT INTO layer_styles (
                f_table_catalog, f_table_schema, f_table_name, f_geometry_column,
                styleName, styleQML, styleSLD, useAsDefault, description, owner, ui
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "",
                "",
                layer_name,
                geom,
                style_name[:30],
                qml_text,
                "",
                1,
                description,
                "",
                "",
            ),
        )
        con.commit()
    finally:
        con.close()


def embed_metro_lga_style(gpkg: Path, layer_name: str | None = None) -> Path:
    gpkg = Path(gpkg)
    layer_name = layer_name or gpkg.stem
    if not METRO_LGA_QML.exists():
        raise FileNotFoundError(METRO_LGA_QML)
    embed_qml(
        gpkg,
        layer_name,
        METRO_LGA_QML,
        style_name=LGA_STYLE_NAME,
        description="shapeName labels: Helvetica 10 pt, white 1 mm halo",
    )
    return gpkg


def embed_ward_style(gpkg: Path, layer_name: str | None = None) -> Path:
    gpkg = Path(gpkg)
    layer_name = layer_name or gpkg.stem
    if not WARD_QML.exists():
        raise FileNotFoundError(WARD_QML)
    embed_qml(
        gpkg,
        layer_name,
        WARD_QML,
        style_name=WARD_STYLE_NAME,
        description="wardname labels: Helvetica 10 pt, white 1 mm halo, dashed ward edge",
    )
    return gpkg
