"""Cross-city chart plates. Same furniture family as the QGIS maps; not maps."""

from __future__ import annotations

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.ticker import MultipleLocator

from .paths import CHARTS, DATA_PROCESSED

ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
for _p in (ARIAL, ARIAL_BOLD):
    font_manager.fontManager.addfont(_p)
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["axes.unicode_minus"] = False

PAGE = "#ffffff"
LAND = "#f3efe6"
INK = "#000000"
MUTED = "#3d3d3d"
GRID = "#d4cdc2"
CREDIT = "©Wisdom Akpabio"
STROKE = 1.15
HALO = [pe.withStroke(linewidth=3.0, foreground=PAGE)]
SMALL_HALO = [pe.withStroke(linewidth=2.2, foreground=PAGE)]

CITY_ORDER = ("Lagos", "Ibadan", "Kano", "Port Harcourt", "Abuja")
CITY_COLOR = {
    "Lagos": "#163d44",
    "Ibadan": "#3d7a74",
    "Kano": "#2f5f7a",
    "Port Harcourt": "#9b3b2f",
    "Abuja": "#8a6a3d",
}
def _fp(bold: bool, size: float) -> FontProperties:
    return FontProperties(fname=ARIAL_BOLD if bold else ARIAL, size=size)


def _text_frac(text: str, size: float, *, fig_w: float = 15.0, pad_in: float = 0.50) -> float:
    """Approximate Arial box width as a figure fraction, with even inset."""
    em = size / 72.0
    return (pad_in + len(text) * em * 0.56) / fig_w


def _open_plate(title: str, subtitle: str, footnote: str, *, colorbar: bool = False, diagram: bool = False):
    """White plate: neatline, snug title, snug footnote, credit, plot panel."""
    fig_w, fig_h = 15.0, 9.2
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=PAGE, dpi=200)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    mx, my = 0.022, 0.036
    fig.patches.append(
        Rectangle(
            (mx, my),
            1 - 2 * mx,
            1 - 2 * my,
            transform=fig.transFigure,
            facecolor="none",
            edgecolor=INK,
            linewidth=STROKE,
            zorder=30,
            clip_on=False,
        )
    )

    title_w = max(_text_frac(title, 15), _text_frac(subtitle, 13))
    title_w = min(max(title_w, 0.26), 0.46)
    title_h = 0.100
    title_x, title_y = mx, 1 - my - title_h
    fig.patches.append(
        Rectangle(
            (title_x, title_y),
            title_w,
            title_h,
            transform=fig.transFigure,
            facecolor=PAGE,
            edgecolor=INK,
            linewidth=STROKE,
            zorder=31,
            clip_on=False,
        )
    )
    fig.text(
        title_x + 0.5 * title_w,
        title_y + 0.64 * title_h,
        title,
        ha="center",
        va="center",
        fontproperties=_fp(True, 15),
        color=INK,
        zorder=32,
    )
    fig.text(
        title_x + 0.5 * title_w,
        title_y + 0.28 * title_h,
        subtitle,
        ha="center",
        va="center",
        fontproperties=_fp(True, 13),
        color=INK,
        zorder=32,
    )

    lines = [ln.strip() for ln in footnote.split("\n") if ln.strip()]
    note_w = max(_text_frac(ln, 12, pad_in=0.55) for ln in lines)
    note_w = min(max(note_w, 0.40), 0.62)
    note_h = 0.100
    note_x = 0.5 - 0.5 * note_w
    note_y = my
    fig.patches.append(
        Rectangle(
            (note_x, note_y),
            note_w,
            note_h,
            transform=fig.transFigure,
            facecolor=PAGE,
            edgecolor=INK,
            linewidth=STROKE,
            zorder=31,
            clip_on=False,
        )
    )
    fig.text(
        note_x + 0.5 * note_w,
        note_y + 0.50 * note_h,
        footnote,
        ha="center",
        va="center",
        fontproperties=_fp(True, 12),
        color=INK,
        zorder=32,
        linespacing=1.35,
    )

    fig.text(
        1 - mx - 0.012,
        my + 0.012,
        CREDIT,
        ha="right",
        va="bottom",
        fontproperties=_fp(False, 8),
        color=INK,
        zorder=32,
        path_effects=SMALL_HALO,
    )

    if diagram:
        ax = fig.add_axes([0.048, 0.198, 0.904, 0.618])
        ax.set_facecolor(PAGE)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_clip_on(False)
        return fig, ax

    ax = fig.add_axes([0.090, 0.248, 0.78 if colorbar else 0.862, 0.568])
    ax.set_facecolor(LAND)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(INK)
    ax.spines["bottom"].set_color(INK)
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)
    ax.tick_params(colors=INK, labelsize=11, width=0.8, length=4)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(_fp(False, 11))
    ax.yaxis.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_locator(MultipleLocator(20))
    return fig, ax


