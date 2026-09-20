"""Build qgis/{slug}_so_far.qgz from processed city layers. Run with QGIS's Python."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
# proximity.classes is stdlib-only so it imports under QGIS's bundled Python 3.9.
sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("QGIS_PREFIX_PATH", "/Applications/QGIS.app/Contents/MacOS")
os.environ.setdefault("PROJ_LIB", "/Applications/QGIS.app/Contents/Resources/proj")
os.environ.setdefault("GDAL_DATA", "/Applications/QGIS.app/Contents/Resources/gdal")

from qgis.core import (  # noqa: E402
    Qgis,
    QgsApplication,
    QgsClassificationJenks,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDistanceArea,
    QgsFeature,
    QgsFillSymbol,
    QgsGeometry,
    QgsGraduatedSymbolRenderer,
    QgsLayoutExporter,
    QgsLayoutItem,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutMeasurement,
    QgsLineSymbol,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLegendRenderer,
    QgsLegendStyle,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPointDisplacementRenderer,
    QgsPointXY,
    QgsCategorizedSymbolRenderer,
    QgsField,
    QgsPrintLayout,
    QgsRendererCategory,
    QgsProject,
    QgsProperty,
    QgsRasterLayer,
    QgsRectangle,
    QgsReferencedRectangle,
    QgsRendererRange,
    QgsRuleBasedRenderer,
    QgsScaleBarSettings,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant, Qt  # noqa: E402
from qgis.PyQt.QtGui import QColor, QFont  # noqa: E402

from proximity.cities import ABUJA_PLATE_WARDS, LAGOS_PLATE_LGAS  # noqa: E402
from proximity.classes import (  # noqa: E402
    PT_CLASS_NAMES,
    PT_CLASS_RANGES,
    PT_CLASS_RGB,
    pt_class_bounds,
)

LGA_QML = ROOT / "qgis" / "styles" / "metro_lgas.qml"
WARD_QML = ROOT / "qgis" / "styles" / "wards.qml"
NORTH_SVG = ROOT / "qgis" / "styles" / "north_arrow_white.svg"
ADM2_PATH = ROOT / "data" / "raw" / "geoBoundaries-NGA-ADM2.geojson"
MAPS = ROOT / "maps"

CITY_DISPLAY = {
    "lagos": "LAGOS",
    "kano": "KANO",
    "ibadan": "IBADAN",
    "abuja": "ABUJA",
    "port_harcourt": "PORT HARCOURT",
}
CITY_UTM = {
    "lagos": "EPSG:32631",
    "ibadan": "EPSG:32631",
    "kano": "EPSG:32632",
    "abuja": "EPSG:32632",
    "port_harcourt": "EPSG:32632",
}
COASTAL = {"lagos", "port_harcourt"}
# Named in the text — keep on the plate when the polygon exists.
PINNED_LABELS = {
    "lagos": (
        "Ikoyi 1",
        "Falomo–Oyinkan Abayomi",
        "Sangotedo",
        "Okun Ajah–Okunmopo",
        "Ikosi Isheri",
    ),
    "kano": ("Ungogo", "Yada Kunya", "Fanisau", "Chalawa"),
    "ibadan": ("Olopomewa",),
    "port_harcourt": ("Rumuoji Eneka", "Rumunduru", "Mgbu Minkpiti"),
    "abuja": ABUJA_PLATE_WARDS,
}
LABEL_AREA_N = {"lagos": 5, "kano": 8, "ibadan": 7, "port_harcourt": 7, "abuja": 6}
LABEL_POP_N = {"lagos": 3, "kano": 6, "ibadan": 4, "port_harcourt": 4, "abuja": 6}
LABEL_CAP = {"lagos": 12, "kano": 14, "ibadan": 10, "port_harcourt": 10, "abuja": 10}
PLACE_LABEL_CAP = {"lagos": 28, "kano": 26, "ibadan": 28, "port_harcourt": 28, "abuja": 26}
ALWAYS_SHOW_LABELS = {
    "abuja": (
        "Lugbe",
        "Apo",
        "Lokogoma",
        "Nyanya",
        "Karu",
        "Gwarinpa",
        "Kabusa",
        "Kubwa",
        "Dutse",
        "Usuma",
    ),
    "lagos": (
        "Eko Atlantic",
        "Tarkwa Bay",
        "Abraham Adesanya",
        "Adesanya",
        "Apapa",
        "Ilado",
        "Oko Agbo",
    ),
    "port_harcourt": (
        "Township VI",
        "Rumuwoji II",
        "Rumuwoji III",
        "Orogbum",
        "Old GRA",
        "Diobu",
    ),
}
WARD_LABEL_PT = 14
PLACE_LABEL_PT = 14
SKIP_LABELS = {
    "lagos": {"Taffi", "I Irede", "Ibeshe and Environ"},
}
SHORT_LABELS = {
    "Falomo–Oyinkan Abayomi": "Falomo",
    "Okun Ajah–Okunmopo": "Okun Ajah",
    "Ring Road–Challenge–Oluyole": "Oluyole",
    "Ibeshe and Environ": "Ibeshe",
    "Abaranje–Okerube": "Abaranje",
    "Egberuukwu Oyigbo": "Oyigbo",
    "Apata–Odo Ona": "Apata",
    "Abraham Adesanya": "Adesanya",
}
MM = QgsUnitTypes.LayoutMillimeters
FRAME_W = 404.0
FRAME_H = 281.0
TITLE_H = 32.0
NOTE_W = 196.0
NOTE_H = 36.0
NOTE_BOTTOM = 8.0
NOTE_FONT_PT = 12
LEGEND_W = 90.0
NORTH_H = 40.0
SCALE_W = 82.0
SCALE_H = 16.0
FURNITURE_GAP = 3.0
# Extra clearance around legend / footnote / scale so hexes cannot nibble the frame.
BOTTOM_CLEAR = 6.0
CITY_BUFFER_M = 0.0
CREDIT = "©Wisdom Akpabio"
# 80% opacity: 70% washes the 15-minute greens into each other.
PT_FILL_ALPHA = 204
POP_FILL_ALPHA = 204

HEALTH_TITLE = {
    "lagos": "6 GRID3 health v2",
    "port_harcourt": "6 GRID3 health v2",
}


def _vector(path: Path, layername: str, title: str) -> QgsVectorLayer:
    uri = f"{path.as_posix()}|layername={layername}"
    layer = QgsVectorLayer(uri, title, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"Could not load {uri}")
    return layer


def _union_geoms(layer: QgsVectorLayer) -> QgsGeometry | None:
    merged = None
    for feat in layer.getFeatures():
        g = feat.geometry()
        if g is None or g.isEmpty():
            continue
        gg = QgsGeometry(g)
        merged = gg if merged is None else merged.combine(gg)
    if merged is None or merged.isEmpty():
        return None
    valid = merged.makeValid()
    return valid if valid is not None and not valid.isEmpty() else merged


def _memory_polygon(geom: QgsGeometry, crs: str, name: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(f"Polygon?crs={crs}", name, "memory")
    feat = QgsFeature(layer.fields())
    feat.setGeometry(QgsGeometry(geom))
    if not layer.dataProvider().addFeature(feat):
        raise RuntimeError(f"Could not write {name}")
    layer.updateExtents()
    return layer


def _quoted_in(names: tuple[str, ...]) -> str:
    return ",".join("'" + n.replace("'", "''") + "'" for n in names)


def _copy_intersecting(src: QgsVectorLayer, mask: QgsGeometry, name: str) -> QgsVectorLayer:
    """Memory copy of features that meet the current filter and intersect mask."""
    kind = {
        QgsWkbTypes.PointGeometry: "Point",
        QgsWkbTypes.LineGeometry: "LineString",
        QgsWkbTypes.PolygonGeometry: "MultiPolygon",
    }.get(QgsWkbTypes.geometryType(src.wkbType()), "Polygon")
    layer = QgsVectorLayer(f"{kind}?crs={src.crs().authid()}", name, "memory")
    prov = layer.dataProvider()
    prov.addAttributes(src.fields().toList())
    layer.updateFields()
    copied = []
    for feat in src.getFeatures():
        g = feat.geometry()
        if g is None or g.isEmpty() or not g.intersects(mask):
            continue
        copied.append(QgsFeature(feat))
    if copied:
        prov.addFeatures(copied)
    layer.updateExtents()
    return layer


def _graduated(
    layer: QgsVectorLayer,
    field: str,
    breaks: list[tuple[float, float, str, str]],
    outline_width: str = "0.05",
) -> None:
    ranges = []
    for lo, hi, color, label in breaks:
        symbol = QgsFillSymbol.createSimple(
            {
                "color": color,
                "outline_color": "255,255,255,40",
                "outline_width": outline_width,
                "outline_width_unit": "MM",
            }
        )
        ranges.append(QgsRendererRange(lo, hi, symbol, label))
    renderer = QgsGraduatedSymbolRenderer(field, ranges)
    layer.setRenderer(renderer)


# ColorBrewer YlOrRd 6 — the palette the population layer shipped with.
POP_YLORRD = (
    (255, 237, 160),
    (254, 217, 118),
    (254, 178, 76),
    (253, 141, 60),
    (227, 26, 28),
    (128, 0, 38),
)


def _nice(value: float) -> float:
    """Snap a Jenks edge to a legend number without moving it far."""
    if value < 250:
        step = 50
    elif value < 2000:
        step = 100
    elif value < 5000:
        step = 500
    else:
        step = 1000
    return float(round(value / step) * step)


def _round_edges(edges: list[float]) -> list[float]:
    """Keep the first (data min) and last (data max); snap interior Jenks cuts."""
    if len(edges) < 3:
        return edges
    lo, *interior, hi = edges
    out = [lo]
    for raw in interior:
        snapped = _nice(raw)
        if snapped <= out[-1]:
            snapped = out[-1] + (50.0 if out[-1] < 2000 else 500.0)
        if snapped >= hi:
            break
        out.append(snapped)
    out.append(hi)
    return out


def _rounded_jenks(
    layer: QgsVectorLayer,
    field: str,
    classes: int = 6,
    *,
    palette: tuple[tuple[int, int, int], ...] = POP_YLORRD,
    alpha: int = POP_FILL_ALPHA,
) -> None:
    """Jenks partitions, rounded for the legend, sequential warm colours.

    Pretty breaks space on the value *range*, so Lagos (max ~9,000) jumped in 2,000s
    and almost every hexagon landed in the palest yellow. Jenks follows the data;
    rounding the cuts (422→400, 954→1,000) is what makes the legend readable. Do not
    share one ladder across cities — that is what emptied Ibadan's top classes.
    """
    method = QgsClassificationJenks()
    raw = method.classes(layer, field, classes)
    if not raw:
        raise RuntimeError(f"Jenks failed on {layer.name()}")
    edges = _round_edges([raw[0].lowerBound()] + [r.upperBound() for r in raw])
    n = len(edges) - 1
    breaks = []
    for i in range(n):
        lo, hi = edges[i], edges[i + 1]
        rgb = palette[round(i * (len(palette) - 1) / max(n - 1, 1))]
        label = f"{lo:,.0f}+" if i == n - 1 else f"{lo:,.0f}–{hi:,.0f}"
        breaks.append((lo, hi, "{},{},{},{}".format(*rgb, alpha), label))
    _graduated(layer, field, breaks)


def _label_expression(field: str) -> str:
    whens = " ".join(
        f"WHEN \"{field}\" = '{key.replace(chr(39), chr(39)+chr(39))}' THEN '{val}'"
        for key, val in SHORT_LABELS.items()
    )
    return f"CASE {whens} ELSE replace(\"{field}\", '-', '‑') END"


def _apply_pal_labels(
    layer: QgsVectorLayer,
    field: str,
    *,
    size: int,
    pinned: tuple | list | None = None,
    max_labels: int | None = None,
    min_mm: float = 0.0,
    around: bool = False,
) -> None:
    """Helvetica labels, no overlaps, colliding names omitted."""
    if field not in layer.fields().names():
        return
    settings = QgsPalLayerSettings()
    settings.fieldName = _label_expression(field)
    settings.isExpression = True
    if around:
        settings.placement = Qgis.LabelPlacement.AroundPoint
        settings.centroidInside = False
    else:
        settings.placement = Qgis.LabelPlacement.OverPoint
        settings.centroidInside = True
    settings.setPolygonPlacementFlags(
        Qgis.LabelPolygonPlacementFlags(
            int(Qgis.LabelPolygonPlacementFlag.AllowPlacementInsideOfPolygon)
        )
    )
    settings.displayAll = False
    settings.obstacle = False
    settings.minFeatureSize = float(min_mm)
    settings.wrapChar = " "
    settings.autoWrapLength = 26
    settings.limitNumLabels = True
    settings.maxNumLabels = int(max_labels or 24)
    settings.setUnplacedVisibility(Qgis.UnplacedLabelVisibility.NeverShow)
    settings.placementSettings().setOverlapHandling(Qgis.LabelOverlapHandling.PreventOverlap)

    fmt = QgsTextFormat()
    font = QFont("Helvetica", size)
    fmt.setFont(font)
    fmt.setSize(size)
    fmt.setSizeUnit(QgsUnitTypes.RenderPoints)
    fmt.setColor(QColor(55, 50, 46))
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(1.15)
    buf.setSizeUnit(QgsUnitTypes.RenderMillimeters)
    buf.setColor(QColor(250, 250, 250))
    fmt.setBuffer(buf)
    settings.setFormat(fmt)

    props = settings.dataDefinedProperties()
    pin_q = ",".join("'" + str(n).replace("'", "''") + "'" for n in (pinned or ()))
    if pin_q:
        props.setProperty(
            QgsPalLayerSettings.Priority,
            QgsProperty.fromExpression(
                f'CASE WHEN "{field}" IN ({pin_q}) THEN 10 '
                f"ELSE scale_linear($area, 0, maximum($area), 3, 8) END"
            ),
        )
    else:
        props.setProperty(
            QgsPalLayerSettings.Priority,
            QgsProperty.fromExpression("scale_linear($area, 0, maximum($area), 2, 10)"),
        )
    settings.setDataDefinedProperties(props)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def _place_labels(layer: QgsVectorLayer, slug: str) -> None:
    """OSM suburb / quarter / neighbourhood names. Helvetica 14, no overlaps."""
    if "name" not in layer.fields().names():
        return
    settings = QgsPalLayerSettings()
    settings.fieldName = (
        "CASE WHEN \"name\" = 'Apata–Odo Ona' THEN 'Apata' "
        "WHEN \"name\" = 'Abraham Adesanya' THEN 'Adesanya' "
        "ELSE replace(\"name\", '-', '‑') END"
    )
    settings.isExpression = True
    ordered = getattr(Qgis.LabelPlacement, "OrderedPositionsAroundPoint", None)
    quad = getattr(Qgis, "LabelQuadrantPosition", None)
    over_q = getattr(quad, "Over", None) if quad is not None else None
    if ordered is not None and over_q is not None:
        settings.placement = ordered
        order = [over_q]
        for name in (
            "Above",
            "Below",
            "Right",
            "Left",
            "AboveRight",
            "AboveLeft",
            "BelowRight",
            "BelowLeft",
        ):
            val = getattr(quad, name, None)
            if val is not None:
                order.append(val)
        settings.predefinedPositionOrder = order
        settings.dist = 1.4
        settings.distUnits = QgsUnitTypes.RenderMillimeters
    else:
        settings.placement = Qgis.LabelPlacement.OverPoint
        settings.dist = 0
    settings.centroidInside = True
    settings.displayAll = False
    settings.obstacle = False
    settings.wrapChar = " "
    settings.autoWrapLength = 22
    settings.limitNumLabels = True
    settings.maxNumLabels = PLACE_LABEL_CAP.get(slug, 16)
    settings.setUnplacedVisibility(Qgis.UnplacedLabelVisibility.NeverShow)
    settings.placementSettings().setOverlapHandling(Qgis.LabelOverlapHandling.PreventOverlap)

    fmt = QgsTextFormat()
    font = QFont("Helvetica", PLACE_LABEL_PT)
    fmt.setFont(font)
    fmt.setSize(PLACE_LABEL_PT)
    fmt.setSizeUnit(QgsUnitTypes.RenderPoints)
    fmt.setColor(QColor(55, 50, 46))
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(1.15)
    buf.setSizeUnit(QgsUnitTypes.RenderMillimeters)
    buf.setColor(QColor(250, 250, 250))
    fmt.setBuffer(buf)
    settings.setFormat(fmt)

    props = settings.dataDefinedProperties()
    if "priority" in layer.fields().names():
        props.setProperty(
            QgsPalLayerSettings.Priority,
            QgsProperty.fromExpression('to_int("priority")'),
        )
    elif "pinned" in layer.fields().names() and "rank" in layer.fields().names():
        props.setProperty(
            QgsPalLayerSettings.Priority,
            QgsProperty.fromExpression('CASE WHEN "pinned" = 1 THEN 10 ELSE "rank" / 2 END'),
        )
    always = ALWAYS_SHOW_LABELS.get(slug, ())
    if always:
        quoted = ",".join("'" + str(n).replace("'", "''") + "'" for n in always)
        always_prop = getattr(QgsPalLayerSettings, "AlwaysShow", None)
        if always_prop is not None:
            props.setProperty(
                always_prop,
                QgsProperty.fromExpression(f'"name" IN ({quoted})'),
            )
        props.setProperty(
            QgsPalLayerSettings.Priority,
            QgsProperty.fromExpression(
                f'CASE WHEN "name" IN ({quoted}) THEN 10 ELSE coalesce("priority", 5) END'
            ),
        )
    settings.setDataDefinedProperties(props)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def _name_labels(layer: QgsVectorLayer, qml: Path, field: str) -> None:
    """State-LGA canvas labels. Print plates do not use this layer."""
    if qml.exists():
        layer.loadNamedStyle(str(qml))
    _apply_pal_labels(layer, field, size=13, max_labels=20, min_mm=8.0)


def _ward_area_m2(layer: QgsVectorLayer, feature) -> float:
    da = QgsDistanceArea()
    da.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
    da.setEllipsoid("WGS84")
    try:
        return float(da.measureArea(feature.geometry()))
    except Exception:
        return 0.0


def _ward_pop_lookup(slug: str) -> dict:
    path = PROCESSED / f"{slug}_ward_f15.gpkg"
    if not path.exists():
        return {}
    layer = _vector(path, f"{slug}_ward_f15", "_ward_f15")
    out = {}
    for feat in layer.getFeatures():
        name = feat["locator"]
        if name:
            out[str(name)] = float(feat["pop"] or 0)
    return out


def _label_keepers(slug: str, layer: QgsVectorLayer) -> list:
    """Short list: pinned names, then largest, then most populated."""
    present = []
    areas = {}
    for feat in layer.getFeatures():
        name = feat["locator"]
        if not name:
            continue
        name = str(name)
        present.append(name)
        areas[name] = _ward_area_m2(layer, feat)
    if slug == "abuja":
        return [n for n in ABUJA_PLATE_WARDS if n in set(present)]

    pinned = [n for n in PINNED_LABELS.get(slug, ()) if n in set(present)]
    by_area = sorted(present, key=lambda n: areas.get(n, 0.0), reverse=True)
    pop = _ward_pop_lookup(slug)
    by_pop = sorted(present, key=lambda n: pop.get(n, 0.0), reverse=True)
    names = []
    for group, take in (
        (pinned, len(pinned)),
        (by_area, LABEL_AREA_N.get(slug, 8)),
        (by_pop, LABEL_POP_N.get(slug, 6)),
    ):
        added = 0
        for name in group:
            if name in names:
                continue
            names.append(name)
            added += 1
            if added >= take:
                break
    cap = LABEL_CAP.get(slug, 12)
    skip = SKIP_LABELS.get(slug, set())
    names = [n for n in names if n not in skip]
    return names[:cap]


def _ward_name_layer(source: QgsVectorLayer, slug: str, keepers: list) -> QgsVectorLayer:
    """Memory layer of the shortlist so PAL never sees the other 200+ polygons."""
    want = set(keepers)
    crs = source.crs().authid() or "EPSG:4326"
    layer = QgsVectorLayer(f"Polygon?crs={crs}", "2b Ward names", "memory")
    prov = layer.dataProvider()
    prov.addAttributes(source.fields().toList())
    layer.updateFields()
    copied = [feat for feat in source.getFeatures() if str(feat["locator"] or "") in want]
    prov.addFeatures(copied)
    layer.updateExtents()
    print(f"  {slug} plate labels ({len(copied)}/{len(keepers)}): {', '.join(keepers)}")
    if len(copied) != len(keepers):
        got = {str(f["locator"]) for f in copied}
        print("  missing", [n for n in keepers if n not in got])
    _apply_pal_labels(
        layer,
        "locator",
        size=WARD_LABEL_PT,
        pinned=PINNED_LABELS.get(slug, ()),
        max_labels=max(len(copied), 1),
        min_mm=0.0,
        around=False,
    )
    layer.renderer().setSymbol(
        QgsFillSymbol.createSimple(
            {
                "color": "0,0,0,0",
                "outline_color": "0,0,0,0",
                "outline_width": "0",
                "outline_style": "no",
            }
        )
    )
    return layer


def _marker(name: str, color: str, size: str, outline: str = "255,255,255,230") -> QgsMarkerSymbol:
    return QgsMarkerSymbol.createSimple(
        {
            "name": name,
            "color": color,
            "outline_color": outline,
            "outline_width": "0.35",
            "size": size,
            "size_unit": "MM",
        }
    )


def _line(color: str, width: str) -> QgsLineSymbol:
    return QgsLineSymbol.createSimple(
        {
            "line_color": color,
            "line_width": width,
            "line_width_unit": "MM",
            "capstyle": "round",
            "joinstyle": "round",
        }
    )


def _grey_basemap() -> QgsRasterLayer:
    """Esri light grey. Carto's free tiles watermark the plate."""
    url = (
        "type=xyz&url=https://services.arcgisonline.com/ArcGIS/rest/services/"
        "Canvas/World_Light_Gray_Base/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D"
        "&zmax=16&zmin=0&crs=EPSG3857"
    )
    return QgsRasterLayer(url, "Grey base", "wms")


