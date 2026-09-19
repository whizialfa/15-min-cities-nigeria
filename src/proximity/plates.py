"""Publication plates: labelled metro LGAs, context, locator, in-frame furniture.

The hex 'distance to centroid' rings are a diagnostic, not a map. These plates
are the public figure: structure of the study area, Kigali-like furniture,
different colour and type.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle
from matplotlib_scalebar.scalebar import ScaleBar
from shapely.geometry import box
from shapely.ops import unary_union

from .cities import CITIES, City
from .download import DATASETS
from .paths import DATA_RAW, MAPS

PAPER = "#fbf8f2"
MAP_FACE = "#efeae1"
INK = "#1a1f24"
MUTED = "#5c5852"
LINE = "#3a3a3a"
CONTEXT_FILL = "#f4f0e8"
CONTEXT_EDGE = "#d2cbbf"
WATER = "#c5d4de"
COASTAL = {"lagos", "port_harcourt"}
HALO = pe.withStroke(linewidth=2.8, foreground="white")

# Restrained earth/ink set — not a rainbow, not the Kigali reds.
LGA_PALETTE = [
    "#1e3f3a",
    "#3d6b63",
    "#6d9086",
    "#a3b5a8",
    "#cbbf9a",
    "#a8845c",
    "#7a5a40",
    "#4d4036",
    "#2f4554",
    "#5b7380",
    "#8a9aa3",
    "#b7c0c4",
    "#6e7f68",
    "#8f6e56",
    "#4a5e50",
    "#d6c7a8",
]


def _font():
    for name in ("Avenir Next", "Avenir", "Gill Sans", "Helvetica Neue", "DejaVu Sans"):
        try:
            from matplotlib import font_manager

            font_manager.findfont(name, fallback_to_default=False)
            return name
        except Exception:
            continue
    return "DejaVu Sans"


FONT = _font()


def _adm2() -> gpd.GeoDataFrame:
    path = DATA_RAW / DATASETS["geoboundaries_adm2"]["filename"]
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326)


def _expand_bbox(bbox, frac=0.35):
    w, s, e, n = bbox
    dx, dy = (e - w) * frac, (n - s) * frac
    return (w - dx, s - dy, e + dx, n + dy)


def _select_named(adm: gpd.GeoDataFrame, names: tuple[str, ...], bbox) -> gpd.GeoDataFrame:
    w, s, e, n = _expand_bbox(bbox, 0.15)
    hit = adm[adm["shapeName"].isin(names)]
    return hit.cx[w:e, s:n].copy()


def _context(adm: gpd.GeoDataFrame, core: gpd.GeoDataFrame, bbox) -> gpd.GeoDataFrame:
    w, s, e, n = _expand_bbox(bbox, 0.55)
    frame = box(w, s, e, n)
    ctx = adm[adm.intersects(frame)].copy()
    ctx = ctx.loc[~ctx.index.isin(core.index)]
    return ctx


def _figsize(bounds, landscape_max=14.2, portrait_max=12.8):
    minx, miny, maxx, maxy = bounds
    aspect = (maxx - minx) / max(maxy - miny, 1e-6)
    if aspect >= 1.15:
        w = landscape_max
        h = w / aspect + 1.35
        h = min(max(h, 8.6), 11.2)
        return (w, h), aspect
    if aspect <= 0.82:
        h = portrait_max
        w = h * aspect + 1.6
        w = min(max(w, 8.8), 11.4)
        return (w, h), aspect
    return (11.4, 11.6), aspect


def _compass(ax):
    ins = ax.inset_axes([0.88, 0.82, 0.10, 0.14])
    ins.set_xlim(-1.2, 1.2)
    ins.set_ylim(-1.2, 1.35)
    ins.set_aspect("equal")
    ins.axis("off")
    ins.add_patch(Circle((0, 0), 1.05, fill=False, lw=0.7, ec=INK, zorder=2))
    ins.add_patch(Circle((0, 0), 0.18, facecolor=INK, edgecolor=INK, zorder=4))
    ins.add_patch(Polygon([(0, 1.0), (0.22, -0.12), (0, 0.15), (-0.22, -0.12)], facecolor=INK, zorder=3))
    ins.add_patch(Polygon([(0, -1.0), (0.18, 0.08), (0, -0.1), (-0.18, 0.08)], facecolor="#d8d2c8", edgecolor=INK, lw=0.4, zorder=3))
    ins.text(0, 1.18, "N", ha="center", va="bottom", fontsize=8, fontweight="bold", fontname=FONT, color=INK)


def _locator(fig, city: City, adm: gpd.GeoDataFrame, metro: gpd.GeoDataFrame, rect):
    ax = fig.add_axes(rect, facecolor="white")
    ax.set_aspect("equal")
    country = adm[["geometry"]].copy()
    country["k"] = 1
    country.dissolve(by="k").boundary.plot(ax=ax, color=INK, lw=0.45, zorder=1)
    metro.to_crs(4326).plot(ax=ax, color="#3d6b63", edgecolor="#1e3f3a", linewidth=0.2, zorder=2)
    ax.plot([np.mean(city.bbox[0::2])], [np.mean(city.bbox[1::2])], marker="o", ms=3.2, color="#a8442a", zorder=3)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color(INK)
        sp.set_linewidth(0.6)
    ax.set_title("Nigeria", fontsize=6.5, fontname=FONT, color=MUTED, pad=2)


def metro_plate(city: City, adm: gpd.GeoDataFrame | None = None, outfile: Path | None = None) -> Path:
    adm = adm if adm is not None else _adm2()
    core = _select_named(adm, city.metro_lgas, city.bbox)
    if core.empty:
        raise RuntimeError(f"No LGAs for {city.name}")
    ctx = _context(adm, core, city.bbox)
    win = box(*_expand_bbox(city.bbox, 0.08))
    if city.slug != "abuja":
        core = core.clip(win)
    if len(ctx):
        ctx = ctx.clip(box(*_expand_bbox(city.bbox, 0.45)))
    utm = core.estimate_utm_crs()
    core_u = core.to_crs(utm)
    ctx_u = ctx.to_crs(utm) if len(ctx) else ctx
    bounds = core_u.total_bounds
    (fw, fh), _ = _figsize(bounds)

    fig = plt.figure(figsize=(fw, fh + 0.85), facecolor=PAPER, dpi=160)
    ax = fig.add_axes([0.045, 0.155, 0.91, 0.77])
    ax.set_aspect("equal")
    ax.axis("off")

    pad_x = 0.04 * (bounds[2] - bounds[0])
    pad_y = 0.04 * (bounds[3] - bounds[1])
    ax.set_xlim(bounds[0] - pad_x, bounds[2] + pad_x)
    ax.set_ylim(bounds[1] - pad_y, bounds[3] + pad_y)
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    frame = box(xmin, ymin, xmax, ymax)
    land_parts = list(core_u.geometry) + (list(ctx_u.geometry) if len(ctx_u) else [])
    land = unary_union(land_parts)
    if city.slug in COASTAL:
        ax.set_facecolor(WATER)
        water = frame.difference(land)
        if not water.is_empty:
            gpd.GeoSeries([water], crs=core_u.crs).plot(ax=ax, color=WATER, edgecolor="none", zorder=0)
        gpd.GeoSeries([land], crs=core_u.crs).plot(ax=ax, color=CONTEXT_FILL, edgecolor="none", zorder=1)
    else:
        ax.set_facecolor(MAP_FACE)

    if len(ctx_u):
        ctx_u.plot(ax=ax, facecolor=CONTEXT_FILL, edgecolor=CONTEXT_EDGE, linewidth=0.35, zorder=2)

    names = list(core_u["shapeName"])
    color_map = {n: LGA_PALETTE[i % len(LGA_PALETTE)] for i, n in enumerate(sorted(names))}
    core_u = core_u.copy()
    core_u["_c"] = core_u["shapeName"].map(color_map)
    core_u.plot(ax=ax, color=core_u["_c"], edgecolor="white", linewidth=0.85, zorder=3)

    # Labels — representative point, halo, skip tiny slivers
    areas = core_u.geometry.area
    cutoff = float(areas.quantile(0.12))
    for _, row in core_u.iterrows():
        if row.geometry.area < cutoff and len(core_u) > 6 and "Island" not in row["shapeName"]:
            continue
        p = row.geometry.representative_point()
        label = row["shapeName"].replace("/", "/\n")
        ax.annotate(
            label,
            (p.x, p.y),
            ha="center",
            va="center",
            fontsize=6.4 if len(core_u) > 8 else 7.4,
            fontname=FONT,
            color="white" if _is_dark(color_map[row["shapeName"]]) else INK,
            fontweight="medium",
            zorder=5,
            path_effects=[HALO] if not _is_dark(color_map[row["shapeName"]]) else [pe.withStroke(linewidth=1.4, foreground="#1a1f24")],
        )

    # Double neatline
    for extra, lw in ((0.0, 1.35), (0.012 * (xmax - xmin), 0.4)):
        ax.add_patch(
            Rectangle(
                (xmin - extra, ymin - extra),
                (xmax - xmin) + 2 * extra,
                (ymax - ymin) + 2 * extra,
                fill=False,
                edgecolor=INK,
                linewidth=lw,
                zorder=8,
            )
        )

    ax.add_artist(
        ScaleBar(
            1,
            location="lower left",
            box_alpha=0.92,
            box_color=PAPER,
            color=INK,
            font_properties={"size": 7, "family": FONT},
            border_pad=0.5,
            pad=0.3,
        )
    )
    _compass(ax)

    # Title plate — sits on the neatline, Kigali logic, not Kigali reds
    t = ax.inset_axes([0.015, 0.88, 0.50, 0.10])
    t.set_xlim(0, 1)
    t.set_ylim(0, 1)
    t.axis("off")
    t.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="square,pad=0", facecolor=PAPER, edgecolor=INK, lw=0.9))
    t.text(0.035, 0.62, f"Metropolitan local government areas", fontsize=9.5, fontweight="bold", fontname=FONT, color=INK, va="center")
    t.text(0.035, 0.28, city.name.upper(), fontsize=8, fontname=FONT, color="#3d6b63", va="center")

    # Legend as patches (not a colour bar)
    handles = [
        Line2D([0], [0], marker="s", color="none", markerfacecolor=color_map[n], markeredgecolor="white", markersize=8, label=n)
        for n in sorted(names)
    ]
    ncol = 2 if len(names) > 6 else 1
    leg = fig.legend(
        handles=handles,
        loc="lower left",
        bbox_to_anchor=(0.045, 0.022),
        frameon=True,
        fancybox=False,
        edgecolor=INK,
        facecolor=PAPER,
        fontsize=6.2,
        title="LGA",
        title_fontsize=7,
        borderpad=0.55,
        labelspacing=0.25,
        ncol=ncol,
    )
    leg.get_title().set_fontname(FONT)
    for txt in leg.get_texts():
        txt.set_fontname(FONT)

    _locator(fig, city, adm, core, [0.80, 0.022, 0.155, 0.12])

    fig.text(
        0.045,
        0.006,
        "geoBoundaries gbOpen ADM2  ·  operational metro dissolve, not GHS Urban Centre",
        fontsize=6.2,
        fontname=FONT,
        color=MUTED,
    )

    outfile = Path(outfile) if outfile else MAPS / f"{city.slug}_metro.png"
    fig.savefig(outfile, dpi=240, facecolor=fig.get_facecolor())
    fig.savefig(outfile.with_suffix(".pdf"), facecolor=fig.get_facecolor())
    plt.close(fig)
    return outfile


def _is_dark(hex_color: str) -> bool:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) < 140


def render_all(out_dir: Path | None = None) -> list[Path]:
    adm = _adm2()
    paths = []
    dest = out_dir or MAPS
    for city in CITIES.values():
        paths.append(metro_plate(city, adm=adm, outfile=dest / f"{city.slug}_metro.png"))
        print("wrote", paths[-1])
    return paths


if __name__ == "__main__":
    render_all()