def _axis_labels(ax, xlabel: str, ylabel: str) -> None:
    ax.set_xlabel(xlabel, fontproperties=_fp(False, 12), color=INK, labelpad=8)
    ax.set_ylabel(ylabel, fontproperties=_fp(False, 12), color=INK, labelpad=8)


def _city_label(ax, x, y, name, *, dx=8, dy=8, ha="left", va="center"):
    ax.annotate(
        name,
        (x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        ha=ha,
        va=va,
        fontproperties=_fp(True, 12),
        color=CITY_COLOR[name],
        path_effects=HALO,
        zorder=5,
    )


def _city_frame() -> pd.DataFrame:
    metrics = pd.read_csv(DATA_PROCESSED / "city_metrics.csv")
    rows = []
    for _, row in metrics.iterrows():
        boundary = gpd.read_file(DATA_PROCESSED / f"{row.slug}_study_boundary.gpkg")
        area_km2 = float(boundary.to_crs(boundary.estimate_utm_crs()).area.sum() / 1e6)
        pop = float(row.pop_total)
        rows.append(
            {
                "city": row.city,
                "slug": row.slug,
                "F15": float(row.F15) * 100.0,
                "PT_city": float(row.PT_city),
                "Gini_PT": float(row.Gini_PT),
                "density": pop / area_km2,
                "pop": pop,
                "health_n": int(row.health_n),
                "clinics_per_million": float(row.health_n) / pop * 1e6,
            }
        )
    frame = pd.DataFrame(rows)
    frame["city"] = pd.Categorical(frame["city"], CITY_ORDER, ordered=True)
    return frame.sort_values("city").reset_index(drop=True)


def _n_frame() -> pd.DataFrame:
    raw = pd.read_csv(DATA_PROCESSED / "robustness.csv")
    walk = raw[(raw["mode"] == "walk network") & (raw["kmh"] == 5.0) & (raw["n"].isin([1, 5, 20]))]
    walk = walk.copy()
    walk["F15"] = walk["F15"] * 100.0
    walk["city"] = pd.Categorical(walk["city"], CITY_ORDER, ordered=True)
    return walk.sort_values(["city", "n"])


def f15_vs_density(outfile=None):
    frame = _city_frame()
    fig, ax = _open_plate(
        "ACCESS AND DENSITY",
        "People within a 15-minute walk",
        "Each city is one point. The dashed line is fitted to the other four.\n"
        "Port Harcourt sits off the line because it holds too few clinics, not because it is sparse.\n"
        "Walk graph, five nearby services, 5 km/h.",
    )
    others = frame[frame["city"] != "Port Harcourt"]
    slope, intercept = np.polyfit(others["density"], others["F15"], 1)
    xs = np.linspace(0, 11_000, 200)
    ax.plot(xs, slope * xs + intercept, color="#8fb9a8", lw=1.8, ls=(0, (5, 3.5)), zorder=1)

    for _, row in frame.iterrows():
        ax.scatter(
            row.density,
            row.F15,
            s=118 if row.city == "Port Harcourt" else 88,
            color=CITY_COLOR[row.city],
            zorder=3,
            edgecolors=PAGE,
            linewidths=0.9,
        )
    offsets = {
        "Lagos": (10, 12),
        "Ibadan": (10, -16),
        "Kano": (12, -14),
        "Port Harcourt": (12, 12),
        "Abuja": (12, 8),
    }
    for _, row in frame.iterrows():
        dx, dy = offsets[row.city]
        _city_label(ax, row.density, row.F15, row.city, dx=dx, dy=dy)

    ibadan = frame.loc[frame["city"] == "Ibadan"].iloc[0]
    ph = frame.loc[frame["city"] == "Port Harcourt"].iloc[0]
    ax.annotate(
        f"{ibadan.clinics_per_million:.0f} clinics / million",
        (ibadan.density, ibadan.F15),
        xytext=(10, -32),
        textcoords="offset points",
        fontproperties=_fp(False, 10),
        color=MUTED,
        path_effects=HALO,
    )
    ax.annotate(
        f"{ph.clinics_per_million:.0f} clinics / million",
        (ph.density, ph.F15),
        xytext=(12, -8),
        textcoords="offset points",
        fontproperties=_fp(False, 10),
        color=CITY_COLOR["Port Harcourt"],
        path_effects=HALO,
    )
    ax.set_xlim(0, 11_200)
    ax.set_ylim(0, 100)
    _axis_labels(ax, "People per km²", "People within 15 minutes, percent")
    return _save(fig, outfile or CHARTS / "f15_vs_density.png")


def f15_by_n(outfile=None):
    frame = _n_frame()
    fig, ax = _open_plate(
        "HOW MANY CLINICS COUNT",
        "People within 15 minutes at 1, 5 or 20 nearby",
        "The middle bar is the headline: five nearby clinics or schools.\n"
        "Twenty is Bruno’s rule and does not travel. Port Harcourt falls to 1.1%, Abuja to none.\n"
        "Walk graph, 5 km/h.",
    )
    ns = (1, 5, 20)
    colors = {1: "#8fb9a8", 5: "#163d44", 20: "#9b3b2f"}
    labels = {1: "Nearest 1", 5: "Nearest 5", 20: "Nearest 20"}
    x = np.arange(len(CITY_ORDER))
    width = 0.24
    for i, n in enumerate(ns):
        vals = [
            float(frame[(frame["city"] == city) & (frame["n"] == n)]["F15"].iloc[0])
            for city in CITY_ORDER
        ]
        bars = ax.bar(
            x + (i - 1) * width,
            vals,
            width,
            color=colors[n],
            label=labels[n],
            zorder=3,
            edgecolor=PAGE,
            linewidth=0.4,
        )
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val + 1.8,
                f"{val:.0f}",
                ha="center",
                va="bottom",
                fontproperties=_fp(True, 10),
                color=INK if n != 20 else colors[20],
            )
    ax.set_xticks(x)
    ax.set_xticklabels(list(CITY_ORDER), fontproperties=_fp(False, 11))
    ax.set_ylim(0, 112)
    ax.set_xlim(-0.55, 4.55)
    _axis_labels(ax, "", "People within 15 minutes, percent")
    leg = ax.legend(
        frameon=True,
        loc="upper right",
        prop=_fp(False, 12),
        labelcolor=INK,
        edgecolor=INK,
        fancybox=False,
        borderpad=0.7,
        handlelength=1.2,
        fontsize=12,
    )
    leg.get_frame().set_linewidth(STROKE)
    leg.get_frame().set_facecolor(PAGE)
    for text in leg.get_texts():
        text.set_fontproperties(_fp(False, 12))
    return _save(fig, outfile or CHARTS / "f15_by_n.png")