def _faint_roads(layer: QgsVectorLayer) -> None:
    """Street fabric in dusty khaki so it reads on the grey base without shouting."""
    if "highway" not in layer.fields().names():
        layer.renderer().setSymbol(_line("148,122,76,165", "0.14"))
        return

    def child(symbol, expr=None, *, else_rule=False, label=""):
        rule = QgsRuleBasedRenderer.Rule(symbol)
        rule.setLabel(label)
        if else_rule:
            rule.setIsElse(True)
        elif expr:
            rule.setFilterExpression(expr)
        return rule

    renderer = QgsRuleBasedRenderer(_line("156,132,86,140", "0.10"))
    root = renderer.rootRule()
    for old in list(root.children()):
        root.removeChild(old)
    root.appendChild(
        child(
            _line("138,116,70,200", "0.24"),
            "\"highway\" ILIKE '%motorway%' OR \"highway\" ILIKE '%trunk%' "
            "OR \"highway\" ILIKE '%primary%'",
            label="Main roads",
        )
    )
    root.appendChild(
        child(
            _line("150,128,82,170", "0.16"),
            "\"highway\" ILIKE '%secondary%' OR \"highway\" ILIKE '%tertiary%'",
            label="Other streets",
        )
    )
    root.appendChild(child(_line("162,142,96,140", "0.10"), else_rule=True, label="Walking streets"))
    layer.setRenderer(renderer)


