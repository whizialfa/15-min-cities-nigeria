"""Lagos study-area plate cloned from the Kigali QGIS layout.

Furniture, type, north arrow, legend swatches, and scale bar follow
Infant_Population_Variability_in_Kigali.jpg. Geography is Lagos metro LGAs.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle
from shapely.geometry import box
from shapely.ops import unary_union

from .cities import CITIES
from .paths import MAPS
from .plates import _adm2, _context, _expand_bbox, _select_named

ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

for _p in (ARIAL, ARIAL_BOLD):
    font_manager.fontManager.addfont(_p)

# Kigali plate colours (sampled from the reference JPG)
PAGE = "#ffffff"
LAND = "#f3efe6"
WATER = "#d5e4d8"
INK = "#000000"
EDGE = "#1a1a1a"
ADJACENT_FILL = "#ffffff"
STUDY_FILL = "#f6c6c6"  # Kigali "Low" pink — study LGAs as one class
LEGEND_PINK = "#f6c6c6"
LEGEND_WHITE = "#ffffff"

# Type sizes taken from the 1024×724 Kigali export (print-like points)
TITLE_PT = 12.0
TITLE_SUB_PT = 12.0
LABEL_PT = 8.0
LEGEND_TITLE_PT = 10.0
LEGEND_ITEM_PT = 9.0
SCALE_PT = 9.0


def _register_arial():
    plt.rcParams["font.family"] = "Arial"
    plt.rcParams["font.size"] = LABEL_PT
    plt.rcParams["axes.unicode_minus"] = False


def _north_arrow_kigali(ax):
    """4-point star + ring, matching the Kigali compass (no letter N)."""
    na = ax.inset_axes([0.88, 0.80, 0.10, 0.16])
    na.set_xlim(-1.4, 1.4)
    na.set_ylim(-1.35, 1.5)
    na.set_aspect("equal")
    na.axis("off")
    verts = []
    for i in range(8):
        ang = np.deg2rad(90 - i * 45)
        r = 1.18 if i % 2 == 0 else 0.36
        verts.append((r * np.cos(ang), r * np.sin(ang)))
    na.add_patch(Polygon(verts, closed=True, facecolor=INK, edgecolor=INK, lw=0.35, zorder=3))
    na.add_patch(Circle((0, 0), 0.52, fill=False, lw=1.85, ec=INK, zorder=4))
    na.add_patch(Circle((0, 0), 0.07, facecolor=INK, edgecolor=INK, zorder=5))


def _scalebar_kigali(ax, x0, y0, metres=10_000):
    """0 — 5 — 10 km hairline bar, Kigali lower-right."""
    half = metres / 2
    ax.plot([x0, x0 + metres], [y0, y0], color=INK, lw=1.4, solid_capstyle="butt", zorder=9, clip_on=False)
    for x in (x0, x0 + half, x0 + metres):
        ax.plot([x, x], [y0, y0 - metres * 0.025], color=INK, lw=1.3, zorder=9, clip_on=False)
    dy = metres * 0.055
    for x, lab in ((x0, "0"), (x0 + half, "5"), (x0 + metres, "10 km")):
        ax.text(x, y0 - dy, lab, ha="center", va="top", fontsize=SCALE_PT, fontname="Arial", color=INK, zorder=9, clip_on=False)


def _legend_kigali(ax):
    """Swatch size, title weight, and item size cloned from the Kigali legend box."""
    lg = ax.inset_axes([0.014, 0.022, 0.178, 0.168])
    lg.set_xlim(0, 1)
    lg.set_ylim(0, 1)
    lg.axis("off")
    lg.add_patch(Rectangle((0.0, 0.0), 1.0, 1.0, fill=True, facecolor=PAGE, edgecolor=INK, lw=1.15, zorder=0))
    lg.text(
        0.08,
        0.84,
        "Study Area",
        ha="left",
        va="center",
        fontsize=LEGEND_TITLE_PT,
        fontname="Arial",
        fontweight="bold",
        color=INK,
    )
    sw = 0.125
    rows = [
        (0.58, ADJACENT_FILL, "Adjacent LGA"),
        (0.32, STUDY_FILL, "Metropolitan LGA"),
    ]
    for y, fill, lab in rows:
        lg.add_patch(Rectangle((0.08, y - sw / 2), sw, sw, facecolor=fill, edgecolor=INK, lw=0.85, zorder=1))
        lg.text(0.24, y, lab, ha="left", va="center", fontsize=LEGEND_ITEM_PT, fontname="Arial", color=INK)


def lagos_study_area(outfile: Path | None = None) -> Path:
    _register_arial()
    city = CITIES["lagos"]
    adm = _adm2()
    core = _select_named(adm, city.metro_lgas, city.bbox)
    ctx = _context(adm, core, city.bbox)
    win = box(*_expand_bbox(city.bbox, 0.22))
    core = core.clip(win)
    if len(ctx):
        ctx = ctx.clip(box(*_expand_bbox(city.bbox, 0.55)))

    utm = core.estimate_utm_crs()
    core_u = core.to_crs(utm)
    ctx_u = ctx.to_crs(utm) if len(ctx) else ctx
    minx, miny, maxx, maxy = core_u.total_bounds
    pad_x = 0.06 * (maxx - minx)
    pad_y = 0.10 * (maxy - miny)

    # Kigali JPG is 1024×724 ≈ 1.414
    fig = plt.figure(figsize=(14.14, 10.0), facecolor=PAGE, dpi=150)
    ax = fig.add_axes([0.035, 0.04, 0.93, 0.93])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    frame = box(xmin, ymin, xmax, ymax)
    land = unary_union(list(core_u.geometry) + (list(ctx_u.geometry) if len(ctx_u) else []))
    water = frame.difference(land)
    ax.set_facecolor(LAND)
    if not water.is_empty:
        gpd.GeoSeries([water], crs=core_u.crs).plot(ax=ax, color=WATER, edgecolor="none", zorder=0)

    if len(ctx_u):
        ctx_u.plot(ax=ax, facecolor=ADJACENT_FILL, edgecolor=EDGE, linewidth=0.45, zorder=2)
    core_u.plot(ax=ax, facecolor=STUDY_FILL, edgecolor=EDGE, linewidth=0.7, zorder=3)

    for _, row in core_u.iterrows():
        p = row.geometry.representative_point()
        name = str(row["shapeName"]).replace("/", "/\n")
        ax.annotate(
            name,
            (p.x, p.y),
            ha="center",
            va="center",
            fontsize=LABEL_PT,
            fontname="Arial",
            color=INK,
            zorder=6,
        )

    # Neatline — Kigali: single black rectangle, ~1.6 pt
    ax.add_patch(
        Rectangle(
            (xmin, ymin),
            xmax - xmin,
            ymax - ymin,
            fill=False,
            edgecolor=INK,
            linewidth=1.6,
            zorder=10,
            clip_on=False,
        )
    )

    # Title box shares the top-left of the neatline
    tw, th = 0.42, 0.095
    t = ax.inset_axes([0.0, 1.0 - th, tw, th])
    t.set_xlim(0, 1)
    t.set_ylim(0, 1)
    t.axis("off")
    t.add_patch(FancyBboxPatch((0.0, 0.0), 1.0, 1.0, boxstyle="square,pad=0", facecolor=PAGE, edgecolor=INK, lw=1.6))
    t.text(0.5, 0.64, "STUDY AREA MAP OF LAGOS", ha="center", va="center", fontsize=TITLE_PT, fontname="Arial", fontweight="bold", color=INK)
    t.text(0.5, 0.28, "(METROPOLITAN LGA BOUNDARIES)", ha="center", va="center", fontsize=TITLE_SUB_PT, fontname="Arial", fontweight="bold", color=INK)

    _north_arrow_kigali(ax)
    _legend_kigali(ax)

    # Scale in the lower-right interior, 10 km
    _scalebar_kigali(ax, xmax - 0.22 * (xmax - xmin), ymin + 0.06 * (ymax - ymin), metres=10_000)

    outfile = Path(outfile) if outfile else MAPS / "lagos_study_area.png"
    fig.savefig(outfile, dpi=200, facecolor=PAGE)
    fig.savefig(outfile.with_suffix(".pdf"), facecolor=PAGE)
    plt.close(fig)
    return outfile


if __name__ == "__main__":
    print(lagos_study_area())