def nstar_curves(outfile=None):
    nstar = pd.read_csv(DATA_PROCESSED / "nstar.csv")
    fig, ax = _open_plate(
        "CLINICS FOR 90%",
        "Coverage as well-placed clinics are added",
        "Each curve starts from an empty city and adds the next best clinic.\n"
        "The dot is N*: how many it takes for 90% of people to reach one in 15 minutes.\n"
        "Abuja is the only city that needs more clinics than it already holds.",
    )
    ax.axhline(90, color="#b7b0a4", lw=1.15, zorder=1)
    ax.text(0.22, 92.2, "90%", fontproperties=_fp(True, 11), color=MUTED, path_effects=HALO)
    label_at = {
        "Lagos": (2.50, 80),
        "Ibadan": (5.25, 83),
        "Kano": (0.18, 76),
        "Port Harcourt": (3.45, 56),
        "Abuja": (13.20, 78),
    }
    for _, row in nstar.iterrows():
        city = row.city
        curve = pd.read_csv(DATA_PROCESSED / f"{row.slug}_nstar_curve.csv")
        per_100k = curve["n_sites"].to_numpy(dtype=float) / (float(row["pop"]) / 1e5)
        covered = curve["pop_covered"].to_numpy(dtype=float) * 100.0
        ax.plot(per_100k, covered, color=CITY_COLOR[city], lw=2.6, zorder=3, solid_capstyle="round")
        ax.scatter(
            [float(row["N_star_per_100k"])],
            [90.0],
            s=42,
            color=CITY_COLOR[city],
            zorder=4,
            edgecolors=PAGE,
            linewidths=0.9,
        )
        lx, ly = label_at[city]
        ax.text(
            lx,
            ly,
            city,
            fontproperties=_fp(True, 12),
            color=CITY_COLOR[city],
            va="center",
            path_effects=HALO,
            zorder=5,
        )
    ax.set_xlim(0, 15.5)
    ax.set_ylim(0, 100)
    _axis_labels(ax, "Well-placed clinics per 100,000 people", "People covered, percent")
    return _save(fig, outfile or CHARTS / "nstar_curves.png")


def _save(fig, outfile):
    path = CHARTS / outfile if not hasattr(outfile, "parent") else outfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, facecolor=PAGE, edgecolor="none")
    fig.savefig(path.with_suffix(".pdf"), facecolor=PAGE, edgecolor="none")
    plt.close(fig)
    return path