def _veil_layer(city_utm: QgsGeometry, crs: str) -> QgsVectorLayer:
    bb = city_utm.boundingBox()
    pad = max(bb.width(), bb.height()) * 12.0
    world = QgsRectangle(
        bb.xMinimum() - pad,
        bb.yMinimum() - pad,
        bb.xMaximum() + pad,
        bb.yMaximum() + pad,
    )
    geom = QgsGeometry.fromRect(world).difference(city_utm)
    layer = _memory_polygon(geom, crs, "Outside study area")
    layer.renderer().setSymbol(
        QgsFillSymbol.createSimple(
            {
                "color": "250,248,244,220",
                "outline_color": "0,0,0,0",
                "outline_width": "0",
                "outline_style": "no",
            }
        )
    )
    return layer


def _nigeria_country() -> QgsGeometry:
    cache = PROCESSED / "nigeria_outline.gpkg"
    if cache.exists():
        lyr = QgsVectorLayer(f"{cache.as_posix()}|layername=nigeria_outline", "_nga_cache", "ogr")
        if lyr.isValid():
            for feat in lyr.getFeatures():
                g = feat.geometry()
                if g is not None and not g.isEmpty():
                    return QgsGeometry(g)
    src = QgsVectorLayer(str(ADM2_PATH), "_adm2", "ogr")
    if not src.isValid():
        raise RuntimeError(f"Could not load {ADM2_PATH.name}")
    bits = []
    for feat in src.getFeatures():
        g = feat.geometry()
        if g is None or g.isEmpty():
            continue
        bits.append(QgsGeometry(g))
    country = None
    if bits:
        try:
            country = QgsGeometry.unaryUnion(bits)
        except Exception:
            country = None
        if country is None or country.isEmpty():
            country = bits[0]
            for g in bits[1:]:
                country = country.combine(g)
    if country is None or country.isEmpty():
        raise RuntimeError("Nigeria dissolve failed")
    country = country.simplify(0.02)
    scratch = _memory_polygon(country, "EPSG:4326", "nigeria_outline")
    from qgis.core import QgsVectorFileWriter

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "GPKG"
    opts.layerName = "nigeria_outline"
    try:
        QgsVectorFileWriter.writeAsVectorFormatV2(
            scratch, str(cache), QgsProject.instance().transformContext(), opts
        )
    except Exception:
        pass
    return country


def _locator_point(aoi: QgsGeometry, name: str) -> QgsVectorLayer:
    layer = QgsVectorLayer("Point?crs=EPSG:4326", "City", "memory")
    prov = layer.dataProvider()
    prov.addAttributes([QgsField("name", QVariant.String)])
    layer.updateFields()
    feat = QgsFeature(layer.fields())
    feat.setGeometry(aoi.centroid())
    feat.setAttribute("name", name)
    prov.addFeature(feat)
    layer.updateExtents()
    layer.renderer().setSymbol(_marker("circle", "168,68,42,255", "2.8", outline="255,255,255,255"))

    settings = QgsPalLayerSettings()
    settings.fieldName = "name"
    settings.isExpression = False
    settings.placement = Qgis.LabelPlacement.AroundPoint
    settings.centroidInside = False
    settings.displayAll = True
    settings.obstacle = False
    settings.dist = 1.2
    settings.distUnits = QgsUnitTypes.RenderMillimeters
    settings.limitNumLabels = True
    settings.maxNumLabels = 1
    quad = getattr(Qgis, "LabelQuadrantPosition", None)
    if quad is not None:
        order = []
        for qname in ("Right", "AboveRight", "BelowRight", "Above", "Left"):
            val = getattr(quad, qname, None)
            if val is not None:
                order.append(val)
        if order:
            settings.predefinedPositionOrder = order

    fmt = QgsTextFormat()
    font = QFont("Arial", 8, QFont.Bold)
    fmt.setFont(font)
    fmt.setSize(8)
    fmt.setSizeUnit(QgsUnitTypes.RenderPoints)
    fmt.setColor(QColor(168, 68, 42))
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(0.9)
    buf.setSizeUnit(QgsUnitTypes.RenderMillimeters)
    buf.setColor(QColor(255, 255, 255))
    fmt.setBuffer(buf)
    settings.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    return layer


def _nigeria_locator_layers(aoi: QgsGeometry, city_name: str):
    """Nigeria outline on a grey base, with a labelled city point."""
    country = _nigeria_country()
    nga = _memory_polygon(country, "EPSG:4326", "Nigeria")
    nga.renderer().setSymbol(
        QgsFillSymbol.createSimple(
            {
                "color": "0,0,0,0",
                "outline_color": "55,52,46,255",
                "outline_width": "0.45",
                "outline_width_unit": "MM",
            }
        )
    )
    study = _memory_polygon(QgsGeometry(aoi), "EPSG:4326", "Study city")
    study.renderer().setSymbol(
        QgsFillSymbol.createSimple(
            {
                "color": "61,122,116,230",
                "outline_color": "28,60,58,255",
                "outline_width": "0.45",
                "outline_width_unit": "MM",
            }
        )
    )
    pin = _locator_point(aoi, city_name)
    bb = country.boundingBox()
    pad_x = bb.width() * 0.006
    pad_y = bb.height() * 0.006
    extent_wgs = QgsRectangle(
        bb.xMinimum() - pad_x,
        bb.yMinimum() - pad_y,
        bb.xMaximum() + pad_x,
        bb.yMaximum() + pad_y,
    )
    return nga, study, pin, extent_wgs


def _inventory_facilities(
    health: QgsVectorLayer,
    schools: QgsVectorLayer,
    mask: QgsGeometry | None,
    *,
    clinic_mm: str,
    school_mm: str,
) -> QgsVectorLayer:
    """One point layer: GRID3 clinics (squares) and schools (circles).

    Point displacement spreads marks that would otherwise sit on top of each
    other. Place names stay off this plate so labels do not cover the stock.
    """
    layer = QgsVectorLayer("Point?crs=EPSG:4326", "Clinics and schools", "memory")
    prov = layer.dataProvider()
    prov.addAttributes([QgsField("kind", QVariant.String)])
    layer.updateFields()
    copied = []
    for src, kind in ((health, "Clinic"), (schools, "School")):
        for feat in src.getFeatures():
            g = feat.geometry()
            if g is None or g.isEmpty():
                continue
            if mask is not None and not g.intersects(mask):
                continue
            row = QgsFeature(layer.fields())
            row.setGeometry(g)
            row.setAttribute("kind", kind)
            copied.append(row)
    if copied:
        prov.addFeatures(copied)
    layer.updateExtents()
    categories = [
        QgsRendererCategory(
            "Clinic",
            _marker("square", "178,34,34,240", clinic_mm),
            "Clinics",
        ),
        QgsRendererCategory(
            "School",
            _marker("circle", "25,80,120,230", school_mm),
            "Schools",
        ),
    ]
    categorized = QgsCategorizedSymbolRenderer("kind", categories)
    displaced = QgsPointDisplacementRenderer()
    displaced.setEmbeddedRenderer(categorized)
    displaced.setPlacement(QgsPointDisplacementRenderer.Ring)
    displaced.setTolerance(1.6)
    displaced.setToleranceUnit(QgsUnitTypes.RenderMillimeters)
    displaced.setCircleRadiusAddition(0.55)
    displaced.setLabelAttributeName("")
    displaced.setCenterSymbol(_marker("circle", "0,0,0,0", "0.15", outline="0,0,0,0"))
    layer.setRenderer(displaced)
    print(f"  inventory points {layer.featureCount():,} (clinics + schools)", flush=True)
    return layer


def _pt_breaks(alpha: int = PT_FILL_ALPHA) -> list:
    return [
        (lo, hi, "{},{},{},{}".format(*rgb, alpha), rng)
        for (lo, hi), rgb, rng in zip(pt_class_bounds(), PT_CLASS_RGB, PT_CLASS_RANGES)
    ]


# Shared with the PNG plates via proximity.classes, and identical in every city so two
# projects can be read against each other. Classes 1-3 sum to F15 by construction.
PT_BREAKS = _pt_breaks()


def _hex_field(slug: str, field: str, title: str) -> QgsVectorLayer:
    layer = _vector(PROCESSED / f"{slug}_hexes.gpkg", f"{slug}_hexes", title)
    layer.setSubsetString('"pop" > 5')
    _graduated(layer, field, _pt_breaks())
    return layer


def _rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def _item_map_box(item, origin_x: float = 8.0, origin_y: float = 8.0):
    """Top-left box of a layout item, in map-item millimetres."""
    top_left = item.positionAtReferencePoint(QgsLayoutItem.UpperLeft)
    size = item.sizeWithUnits()
    return (
        float(top_left.x()) - origin_x,
        float(top_left.y()) - origin_y,
        float(size.width()),
        float(size.height()),
    )


def _utm_union(layers, xform) -> QgsGeometry | None:
    merged = None
    for lyr in layers:
        if "Study boundary" not in lyr.name():
            continue
        for feat in lyr.getFeatures():
            g = feat.geometry()
            if g is None or g.isEmpty():
                continue
            gg = QgsGeometry(g)
            gg.transform(xform)
            merged = gg if merged is None else merged.combine(gg)
    if merged is None or merged.isEmpty():
        return None
    valid = merged.makeValid()
    return valid if valid is not None and not valid.isEmpty() else merged


def _hex_hull(layer, xform) -> QgsGeometry | None:
    """Convex hull of drawn hexes in UTM, buffered by one cell so edges miss furniture."""
    bits = []
    for feat in layer.getFeatures():
        g = feat.geometry()
        if g is None or g.isEmpty():
            continue
        gg = QgsGeometry(g)
        gg.transform(xform)
        bits.append(gg)
    if not bits:
        return None
    collected = QgsGeometry.collectGeometry(bits)
    if collected is None or collected.isEmpty():
        return None
    hull = collected.convexHull()
    if hull is None or hull.isEmpty():
        hull = collected
    return hull.buffer(180.0, 8)


def _hex_norm_xy(layer, xform, city: QgsRectangle):
    """Hex centroids in bbox-normalised page space (x right, y down, 0–1)."""
    xmin, ymax = city.xMinimum(), city.yMaximum()
    cw, ch = max(city.width(), 1.0), max(city.height(), 1.0)
    xs, ys = [], []
    for feat in layer.getFeatures():
        g = feat.geometry()
        if g is None or g.isEmpty():
            continue
        gg = g.centroid()
        gg.transform(xform)
        p = gg.asPoint()
        xs.append((p.x() - xmin) / cw)
        ys.append((ymax - p.y()) / ch)
    if not xs:
        return None
    return list(zip(xs, ys))


def _norm_geom(geom: QgsGeometry, city: QgsRectangle) -> QgsGeometry | None:
    """City polygon in bbox-normalised page space: x right, y down, both 0–1."""
    xmin, ymax = city.xMinimum(), city.yMaximum()
    cw, ch = max(city.width(), 1.0), max(city.height(), 1.0)

    def conv(p):
        x, y = (p.x(), p.y()) if hasattr(p, "x") else (p[0], p[1])
        return QgsPointXY((x - xmin) / cw, (ymax - y) / ch)

    def rings(poly):
        return [[conv(p) for p in ring] for ring in poly]

    g = QgsGeometry(geom)
    if g.isMultipart():
        mp = g.asMultiPolygon()
        if mp:
            return QgsGeometry.fromMultiPolygonXY([rings(poly) for poly in mp])
    poly = g.asPolygon()
    if poly:
        return QgsGeometry.fromPolygonXY(rings(poly))
    hull = g.convexHull().asPolygon()
    if hull:
        return QgsGeometry.fromPolygonXY(rings(hull))
    return None


def _framed_extent(
    city: QgsRectangle,
    item_w: float,
    item_h: float,
    *,
    boxes: list[tuple[float, float, float, float]],
    city_poly: QgsGeometry | None = None,
    hex_xy=None,
    slug: str = "",
) -> QgsRectangle:
    """Largest view that keeps drawn hexes off furniture, city mass at centre."""
    cw = max(city.width(), 1.0)
    ch = max(city.height(), 1.0)
    gap = FURNITURE_GAP
    padded = [(x - gap, y - gap, w + 2 * gap, h + 2 * gap) for x, y, w, h in boxes]
    pts = list(hex_xy) if hex_xy else None
    if pts is None and city_poly is not None and not city_poly.isEmpty():
        simplified = city_poly.simplify(max(cw, ch) / 200.0)
        if simplified is not None and not simplified.isEmpty():
            city_poly = simplified
    norm = _norm_geom(city_poly, city) if pts is None and city_poly is not None else None
    mx, my = 0.5, 0.5
    # Compact cities fill the page. Lagos stays in the title/footnote band
    # because the peninsula is wide and the furniture has to keep the shore.
    tight = slug in {"ibadan", "kano", "abuja", "port_harcourt"}

    top_block = 3.0
    bot_block = item_h - 3.0
    for x, y, w, h in padded:
        mid = y + 0.5 * h
        if mid < 0.42 * item_h:
            top_block = max(top_block, y + h)
        elif mid > 0.55 * item_h:
            bot_block = min(bot_block, y)

    def hits(cx: float, cy: float, wmm: float, hmm: float) -> bool:
        if pts is not None:
            for x, y, w, h in padded:
                x1 = x + w
                y1 = y + h
                for px, py in pts:
                    qx = cx + px * wmm
                    qy = cy + py * hmm
                    if x <= qx <= x1 and y <= qy <= y1:
                        return True
            return False
        if norm is None:
            city_box = (cx, cy, wmm, hmm)
            return any(_rects_overlap(city_box, b) for b in padded)
        for x, y, w, h in padded:
            fg = QgsGeometry.fromRect(
                QgsRectangle((x - cx) / wmm, (y - cy) / hmm, (x + w - cx) / wmm, (y + h - cy) / hmm)
            )
            if norm.intersects(fg):
                return True
        return False

    def place(city_w_mm: float, nx: int = 13, ny: int = 11, *, slack: float | None = 8.0):
        city_h_mm = city_w_mm * ch / cw
        x0 = 3.0
        x1 = item_w - 3.0 - city_w_mm
        if tight:
            y0 = 3.0
            y1 = item_h - 3.0 - city_h_mm
        else:
            y0 = max(3.0, top_block)
            y1 = min(item_h - 3.0 - city_h_mm, bot_block - city_h_mm)
        if x1 < x0 or y1 < y0:
            return None
        tx = min(max(0.5 * item_w - mx * city_w_mm, x0), x1)
        ty = min(max(0.5 * item_h - my * city_h_mm, y0), y1) if tight else y1
        best = None
        best_d = 1e18
        for i in range(nx):
            cx = x0 if nx == 1 else x0 + (x1 - x0) * i / (nx - 1)
            for j in range(ny):
                cy = y0 if ny == 1 else y0 + (y1 - y0) * j / (ny - 1)
                if slack is not None and abs(cx - tx) > slack:
                    continue
                if hits(cx, cy, city_w_mm, city_h_mm):
                    continue
                d = (cx - tx) ** 2 + (cy - ty) ** 2
                if d < best_d:
                    best, best_d = (cx, cy, city_w_mm, city_h_mm), d
        return best

    if tight:
        lo, hi = 40.0, min(item_w - 6.0, (item_h - 6.0) * cw / ch)
    else:
        inner_h = max(bot_block - top_block, 80.0)
        fit_w = min(item_w - 6.0, inner_h * cw / ch)
        lo, hi = 40.0, max(fit_w, 40.0)
    best = place(lo)
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        placed = place(mid)
        if placed is None:
            hi = mid
        else:
            best = placed
            lo = mid
    if best is None:
        best = place(lo, slack=None)
        for _ in range(16):
            mid = 0.5 * (lo + hi)
            placed = place(mid, slack=None)
            if placed is None:
                hi = mid
            else:
                best = placed
                lo = mid
    if best is None:
        raise RuntimeError("could not place city in layout")
    refined = place(best[2], nx=32, ny=22)
    if refined is None:
        refined = place(best[2], nx=32, ny=22, slack=None)
    if refined is not None:
        best = refined
    city_x, city_y, city_w_mm, city_h_mm = best
    print(
        f"    city {city_w_mm:.0f}×{city_h_mm:.0f} mm on {item_w:.0f}×{item_h:.0f}"
        f"  mass=({mx:.2f},{my:.2f}) origin=({city_x:.0f},{city_y:.0f})"
    )
    view_w = item_w * cw / city_w_mm
    view_h = item_h * ch / city_h_mm
    xmin = city.xMinimum() - city_x / item_w * view_w
    ymax = city.yMaximum() + city_y / item_h * view_h
    return QgsRectangle(xmin, ymax - view_h, xmin + view_w, ymax)


def _halo_label(
    layout: QgsPrintLayout,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    pt: float = 7.0,
) -> QgsLayoutItemLabel:
    """Small credit type: black fill, white buffer, no box."""
    item = QgsLayoutItemLabel(layout)
    item.setText(text)
    fmt = QgsTextFormat()
    fmt.setFont(QFont("Arial", int(pt)))
    fmt.setSize(pt)
    fmt.setSizeUnit(QgsUnitTypes.RenderPoints)
    fmt.setColor(QColor(0, 0, 0))
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(0.6)
    buf.setSizeUnit(QgsUnitTypes.RenderMillimeters)
    buf.setColor(QColor(255, 255, 255))
    fmt.setBuffer(buf)
    item.setTextFormat(fmt)
    item.setHAlign(Qt.AlignRight)
    item.setVAlign(Qt.AlignBottom)
    item.setMargin(0)
    item.setZValue(22)
    _place(layout, item, x, y, w, h)
    return item


def _white_box(layout: QgsPrintLayout, x: float, y: float, w: float, h: float) -> QgsLayoutItemShape:
    box = QgsLayoutItemShape(layout)
    box.setShapeType(QgsLayoutItemShape.Rectangle)
    box.setSymbol(
        QgsFillSymbol.createSimple(
            {
                "color": "255,255,255,255",
                "outline_color": "0,0,0,255",
                "outline_width": "0.45",
                "outline_width_unit": "MM",
            }
        )
    )
    box.setFrameEnabled(False)
    box.setZValue(20)
    _place(layout, box, x, y, w, h)
    return box


def _place(layout: QgsPrintLayout, item, x: float, y: float, w: float | None = None, h: float | None = None) -> None:
    """Add the item, then move it. attemptMove is a no-op until the item is on the layout."""
    layout.addLayoutItem(item)
    item.attemptMove(QgsLayoutPoint(x, y, MM))
    if w is not None and h is not None:
        item.attemptResize(QgsLayoutSize(w, h, MM))


def _legend_class_count(layer: QgsVectorLayer) -> int:
    renderer = layer.renderer()
    ranges = getattr(renderer, "ranges", lambda: [])()
    return max(len(ranges), 1)


def _pin_legend(legend: QgsLayoutItemLegend, layer: QgsVectorLayer, *, x: float = 14.0, bottom: float = 283.0) -> tuple[float, float]:
    """Pack the legend to its classes and pin the lower-left corner.

    QGIS often reports a huge box after adjustBoxSize. Empty white inside the
    frame is the defect — size from the class count, then keep a 2.2 mm inset.
    """
    n = _legend_class_count(layer)
    pad = float(legend.boxSpace())
    row = float(legend.symbolHeight()) + 1.05
    target_w = 54.0
    target_h = 2.0 * pad + 6.4 + n * row
    legend.setLegendFilterByMapEnabled(False)
    legend.setColumnCount(1)
    legend.setResizeToContents(True)
    legend.setReferencePoint(QgsLayoutItem.UpperLeft)
    legend.attemptMove(QgsLayoutPoint(x, 200.0, MM))
    legend.attemptResize(QgsLayoutSize(target_w, target_h, MM))
    legend.refresh()
    legend.adjustBoxSize()
    measured = legend.sizeWithUnits()
    mw = float(measured.width())
    mh = float(measured.height())
    w = mw if 46.0 <= mw <= target_w + 6.0 else target_w
    # Never keep a measured height that is taller than the class stack.
    h = mh if 24.0 <= mh <= target_h + 1.5 else target_h
    h = min(h, target_h)
    legend.setResizeToContents(False)
    legend.setReferencePoint(QgsLayoutItem.LowerLeft)
    legend.attemptResize(QgsLayoutSize(w, h, MM))
    legend.attemptMove(QgsLayoutPoint(x, bottom, MM))
    print(f"    legend measured {mw:.1f}×{mh:.1f} mm → {w:.1f}×{h:.1f} mm ({n} classes)")
    return w, h