def _flow_header(ax, x, y, w, h, text, fc):
    ax.add_patch(
        Rectangle(
            (x, y),
            w,
            h,
            facecolor=fc,
            edgecolor=fc,
            linewidth=0,
            zorder=3,
        )
    )
    ax.text(
        x + 0.5 * w,
        y + 0.5 * h,
        text,
        ha="center",
        va="center",
        fontproperties=_fp(True, 12),
        color=PAGE,
        zorder=4,
    )


def _flow_box(ax, x, y, w, h, title, body, *, ec):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.006,rounding_size=0.012",
            facecolor=LAND,
            edgecolor=ec,
            linewidth=1.15,
            zorder=3,
            mutation_aspect=0.45,
        )
    )
    ax.text(
        x + 0.5 * w,
        y + h - 0.032,
        title,
        ha="center",
        va="top",
        fontproperties=_fp(True, 11),
        color=ec,
        zorder=4,
    )
    ax.text(
        x + 0.5 * w,
        y + 0.048,
        body,
        ha="center",
        va="center",
        fontproperties=_fp(False, 10),
        color=INK,
        zorder=4,
        linespacing=1.28,
    )


def _flow_arrow(ax, x0, y0, x1, y1):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops={
            "arrowstyle": "-|>",
            "color": INK,
            "lw": 1.4,
            "mutation_scale": 11,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=2,
    )


def pipeline_flowchart(outfile=None):
    fig, ax = _open_plate(
        "FROM STREETS TO SCORES",
        "Inventories, the walk, and what is reported",
        "Left: the four inventories. Middle: hexagons, streets, and the 15-minute walk.\n"
        "Right: F15, Gini, N* and the plates. Empty hexes stay; completeness is a table.\n"
        "Walk graph, five nearby GRID3 clinics and schools, 5 km/h.",
        diagram=True,
    )
    data_x, walk_x, score_x = 0.000, 0.350, 0.700
    col_w = 0.268
    header_h = 0.078
    box_h = 0.168
    gap = 0.022
    header_y = 0.910
    _flow_header(ax, data_x, header_y, col_w, header_h, "Data", "#163d44")
    _flow_header(ax, walk_x, header_y, col_w, header_h, "Walks", "#3d7a74")
    _flow_header(ax, score_x, header_y, col_w, header_h, "Scores", "#9b3b2f")

    data = [
        ("City outlines", "geoBoundaries metro\nlocal government areas"),
        ("People", "GRID3 / WorldPop v3.0\nscaled to mid-2025"),
        ("Clinics and schools", "GRID3 health and education.\nv3 where released; v2 if not"),
        ("Walking streets", "OpenStreetMap paths,\nnot the list of buildings"),
    ]
    walks = [
        ("Hexagons", "200 m on a side, matching\nBruno et al. Empty cells kept"),
        ("Snap to streets", "Centre to nearest node.\nFarther than 250 m is flagged"),
        ("Timed walks", "5 km/h to five clinics and\nfive schools; then averaged"),
        ("N* siting", "Place clinics until 90%\ncan walk 15 minutes to one"),
    ]
    scores = [
        ("City scores", "F15, average walk, Gini.\nn = 5 is the headline"),
        ("By service", "Health versus schools.\nUnder-five headcounts"),
        ("Placement", "N* against clinics held.\nFour cities already have enough"),
        ("Maps and checks", "Walking and population plates.\nCompleteness in a table"),
    ]
    first_top = header_y - 0.024
    ys = [first_top - box_h - i * (box_h + gap) for i in range(4)]
    for y, (title, body) in zip(ys, data):
        _flow_box(ax, data_x, y, col_w, box_h, title, body, ec="#163d44")
    for y, (title, body) in zip(ys, walks):
        _flow_box(ax, walk_x, y, col_w, box_h, title, body, ec="#3d7a74")
    for y, (title, body) in zip(ys, scores):
        _flow_box(ax, score_x, y, col_w, box_h, title, body, ec="#9b3b2f")

    stack_mid = 0.5 * (ys[0] + box_h + ys[-1])
    _flow_arrow(ax, data_x + col_w + 0.010, stack_mid, walk_x - 0.010, stack_mid)
    _flow_arrow(ax, walk_x + col_w + 0.010, stack_mid, score_x - 0.010, stack_mid)

    ax.text(
        0.5,
        0.012,
        "Also stored: nearest 1 and nearest 20; 3.5 km/h. Straight-line times are a check, never the result.",
        ha="center",
        va="bottom",
        fontproperties=_fp(False, 9),
        color=MUTED,
        zorder=4,
    )
    return _save(fig, outfile or CHARTS / "pipeline.png")


def write_charts() -> list:
    out = [
        pipeline_flowchart(),
        f15_vs_density(),
        f15_by_n(),
        nstar_curves(),
    ]
    for path in out:
        print(f"  {path}", flush=True)
    return out


if __name__ == "__main__":
    write_charts()