def _kigali_layout(
    project: QgsProject,
    slug: str,
    *,
    layout_name: str,
    choropleth: QgsVectorLayer,
    overlays: list,
    osm: QgsRasterLayer,
    extent_wgs: QgsRectangle,
    title: str,
    subtitle: str,
    caption: str,
    legend_title: str,
    export_stem: str,
) -> Path:
    """Print layout: Kigali furniture around an already-styled choropleth.

    Layer renderers are not modified. The layout only chooses which layers are
    visible and draws title / footnote / north / legend / scale / credit
    inside the neatline, with no overlap onto the city outline.
    """
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(layout_name)
    for item in list(layout.items()):
        if isinstance(item, QgsLayoutItemMap):
            layout.removeLayoutItem(item)
    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(420, 297, MM))

    utm = QgsCoordinateReferenceSystem(CITY_UTM[slug])
    xform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"),
        utm,
        project.transformContext(),
    )
    ext = xform.transformBoundingBox(extent_wgs)
    bound_poly = _utm_union(overlays, xform)
    city_poly = _hex_hull(choropleth, xform)
    # Clipped plates: the dissolve is the city, not a convex hull of leftover hexes.
    if slug in {"abuja", "lagos"} and bound_poly is not None and not bound_poly.isEmpty():
        city_poly = bound_poly
    elif city_poly is None or city_poly.isEmpty():
        city_poly = bound_poly
    if city_poly is not None and not city_poly.isEmpty():
        ext = city_poly.boundingBox()
    hex_xy = _hex_norm_xy(choropleth, xform, ext)
    title_w = {"lagos": 148.0, "abuja": 148.0}.get(slug, 172.0)

    map_item = QgsLayoutItemMap(layout)
    map_item.setFrameEnabled(True)
    map_item.setFrameStrokeColor(QColor(0, 0, 0))
    map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.55, MM))
    map_item.setBackgroundColor(QColor("#f3efe6"))
    map_item.setCrs(utm)
    map_item.setKeepLayerSet(True)
    map_item.setKeepLayerStyles(True)
    # First in this list is drawn last (on top). OSM is the geographic base.
    map_item.setLayers(list(overlays) + [choropleth, osm])
    map_item.setZValue(0)
    _place(layout, map_item, 8, 8, FRAME_W, FRAME_H)
    map_item.setCrs(utm)
    map_item.attemptMove(QgsLayoutPoint(8, 8, MM))
    map_item.attemptResize(QgsLayoutSize(FRAME_W, FRAME_H, MM))
    map_item.setFixedSize(QgsLayoutSize(FRAME_W, FRAME_H, MM))
    map_item.setExtent(ext)
    map_item.refresh()

    title_panel = _white_box(layout, 8, 8, title_w, TITLE_H)

    label = QgsLayoutItemLabel(layout)
    label.setText(f"{title}\n{subtitle}")
    label.setFont(QFont("Arial", 15, QFont.Bold))
    label.setFontColor(QColor(0, 0, 0))
    label.setHAlign(Qt.AlignHCenter)
    label.setVAlign(Qt.AlignVCenter)
    label.setMargin(2.0)
    label.setZValue(21)
    _place(layout, label, 8, 8, title_w, TITLE_H)

    north = QgsLayoutItemPicture(layout)
    north.setMode(QgsLayoutItemPicture.FormatSVG)
    north.setPicturePath(str(NORTH_SVG))
    north.setLinkedMap(map_item)
    north.setNorthMode(QgsLayoutItemPicture.GridNorth)
    north.setFrameEnabled(False)
    north.setBackgroundEnabled(False)
    north.setZValue(20)
    _place(layout, north, 372, 10, 34, 42)

    legend = QgsLayoutItemLegend(layout)
    legend.setLinkedMap(map_item)
    legend.setTitle(legend_title)
    legend.setTitleAlignment(Qt.AlignLeft)
    legend.setStyleFont(QgsLegendStyle.Title, QFont("Arial", 13, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.Subgroup, QFont("Arial", 12))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Arial", 12))
    legend.setFontColor(QColor(0, 0, 0))
    legend.setSymbolWidth(5.2)
    legend.setSymbolHeight(4.2)
    legend.setBoxSpace(2.2)
    legend.setLineSpacing(0.2)
    legend.setStyleMargin(QgsLegendStyle.Title, 0.2)
    legend.setStyleMargin(QgsLegendStyle.Title, QgsLegendStyle.Bottom, 1.1)
    legend.setStyleMargin(QgsLegendStyle.Symbol, 0.3)
    legend.setStyleMargin(QgsLegendStyle.SymbolLabel, 0.25)
    legend.setStyleMargin(QgsLegendStyle.SymbolLabel, QgsLegendStyle.Left, 1.2)
    legend.setFrameEnabled(True)
    legend.setFrameStrokeColor(QColor(0, 0, 0))
    legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.45, MM))
    legend.setBackgroundColor(QColor(255, 255, 255))
    legend.setBackgroundEnabled(True)
    legend.setAutoUpdateModel(False)
    root = legend.model().rootGroup()
    for child in list(root.children()):
        root.removeChildNode(child)
    node = root.addLayer(choropleth)
    QgsLegendRenderer.setNodeLegendStyle(node, QgsLegendStyle.Hidden)
    legend.setZValue(20)
    layout.addLayoutItem(legend)
    node.setExpanded(True)
    legend.refresh()
    leg_w, _leg_h = _pin_legend(legend, choropleth)

    scale = QgsLayoutItemScaleBar(layout)
    scale.setLinkedMap(map_item)
    scale.setStyle("Line Ticks Up")
    scale.setUnits(QgsUnitTypes.DistanceKilometers)
    scale.setSegmentSizeMode(QgsScaleBarSettings.SegmentSizeFitWidth)
    scale.setMinimumBarWidth(62)
    scale.setMaximumBarWidth(82)
    scale.setNumberOfSegments(2)
    scale.setNumberOfSegmentsLeft(0)
    scale.setUnitLabel("km")
    scale.setFont(QFont("Arial", 11))
    scale.setFontColor(QColor(0, 0, 0))
    scale.setHeight(2.4)
    scale.setLineWidth(0.5)
    scale.setLineColor(QColor(0, 0, 0))
    scale.setBoxContentSpace(1.4)
    scale.setFrameEnabled(False)
    scale.setBackgroundEnabled(False)
    scale.setZValue(20)
    layout.addLayoutItem(scale)
    scale.refresh()
    scale.setReferencePoint(QgsLayoutItem.LowerRight)
    scale.attemptMove(QgsLayoutPoint(400, 283, MM))
    scale.refresh()

    scale_w = scale.sizeWithUnits().width()
    gap_left = 14.0 + leg_w + FURNITURE_GAP
    gap_right = 400.0 - scale_w - FURNITURE_GAP
    avail = max(gap_right - gap_left, 80.0)
    note_w = min(NOTE_W, avail)
    note_x = gap_left + 0.5 * (avail - note_w)
    note_y = 8 + FRAME_H - NOTE_BOTTOM - NOTE_H
    note_panel = _white_box(layout, note_x, note_y, note_w, NOTE_H)
    note = QgsLayoutItemLabel(layout)
    note.setMode(QgsLayoutItemLabel.ModeFont)
    note.setText(caption)
    note.setFont(QFont("Arial", NOTE_FONT_PT, QFont.Bold))
    note.setFontColor(QColor(0, 0, 0))
    note.setHAlign(Qt.AlignHCenter)
    note.setVAlign(Qt.AlignVCenter)
    note.setMargin(3.0)
    note.setZValue(21)
    _place(layout, note, note_x, note_y, note_w, NOTE_H)

    credit = _halo_label(
        layout,
        CREDIT,
        400.0 - scale_w,
        283.0 - scale.sizeWithUnits().height() - 9.0,
        scale_w,
        8.0,
        pt=8,
    )

    def _grow(box, pad):
        x, y, w, h = box
        return (x - pad, y - pad, w + 2 * pad, h + 2 * pad)

    title_box = _item_map_box(title_panel)
    tx, ty, tw, th = title_box
    title_pad = 4.0 if slug in {"abuja", "port_harcourt"} else 8.0
    title_box = (tx, ty, tw, th + title_pad)
    vis = _item_map_box(legend)
    legend_box = vis
    boxes = [
        title_box,
        _item_map_box(north),
        _grow(legend_box, BOTTOM_CLEAR),
        _grow(_item_map_box(note_panel), BOTTOM_CLEAR),
        _grow(_item_map_box(scale), BOTTOM_CLEAR),
        _grow(_item_map_box(credit), BOTTOM_CLEAR),
    ]
    extent = _framed_extent(
        ext, FRAME_W, FRAME_H, boxes=boxes, city_poly=city_poly, hex_xy=hex_xy, slug=slug
    )
    map_item.setExtent(extent)
    map_item.refresh()
    scale.refresh()

    project.layoutManager().addLayout(layout)

    MAPS.mkdir(parents=True, exist_ok=True)
    png = MAPS / f"{slug}_{export_stem}.png"
    for path in (png, png.with_suffix(".pdf")):
        if path.exists():
            path.unlink()
    exporter = QgsLayoutExporter(layout)
    img = QgsLayoutExporter.ImageExportSettings()
    img.dpi = 200
    img.generateWorldFile = False
    img.exportMetadata = False
    img.cropToContents = False
    status = exporter.exportToImage(str(png), img)
    if status != QgsLayoutExporter.Success:
        raise RuntimeError(f"layout export failed for {png.name}: {status}")
    pdf_settings = QgsLayoutExporter.PdfExportSettings()
    exporter.exportToPdf(str(png.with_suffix(".pdf")), pdf_settings)
    return png


def _inventory_layout(
    project: QgsProject,
    slug: str,
    *,
    roads: QgsVectorLayer,
    facilities: QgsVectorLayer,
    overlays: list,
    osm: QgsRasterLayer,
    extent_wgs: QgsRectangle,
    title: str,
    subtitle: str,
    caption: str,
) -> Path:
    """Clinics, schools and walking streets. Same A3 furniture as the score plates."""
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("Clinics, schools and streets")
    for item in list(layout.items()):
        if isinstance(item, QgsLayoutItemMap):
            layout.removeLayoutItem(item)
    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(420, 297, MM))

    utm = QgsCoordinateReferenceSystem(CITY_UTM[slug])
    xform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"),
        utm,
        project.transformContext(),
    )
    ext = xform.transformBoundingBox(extent_wgs)
    bound_poly = _utm_union(overlays, xform)
    city_poly = bound_poly
    if city_poly is not None and not city_poly.isEmpty():
        ext = city_poly.boundingBox()
    title_w = {"lagos": 148.0, "abuja": 148.0}.get(slug, 172.0)

    map_item = QgsLayoutItemMap(layout)
    map_item.setFrameEnabled(True)
    map_item.setFrameStrokeColor(QColor(0, 0, 0))
    map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.55, MM))
    map_item.setBackgroundColor(QColor("#f3efe6"))
    map_item.setCrs(utm)
    map_item.setKeepLayerSet(True)
    map_item.setKeepLayerStyles(True)
    map_item.setLayers(list(overlays) + [facilities, roads, osm])
    map_item.setZValue(0)
    _place(layout, map_item, 8, 8, FRAME_W, FRAME_H)
    map_item.setCrs(utm)
    map_item.attemptMove(QgsLayoutPoint(8, 8, MM))
    map_item.attemptResize(QgsLayoutSize(FRAME_W, FRAME_H, MM))
    map_item.setFixedSize(QgsLayoutSize(FRAME_W, FRAME_H, MM))
    map_item.setExtent(ext)
    map_item.refresh()

    title_panel = _white_box(layout, 8, 8, title_w, TITLE_H)
    label = QgsLayoutItemLabel(layout)
    label.setText(f"{title}\n{subtitle}")
    label.setFont(QFont("Arial", 15, QFont.Bold))
    label.setFontColor(QColor(0, 0, 0))
    label.setHAlign(Qt.AlignHCenter)
    label.setVAlign(Qt.AlignVCenter)
    label.setMargin(2.0)
    label.setZValue(21)
    _place(layout, label, 8, 8, title_w, TITLE_H)

    north = QgsLayoutItemPicture(layout)
    north.setMode(QgsLayoutItemPicture.FormatSVG)
    north.setPicturePath(str(NORTH_SVG))
    north.setLinkedMap(map_item)
    north.setNorthMode(QgsLayoutItemPicture.GridNorth)
    north.setFrameEnabled(False)
    north.setBackgroundEnabled(False)
    north.setZValue(20)
    _place(layout, north, 372, 10, 34, 42)

    legend = QgsLayoutItemLegend(layout)
    legend.setLinkedMap(map_item)
    legend.setTitle("Clinics and schools")
    legend.setTitleAlignment(Qt.AlignLeft)
    legend.setStyleFont(QgsLegendStyle.Title, QFont("Arial", 13, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.Subgroup, QFont("Arial", 12))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Arial", 12))
    legend.setFontColor(QColor(0, 0, 0))
    legend.setSymbolWidth(5.2)
    legend.setSymbolHeight(4.2)
    legend.setBoxSpace(2.2)
    legend.setLineSpacing(0.2)
    legend.setStyleMargin(QgsLegendStyle.Title, 0.2)
    legend.setStyleMargin(QgsLegendStyle.Title, QgsLegendStyle.Bottom, 1.1)
    legend.setStyleMargin(QgsLegendStyle.Symbol, 0.3)
    legend.setStyleMargin(QgsLegendStyle.SymbolLabel, 0.25)
    legend.setStyleMargin(QgsLegendStyle.SymbolLabel, QgsLegendStyle.Left, 1.2)
    legend.setFrameEnabled(True)
    legend.setFrameStrokeColor(QColor(0, 0, 0))
    legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.45, MM))
    legend.setBackgroundColor(QColor(255, 255, 255))
    legend.setBackgroundEnabled(True)
    legend.setAutoUpdateModel(False)
    root = legend.model().rootGroup()
    for child in list(root.children()):
        root.removeChildNode(child)
    # Displacement renderer flattens the legend to dots. Proxy layers keep
    # the square (clinic) and circle (school) that the map actually uses.
    legend_clinic = QgsVectorLayer("Point?crs=EPSG:4326", "Clinics", "memory")
    legend_clinic.renderer().setSymbol(_marker("square", "178,34,34,240", "2.4"))
    legend_school = QgsVectorLayer("Point?crs=EPSG:4326", "Schools", "memory")
    legend_school.renderer().setSymbol(_marker("circle", "25,80,120,230", "2.2"))
    project.addMapLayer(legend_clinic, False)
    project.addMapLayer(legend_school, False)
    for layer in (legend_clinic, legend_school, roads):
        node = root.addLayer(layer)
        QgsLegendRenderer.setNodeLegendStyle(node, QgsLegendStyle.Hidden)
        node.setExpanded(True)
    legend.setZValue(20)
    layout.addLayoutItem(legend)
    legend.refresh()
    pad = float(legend.boxSpace())
    w = 58.0
    h = pad * 2 + 15.0 + 3 * (float(legend.symbolHeight()) + 0.9)
    h = min(max(h, 32.0), 40.0)
    legend.setResizeToContents(False)
    legend.setReferencePoint(QgsLayoutItem.LowerLeft)
    legend.attemptResize(QgsLayoutSize(w, h, MM))
    legend.attemptMove(QgsLayoutPoint(14.0, 283.0, MM))
    leg_w = w

    scale = QgsLayoutItemScaleBar(layout)
    scale.setLinkedMap(map_item)
    scale.setStyle("Line Ticks Up")
    scale.setUnits(QgsUnitTypes.DistanceKilometers)
    scale.setSegmentSizeMode(QgsScaleBarSettings.SegmentSizeFitWidth)
    scale.setMinimumBarWidth(62)
    scale.setMaximumBarWidth(82)
    scale.setNumberOfSegments(2)
    scale.setNumberOfSegmentsLeft(0)
    scale.setUnitLabel("km")
    scale.setFont(QFont("Arial", 11))
    scale.setFontColor(QColor(0, 0, 0))
    scale.setHeight(2.4)
    scale.setLineWidth(0.5)
    scale.setLineColor(QColor(0, 0, 0))
    scale.setBoxContentSpace(1.4)
    scale.setFrameEnabled(False)
    scale.setBackgroundEnabled(False)
    scale.setZValue(20)
    layout.addLayoutItem(scale)
    scale.refresh()
    scale.setReferencePoint(QgsLayoutItem.LowerRight)
    scale.attemptMove(QgsLayoutPoint(400, 283, MM))
    scale.refresh()

    scale_w = scale.sizeWithUnits().width()
    gap_left = 14.0 + leg_w + FURNITURE_GAP
    gap_right = 400.0 - scale_w - FURNITURE_GAP
    avail = max(gap_right - gap_left, 80.0)
    note_w = min(NOTE_W, avail)
    note_x = gap_left + 0.5 * (avail - note_w)
    note_y = 8 + FRAME_H - NOTE_BOTTOM - NOTE_H
    note_panel = _white_box(layout, note_x, note_y, note_w, NOTE_H)
    note = QgsLayoutItemLabel(layout)
    note.setMode(QgsLayoutItemLabel.ModeFont)
    note.setText(caption)
    note.setFont(QFont("Arial", NOTE_FONT_PT, QFont.Bold))
    note.setFontColor(QColor(0, 0, 0))
    note.setHAlign(Qt.AlignHCenter)
    note.setVAlign(Qt.AlignVCenter)
    note.setMargin(3.0)
    note.setZValue(21)
    _place(layout, note, note_x, note_y, note_w, NOTE_H)

    credit = _halo_label(
        layout,
        CREDIT,
        400.0 - scale_w,
        283.0 - scale.sizeWithUnits().height() - 9.0,
        scale_w,
        8.0,
        pt=8,
    )

    def _grow(box, pad_mm):
        x, y, bw, bh = box
        return (x - pad_mm, y - pad_mm, bw + 2 * pad_mm, bh + 2 * pad_mm)

    title_box = _item_map_box(title_panel)
    tx, ty, tw, th = title_box
    title_pad = 4.0 if slug in {"abuja", "port_harcourt"} else 8.0
    title_box = (tx, ty, tw, th + title_pad)
    boxes = [
        title_box,
        _item_map_box(north),
        _grow(_item_map_box(legend), BOTTOM_CLEAR),
        _grow(_item_map_box(note_panel), BOTTOM_CLEAR),
        _grow(_item_map_box(scale), BOTTOM_CLEAR),
        _grow(_item_map_box(credit), BOTTOM_CLEAR),
    ]
    extent = _framed_extent(
        ext, FRAME_W, FRAME_H, boxes=boxes, city_poly=city_poly, hex_xy=None, slug=slug
    )
    map_item.setExtent(extent)
    map_item.refresh()
    scale.refresh()

    project.layoutManager().addLayout(layout)

    MAPS.mkdir(parents=True, exist_ok=True)
    png = MAPS / f"{slug}_inventory_plate.png"
    for path in (png, png.with_suffix(".pdf")):
        if path.exists():
            path.unlink()
    exporter = QgsLayoutExporter(layout)
    img = QgsLayoutExporter.ImageExportSettings()
    img.dpi = 200
    img.generateWorldFile = False
    img.exportMetadata = False
    img.cropToContents = False
    status = exporter.exportToImage(str(png), img)
    if status != QgsLayoutExporter.Success:
        raise RuntimeError(f"layout export failed for {png.name}: {status}")
    exporter.exportToPdf(str(png.with_suffix(".pdf")), QgsLayoutExporter.PdfExportSettings())
    return png


def _study_area_layout(
    project: QgsProject,
    slug: str,
    *,
    roads: QgsVectorLayer,
    facilities: QgsVectorLayer,
    overlays: list,
    grey: QgsRasterLayer | None,
    veil: QgsVectorLayer | None,
    nga: QgsVectorLayer,
    aoi_layer: QgsVectorLayer,
    locator_pin: QgsVectorLayer,
    locator_extent_wgs: QgsRectangle,
    extent_wgs: QgsRectangle,
    title: str,
    subtitle: str,
    caption: str,
) -> Path:
    """Study-area plate: grey base, faint streets, ward names, Nigeria inset."""
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("Study area")
    for item in list(layout.items()):
        if isinstance(item, QgsLayoutItemMap):
            layout.removeLayoutItem(item)
    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(420, 297, MM))

    utm = QgsCoordinateReferenceSystem(CITY_UTM[slug])
    xform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"),
        utm,
        project.transformContext(),
    )
    ext = xform.transformBoundingBox(extent_wgs)
    bound_poly = _utm_union(overlays, xform)
    city_poly = bound_poly
    if city_poly is not None and not city_poly.isEmpty():
        ext = city_poly.boundingBox()
    title_w = 128.0

    layers = [facilities] + list(overlays)
    if roads is not None:
        layers.append(roads)
    if veil is not None:
        layers.append(veil)
    if grey is not None:
        layers.append(grey)

    map_item = QgsLayoutItemMap(layout)
    map_item.setFrameEnabled(True)
    map_item.setFrameStrokeColor(QColor(0, 0, 0))
    map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.55, MM))
    map_item.setBackgroundColor(QColor("#eceae4"))
    map_item.setCrs(utm)
    map_item.setKeepLayerSet(True)
    map_item.setKeepLayerStyles(True)
    map_item.setLayers(layers)
    map_item.setZValue(0)
    _place(layout, map_item, 8, 8, FRAME_W, FRAME_H)
    map_item.setCrs(utm)
    map_item.attemptMove(QgsLayoutPoint(8, 8, MM))
    map_item.attemptResize(QgsLayoutSize(FRAME_W, FRAME_H, MM))
    map_item.setFixedSize(QgsLayoutSize(FRAME_W, FRAME_H, MM))
    map_item.setExtent(ext)
    map_item.refresh()

    title_panel = _white_box(layout, 8, 8, title_w, TITLE_H)
    label = QgsLayoutItemLabel(layout)
    label.setText(f"{title}\n{subtitle}")
    label.setFont(QFont("Arial", 15, QFont.Bold))
    label.setFontColor(QColor(0, 0, 0))
    label.setHAlign(Qt.AlignHCenter)
    label.setVAlign(Qt.AlignVCenter)
    label.setMargin(2.0)
    label.setZValue(21)
    _place(layout, label, 8, 8, title_w, TITLE_H)

    north = QgsLayoutItemPicture(layout)
    north.setMode(QgsLayoutItemPicture.FormatSVG)
    north.setPicturePath(str(NORTH_SVG))
    north.setLinkedMap(map_item)
    north.setNorthMode(QgsLayoutItemPicture.GridNorth)
    north.setFrameEnabled(False)
    north.setBackgroundEnabled(False)
    north.setZValue(24)
    _place(layout, north, 380, 10, 26, 32)

    to_web = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"),
        QgsCoordinateReferenceSystem("EPSG:3857"),
        project.transformContext(),
    )
    loc_ext = to_web.transformBoundingBox(locator_extent_wgs)
    loc_h = 28.0
    loc_w = loc_h * (loc_ext.width() / loc_ext.height())
    loc_x = 380.0 + 26.0 - loc_w
    loc_y = 44.0
    loc_map = QgsLayoutItemMap(layout)
    loc_map.setFrameEnabled(True)
    loc_map.setFrameStrokeColor(QColor(0, 0, 0))
    loc_map.setFrameStrokeWidth(QgsLayoutMeasurement(0.35, MM))
    loc_map.setBackgroundColor(QColor("#eceae4"))
    loc_map.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
    loc_map.setKeepLayerSet(True)
    loc_map.setKeepLayerStyles(True)
    loc_map.setLayers([locator_pin, aoi_layer, nga, grey] if grey is not None else [locator_pin, aoi_layer, nga])
    loc_map.setZValue(22)
    _place(layout, loc_map, loc_x, loc_y, loc_w, loc_h)
    loc_map.setExtent(loc_ext)
    loc_map.refresh()

    legend = QgsLayoutItemLegend(layout)
    legend.setLinkedMap(map_item)
    legend.setTitle("On this map")
    legend.setTitleAlignment(Qt.AlignLeft)
    legend.setStyleFont(QgsLegendStyle.Title, QFont("Arial", 13, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.Subgroup, QFont("Arial", 12))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Arial", 12))
    legend.setFontColor(QColor(0, 0, 0))
    legend.setSymbolWidth(5.2)
    legend.setSymbolHeight(4.2)
    legend.setBoxSpace(2.2)
    legend.setLineSpacing(0.2)
    legend.setStyleMargin(QgsLegendStyle.Title, 0.2)
    legend.setStyleMargin(QgsLegendStyle.Title, QgsLegendStyle.Bottom, 1.1)
    legend.setStyleMargin(QgsLegendStyle.Symbol, 0.3)
    legend.setStyleMargin(QgsLegendStyle.SymbolLabel, 0.25)
    legend.setStyleMargin(QgsLegendStyle.SymbolLabel, QgsLegendStyle.Left, 1.2)
    legend.setFrameEnabled(True)
    legend.setFrameStrokeColor(QColor(0, 0, 0))
    legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.45, MM))
    legend.setBackgroundColor(QColor(255, 255, 255))
    legend.setBackgroundEnabled(True)
    legend.setAutoUpdateModel(False)
    root = legend.model().rootGroup()
    for child in list(root.children()):
        root.removeChildNode(child)
    legend_clinic = QgsVectorLayer("Point?crs=EPSG:4326", "Clinics", "memory")
    legend_clinic.renderer().setSymbol(_marker("square", "178,34,34,240", "2.4"))
    legend_school = QgsVectorLayer("Point?crs=EPSG:4326", "Schools", "memory")
    legend_school.renderer().setSymbol(_marker("circle", "25,80,120,230", "2.2"))
    legend_road = QgsVectorLayer("LineString?crs=EPSG:4326", "Walking streets", "memory")
    legend_road.renderer().setSymbol(_line("148,122,76,230", "0.55"))
    project.addMapLayer(legend_clinic, False)
    project.addMapLayer(legend_school, False)
    project.addMapLayer(legend_road, False)
    for layer in (legend_clinic, legend_school, legend_road):
        node = root.addLayer(layer)
        QgsLegendRenderer.setNodeLegendStyle(node, QgsLegendStyle.Hidden)
        node.setExpanded(True)
    legend.setZValue(20)
    layout.addLayoutItem(legend)
    legend.refresh()
    pad = float(legend.boxSpace())
    w = 58.0
    h = pad * 2 + 15.0 + 3 * (float(legend.symbolHeight()) + 0.9)
    h = min(max(h, 32.0), 42.0)
    legend.setResizeToContents(False)
    legend.setReferencePoint(QgsLayoutItem.LowerLeft)
    legend.attemptResize(QgsLayoutSize(w, h, MM))
    legend.attemptMove(QgsLayoutPoint(14.0, 283.0, MM))
    leg_w = w

    scale = QgsLayoutItemScaleBar(layout)
    scale.setLinkedMap(map_item)
    scale.setStyle("Line Ticks Up")
    scale.setUnits(QgsUnitTypes.DistanceKilometers)
    scale.setSegmentSizeMode(QgsScaleBarSettings.SegmentSizeFitWidth)
    scale.setMinimumBarWidth(62)
    scale.setMaximumBarWidth(82)
    scale.setNumberOfSegments(2)
    scale.setNumberOfSegmentsLeft(0)
    scale.setUnitLabel("km")
    scale.setFont(QFont("Arial", 11))
    scale.setFontColor(QColor(0, 0, 0))
    scale.setHeight(2.4)
    scale.setLineWidth(0.5)
    scale.setLineColor(QColor(0, 0, 0))
    scale.setBoxContentSpace(1.4)
    scale.setFrameEnabled(False)
    scale.setBackgroundEnabled(False)
    scale.setZValue(20)
    layout.addLayoutItem(scale)
    scale.refresh()
    scale.setReferencePoint(QgsLayoutItem.LowerRight)
    scale.attemptMove(QgsLayoutPoint(400, 283, MM))
    scale.refresh()

    scale_w = scale.sizeWithUnits().width()
    gap_left = 14.0 + leg_w + FURNITURE_GAP
    gap_right = 400.0 - scale_w - FURNITURE_GAP
    avail = max(gap_right - gap_left, 80.0)
    note_w = min(NOTE_W, avail)
    note_x = gap_left + 0.5 * (avail - note_w)
    note_y = 8 + FRAME_H - NOTE_BOTTOM - NOTE_H
    note_panel = _white_box(layout, note_x, note_y, note_w, NOTE_H)
    note = QgsLayoutItemLabel(layout)
    note.setMode(QgsLayoutItemLabel.ModeFont)
    note.setText(caption)
    note.setFont(QFont("Arial", NOTE_FONT_PT, QFont.Bold))
    note.setFontColor(QColor(0, 0, 0))
    note.setHAlign(Qt.AlignHCenter)
    note.setVAlign(Qt.AlignVCenter)
    note.setMargin(3.0)
    note.setZValue(21)
    _place(layout, note, note_x, note_y, note_w, NOTE_H)

    credit = _halo_label(
        layout,
        CREDIT,
        400.0 - scale_w,
        283.0 - scale.sizeWithUnits().height() - 9.0,
        scale_w,
        8.0,
        pt=8,
    )

    def _grow(box, pad_mm):
        x, y, bw, bh = box
        return (x - pad_mm, y - pad_mm, bw + 2 * pad_mm, bh + 2 * pad_mm)

    title_box = _item_map_box(title_panel)
    tx, ty, tw, th = title_box
    title_box = (tx, ty, tw, th + 4.0)
    boxes = [
        title_box,
        _item_map_box(north),
        _item_map_box(loc_map),
        _grow(_item_map_box(legend), BOTTOM_CLEAR),
        _grow(_item_map_box(note_panel), BOTTOM_CLEAR),
        _grow(_item_map_box(scale), BOTTOM_CLEAR),
        _grow(_item_map_box(credit), BOTTOM_CLEAR),
    ]
    extent = _framed_extent(
        ext, FRAME_W, FRAME_H, boxes=boxes, city_poly=city_poly, hex_xy=None, slug=slug
    )
    map_item.setExtent(extent)
    map_item.refresh()
    scale.refresh()

    project.layoutManager().addLayout(layout)

    MAPS.mkdir(parents=True, exist_ok=True)
    png = MAPS / f"{slug}_study_area.png"
    review = MAPS / f"{slug}_study_area_review.png"
    tmp = png.with_name(f"{png.stem}_{os.getpid()}_tmp.png")
    for path in (png, png.with_suffix(".pdf"), tmp, review):
        if path.exists():
            path.unlink()
    exporter = QgsLayoutExporter(layout)
    img = QgsLayoutExporter.ImageExportSettings()
    img.dpi = 200
    img.generateWorldFile = False
    img.exportMetadata = False
    img.cropToContents = False
    status = exporter.exportToImage(str(tmp), img)
    if status != QgsLayoutExporter.Success:
        raise RuntimeError(f"layout export failed for {png.name}: {status}")
    tmp.replace(png)
    shutil.copy2(png, review)
    return png


def main(slug: str = "lagos") -> Path:
    out = ROOT / "qgis" / f"{slug}_so_far.qgz"
    health_title = HEALTH_TITLE.get(slug, "6 GRID3 health v3")
    sparse = slug in {"abuja"}
    school_size = "3.4" if sparse else "1.8"
    health_size = "4.2" if sparse else "2.4"

    QgsApplication.setPrefixPath(os.environ["QGIS_PREFIX_PATH"], True)
    app = QgsApplication([], False)
    app.initQgis()

    out.parent.mkdir(parents=True, exist_ok=True)
    project = QgsProject.instance()
    project.clear()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    project.setPresetHomePath(str(ROOT))
    project.setFileName(str(out))

    osm = QgsRasterLayer(
        "type=xyz&url=https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png&zmax=19&zmin=0&crs=EPSG3857",
        "OpenStreetMap",
        "wms",
    )

    outline = QgsFillSymbol.createSimple(
        {
            "color": "0,0,0,0",
            "outline_color": "28,25,22,255",
            "outline_width": "0.9",
            "outline_width_unit": "MM",
        }
    )

    wards = None
    places = None
    plate_mask = None
    ward_gpkg = PROCESSED / f"{slug}_wards.gpkg"
    metro_gpkg = PROCESSED / f"{slug}_metro_lgas.gpkg"
    if ward_gpkg.exists():
        wards = _vector(ward_gpkg, f"{slug}_wards", "2 Wards (GRID3 operational)")
        if slug == "abuja":
            wards.setSubsetString(f'"locator" IN ({_quoted_in(ABUJA_PLATE_WARDS)})')
            plate_mask = _union_geoms(wards)
            if plate_mask is None or plate_mask.isEmpty():
                raise RuntimeError("Abuja plate wards did not dissolve")
            wards = _copy_intersecting(wards, plate_mask, "2 Wards (GRID3 operational)")
        elif slug == "lagos" and metro_gpkg.exists():
            plate_lgas = _vector(metro_gpkg, f"{slug}_metro_lgas", "_plate_lgas")
            plate_lgas.setSubsetString(f'"shapeName" IN ({_quoted_in(LAGOS_PLATE_LGAS)})')
            plate_mask = _union_geoms(plate_lgas)
            if plate_mask is None or plate_mask.isEmpty():
                raise RuntimeError("Lagos plate LGAs did not dissolve")
            wards = _copy_intersecting(wards, plate_mask, "2 Wards (GRID3 operational)")
        wards.setLabelsEnabled(False)
        wards.renderer().setSymbol(
            QgsFillSymbol.createSimple(
                {
                    "color": "0,0,0,0",
                    "outline_color": "90,84,78,165",
                    "outline_width": "0.22",
                    "outline_width_unit": "MM",
                    "outline_style": "solid",
                }
            )
        )

    if plate_mask is not None:
        boundary = _memory_polygon(
            plate_mask,
            wards.crs().authid() if wards is not None else "EPSG:4326",
            "1 Study boundary",
        )
    else:
        boundary = _vector(
            PROCESSED / f"{slug}_study_boundary.gpkg",
            f"{slug}_study_boundary",
            "1 Study boundary",
        )
    boundary.renderer().setSymbol(outline)

    place_gpkg = PROCESSED / f"{slug}_places.gpkg"
    if place_gpkg.exists():
        places = _vector(place_gpkg, f"{slug}_places", "2b Named places (OSM)")
        if plate_mask is not None:
            places = _copy_intersecting(places, plate_mask, "2b Named places (OSM)")
        places.renderer().setSymbol(
            _marker("circle", "0,0,0,0", "0.1", outline="0,0,0,0")
        )
        _place_labels(places, slug)

    state_lgas = None
    state_gpkg = PROCESSED / f"{slug}_state_lgas.gpkg"
    if state_gpkg.exists():
        state_lgas = _vector(state_gpkg, f"{slug}_state_lgas", "2c State LGAs (COD-AB)")
        _name_labels(state_lgas, LGA_QML, "shapeName")
        if metro_gpkg.exists():
            probe_lgas = _vector(metro_gpkg, f"{slug}_metro_lgas", "_metro_names")
            metro_names = {f["shapeName"] for f in probe_lgas.getFeatures() if f["shapeName"]}
            del probe_lgas
            if metro_names:
                quoted = ",".join("'" + str(n).replace("'", "''") + "'" for n in sorted(metro_names))
                state_lgas.setSubsetString(f'"shapeName" NOT IN ({quoted})')

    hex_pop = _vector(
        PROCESSED / f"{slug}_hexes.gpkg",
        f"{slug}_hexes",
        "3 Hex population (NGA v3.0, pop > 5)",
    )
    hex_pop.setSubsetString('"pop" > 5')
    if plate_mask is not None:
        hex_pop = _copy_intersecting(hex_pop, plate_mask, hex_pop.name())
    _rounded_jenks(hex_pop, "pop", 6)

    hex_pt = _vector(
        PROCESSED / f"{slug}_hexes.gpkg",
        f"{slug}_hexes",
        "4 Walk PT_k (OSM foot n=5)",
    )
    hex_pt.setSubsetString('"pop" > 5')
    if plate_mask is not None:
        hex_pt = _copy_intersecting(hex_pt, plate_mask, hex_pt.name())
        print(f"  {slug} plate clip: {hex_pt.featureCount()} hexes")
    _graduated(hex_pt, "PT_k", _pt_breaks())

    extra_pt = []
    probe = _vector(PROCESSED / f"{slug}_hexes.gpkg", f"{slug}_hexes", "_probe")
    fields = {f.name() for f in probe.fields()}
    del probe
    if "PT_eucl" in fields:
        eucl = _hex_field(slug, "PT_eucl", "4e Walk Euclidean n=5 (sensitivity)")
        if plate_mask is not None:
            eucl = _copy_intersecting(eucl, plate_mask, eucl.name())
            _graduated(eucl, "PT_eucl", _pt_breaks())
        extra_pt.append(eucl)
    # Walk PT_k is the headline; car grades are out of the project by request.
    car_layers = []

    schools = _vector(
        PROCESSED / f"{slug}_school_points.gpkg",
        f"{slug}_school_points",
        "5 GRID3 schools",
    )
    schools.renderer().setSymbol(_marker("circle", "25,80,120,230", school_size))

    health = _vector(
        PROCESSED / f"{slug}_health_points.gpkg",
        f"{slug}_health_points",
        health_title,
    )
    health.renderer().setSymbol(_marker("square", "178,34,34,240", health_size))

    walk = None
    walk_gpkg = PROCESSED / f"{slug}_walk_edges.gpkg"
    if walk_gpkg.exists():
        walk = _vector(walk_gpkg, f"{slug}_walk_edges", "Walking streets")
        walk.renderer().setSymbol(_line("45,70,92,220", "0.26"))
        if plate_mask is not None:
            walk = _copy_intersecting(walk, plate_mask, "Walking streets")
            walk.renderer().setSymbol(_line("45,70,92,220", "0.26"))

    inv_clinic_mm = "2.2" if sparse else "1.6"
    inv_school_mm = "1.8" if sparse else "1.35"
    facilities = _inventory_facilities(
        health,
        schools,
        plate_mask,
        clinic_mm=inv_clinic_mm,
        school_mm=inv_school_mm,
    )

    layers = [osm]
    if state_lgas is not None:
        layers.append(state_lgas)
    layers += [hex_pop, hex_pt, *extra_pt, *car_layers]
    if wards is not None:
        layers.append(wards)
    if places is not None:
        layers.append(places)
    layers += [boundary, schools, health]
    if walk is not None:
        layers.append(walk)
    layers.append(facilities)
    for layer in layers:
        if layer.isValid():
            project.addMapLayer(layer, True)

    root = project.layerTreeRoot()
    pop_node = root.findLayer(hex_pop.id())
    pt_node = root.findLayer(hex_pt.id())
    if sparse:
        if pt_node:
            pt_node.setItemVisibilityChecked(False)
        if pop_node:
            pop_node.setItemVisibilityChecked(True)
    elif pop_node:
        pop_node.setItemVisibilityChecked(False)
    for layer in extra_pt:
        node = root.findLayer(layer.id())
        if node:
            node.setItemVisibilityChecked(False)
    if pt_node and extra_pt:
        pt_node.setItemVisibilityChecked(True)
    for i, layer in enumerate(car_layers):
        node = root.findLayer(layer.id())
        if node:
            node.setItemVisibilityChecked(False)
    for extra in (walk, facilities):
        if extra is None:
            continue
        node = root.findLayer(extra.id())
        if node:
            node.setItemVisibilityChecked(False)

    hex_pop.updateExtents()
    hex_pt.updateExtents()
    extent = hex_pop.extent()
    pad = 0.003 if sparse else 0.004
    canvas = QgsRectangle(
        extent.xMinimum() - pad,
        extent.yMinimum() - pad,
        extent.xMaximum() + pad,
        extent.yMaximum() + pad,
    )
    project.viewSettings().setDefaultViewExtent(
        QgsReferencedRectangle(canvas, QgsCoordinateReferenceSystem("EPSG:4326"))
    )

    city = CITY_DISPLAY[slug]
    layout_overlays = [boundary]
    if places is not None:
        layout_overlays.append(places)
    if wards is not None:
        layout_overlays.append(wards)
    _kigali_layout(
        project,
        slug,
        layout_name="Walk PT_k",
        choropleth=hex_pt,
        overlays=layout_overlays,
        osm=osm,
        extent_wgs=hex_pop.extent(),
        title=f"WALKING ACCESS IN {city}",
        subtitle="To clinics and schools",
        caption=(
            "This map shows how long it takes to walk to clinics and schools. "
            "Each cell is a 200-metre neighbourhood. "
            "Green is a 15-minute walk or less."
        ),
        legend_title="Minutes on foot",
        export_stem="PT_k_plate",
    )
    _kigali_layout(
        project,
        slug,
        layout_name="Population",
        choropleth=hex_pop,
        overlays=layout_overlays,
        osm=osm,
        extent_wgs=hex_pop.extent(),
        title=f"POPULATION IN {city}",
        subtitle="People in each neighbourhood",
        caption=(
            "This map shows how many people live in each neighbourhood. "
            "Each cell is 200 metres across. "
            "Darker red means more residents."
        ),
        legend_title="People per hexagon",
        export_stem="pop_plate",
    )
    if walk is not None:
        stock_overlays = [boundary]
        if wards is not None:
            stock_overlays.append(wards)
        _inventory_layout(
            project,
            slug,
            roads=walk,
            facilities=facilities,
            overlays=stock_overlays,
            osm=osm,
            extent_wgs=hex_pop.extent(),
            title=f"CLINICS AND SCHOOLS IN {city}",
            subtitle="On the walking streets",
            caption=(
                "Red squares are clinics, blue circles schools. "
                "The lines are the streets the walk is timed on. "
                "Where two buildings share a corner, the marks are nudged apart."
            ),
        )
    else:
        print(f"  skip inventory plate: {slug}_walk_edges.gpkg missing", flush=True)

    ok = project.write(str(out))
    app.exitQgis()
    if not ok:
        raise RuntimeError("QGIS project.write failed")
    return out


STUDY_CAPTIONS = {
    "ibadan": (
        "Ibadan here is the five core local government areas. "
        "Red squares are GRID3 clinics and blue circles schools. "
        "Brown lines are the streets the walk is timed on."
    ),
    "lagos": (
        "Lagos here is seven local government areas, the inner mainland and the islands. "
        "Red squares are GRID3 clinics and blue circles schools. "
        "Brown lines are the streets the walk is timed on."
    ),
    "kano": (
        "Kano here is eight metro local government areas, including Ungogo and Kumbotso. "
        "Red squares are GRID3 clinics and blue circles schools. "
        "Brown lines are the streets the walk is timed on."
    ),
    "abuja": (
        "Abuja here is seven Municipal Area Council wards plus Kubwa, Dutse and Usuma in Bwari. "
        "Red squares are GRID3 clinics and blue circles schools. "
        "Brown lines are the streets the walk is timed on."
    ),
    "port_harcourt": (
        "Port Harcourt here is the township and Obio/Akpor together. "
        "Red squares are GRID3 clinics and blue circles schools. "
        "Brown lines are the streets the walk is timed on."
    ),
}


def build_study_area(slug: str = "ibadan") -> Path:
    """One study-area plate. Does not rebuild the walking or population plates."""
    QgsApplication.setPrefixPath(os.environ["QGIS_PREFIX_PATH"], True)
    app = QgsApplication([], False)
    app.initQgis()

    out = ROOT / "qgis" / f"{slug}_so_far.qgz"
    project = QgsProject.instance()
    project.clear()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    project.setPresetHomePath(str(ROOT))
    project.setFileName(str(out))

    outline = QgsFillSymbol.createSimple(
        {
            "color": "0,0,0,0",
            "outline_color": "28,25,22,255",
            "outline_width": "0.9",
            "outline_width_unit": "MM",
        }
    )

    plate_mask = None
    wards = None
    ward_gpkg = PROCESSED / f"{slug}_wards.gpkg"
    metro_gpkg = PROCESSED / f"{slug}_metro_lgas.gpkg"
    if ward_gpkg.exists():
        wards = _vector(ward_gpkg, f"{slug}_wards", "2 Wards (GRID3 operational)")
        if slug == "abuja":
            wards.setSubsetString(f'"locator" IN ({_quoted_in(ABUJA_PLATE_WARDS)})')
            plate_mask = _union_geoms(wards)
            wards = _copy_intersecting(wards, plate_mask, "2 Wards (GRID3 operational)")
        elif slug == "lagos" and metro_gpkg.exists():
            plate_lgas = _vector(metro_gpkg, f"{slug}_metro_lgas", "_plate_lgas")
            plate_lgas.setSubsetString(f'"shapeName" IN ({_quoted_in(LAGOS_PLATE_LGAS)})')
            plate_mask = _union_geoms(plate_lgas)
            wards = _copy_intersecting(wards, plate_mask, "2 Wards (GRID3 operational)")
        wards.renderer().setSymbol(
            QgsFillSymbol.createSimple(
                {
                    "color": "0,0,0,0",
                    "outline_color": "90,84,78,175",
                    "outline_width": "0.22",
                    "outline_width_unit": "MM",
                    "outline_style": "solid",
                }
            )
        )
        _apply_pal_labels(
            wards,
            "locator",
            size=10,
            pinned=PINNED_LABELS.get(slug, ()),
            max_labels=32,
            min_mm=2.2,
        )

    if plate_mask is not None:
        boundary = _memory_polygon(
            plate_mask,
            wards.crs().authid() if wards is not None else "EPSG:4326",
            "1 Study boundary",
        )
        aoi_wgs = QgsGeometry(plate_mask)
    else:
        boundary = _vector(
            PROCESSED / f"{slug}_study_boundary.gpkg",
            f"{slug}_study_boundary",
            "1 Study boundary",
        )
        aoi_wgs = _union_geoms(boundary)
        if aoi_wgs is None or aoi_wgs.isEmpty():
            raise RuntimeError(f"{slug} study boundary did not dissolve")
    boundary.renderer().setSymbol(outline)

    walk = _vector(PROCESSED / f"{slug}_walk_edges.gpkg", f"{slug}_walk_edges", "Walking streets")
    if plate_mask is not None:
        walk = _copy_intersecting(walk, plate_mask, "Walking streets")
    _faint_roads(walk)

    sparse = slug in {"abuja"}
    health = _vector(
        PROCESSED / f"{slug}_health_points.gpkg",
        f"{slug}_health_points",
        HEALTH_TITLE.get(slug, "6 GRID3 health v3"),
    )
    schools = _vector(
        PROCESSED / f"{slug}_school_points.gpkg",
        f"{slug}_school_points",
        "5 GRID3 schools",
    )
    facilities = _inventory_facilities(
        health,
        schools,
        plate_mask,
        clinic_mm="2.0" if sparse else "1.75",
        school_mm="1.7" if sparse else "1.45",
    )

    grey = _grey_basemap()
    project.addMapLayer(grey, False)

    nga, aoi_layer, locator_pin, loc_extent = _nigeria_locator_layers(
        aoi_wgs, CITY_DISPLAY[slug].title()
    )

    for layer in (wards, boundary, walk, facilities, nga, aoi_layer, locator_pin, grey):
        if layer is not None and layer.isValid():
            project.addMapLayer(layer, True)

    overlays = [boundary]
    if wards is not None:
        overlays.append(wards)

    png = _study_area_layout(
        project,
        slug,
        roads=walk,
        facilities=facilities,
        overlays=overlays,
        grey=grey,
        veil=None,
        nga=nga,
        aoi_layer=aoi_layer,
        locator_pin=locator_pin,
        locator_extent_wgs=loc_extent,
        extent_wgs=boundary.extent(),
        title="STUDY AREA",
        subtitle=CITY_DISPLAY[slug],
        caption=STUDY_CAPTIONS[slug],
    )
    print(f"  study area plate → {png.name}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "lagos"
    mode = sys.argv[2] if len(sys.argv) > 2 else "all"
    if mode == "study_area":
        print(build_study_area(slug))
    else:
        print(main(slug))
