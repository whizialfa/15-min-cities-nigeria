"""Print layout: framed choropleth with title, legend, north arrow, scale.

Inspired by a planning-studio layout (boxed title, north arrow, scale, legend)
but not a copy: cream paper, hairline rules.

Two colour treatments, chosen by what the number means. Anything in minutes gets the
fixed five-class green-to-red scheme from `proximity.classes`, identical in every city so
the plates can be read against each other. Everything else is a magnitude with no
cross-city threshold, so it gets natural breaks fitted to that city on the teal ramp.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrow, FancyBboxPatch, Rectangle
from matplotlib_scalebar.scalebar import ScaleBar

from .cities import CITIES
from .classes import PT_CLASS_EDGES, PT_CLASS_NAMES, PT_CLASS_RANGES, pt_hex_colors
from .paths import DATA_PROCESSED, MAPS

PAPER = "#f4efe6"
INK = "#1c2430"
TEAL = ["#edf4ef", "#cfe3d6", "#8fb9a8", "#3d7a74", "#163d44"]
MASK_INK = "#9b3b2f"

# Minute metrics use the shared five-class scheme (see proximity.classes); everything
# else gets natural breaks fitted to that city.
MINUTE_BINS = list(PT_CLASS_EDGES)


def _jenks_or_quantile(values, k=5):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    try:
        import mapclassify

        clf = mapclassify.NaturalBreaks(x, k=min(k, max(3, x.size)))
        return list(clf.bins)
    except Exception:
        qs = np.linspace(0, 1, k + 1)[1:]
        return list(np.quantile(x, qs))


def _ramp(n: int):
    """n colours off the teal ramp, so the class count is free of len(TEAL)."""
    from matplotlib.colors import LinearSegmentedColormap, ListedColormap

    if n <= len(TEAL):
        return ListedColormap(TEAL[:n])
    ramp = LinearSegmentedColormap.from_list("teal", TEAL)
    return ListedColormap([ramp(i / (n - 1)) for i in range(n)])


def framed_choropleth(
    hexes,
    column: str,
    *,
    title: str,
    city_name: str,
    units: str,
    mode: str,
    vintage: str,
    boundary_def: str,
    outfile: Path | None = None,
    cmap_bins: list[float] | None = None,
    hatch_unmapped: bool = True,
    mask=None,
    mask_label: str | None = None,
):
    """One city, one metric, export PNG + PDF under maps/."""
    gdf = hexes.to_crs(hexes.estimate_utm_crs())
    fig = plt.figure(figsize=(11, 11), facecolor=PAPER)
    ax = fig.add_axes([0.08, 0.12, 0.84, 0.74])
    ax.set_facecolor("#e7e1d6")
    ax.set_aspect("equal")
    ax.axis("off")

    vals = gdf[column]
    finite = np.asarray(vals, dtype=float)
    has_values = np.isfinite(finite).any()
    lo = float(np.nanmin(finite)) if has_values else 0.0
    hi = float(np.nanmax(finite)) if has_values else 60.0

    from matplotlib.colors import BoundaryNorm, ListedColormap

    nominal = cmap_bins is None and units == "minutes"
    if nominal:
        boundaries = [0.0, *PT_CLASS_EDGES, max(hi, PT_CLASS_EDGES[-1] * 1.0001)]
        cmap = ListedColormap(pt_hex_colors())
    else:
        bins = list(cmap_bins) if cmap_bins is not None else _jenks_or_quantile(vals)
        boundaries = sorted({float(b) for b in [lo, *bins, hi] if lo <= b <= hi})
        if len(boundaries) < 3:
            boundaries = [0, 5, 10, 15, 30, 60]
        cmap = _ramp(len(boundaries) - 1)
    norm = BoundaryNorm(boundaries, cmap.N)

    if has_values:
        gdf.plot(
            column=column,
            ax=ax,
            cmap=cmap,
            norm=norm,
            linewidth=0.12,
            edgecolor="#c9c2b4",
            missing_kwds={"color": "#d9d3c7", "hatch": "///" if hatch_unmapped else None},
            legend=False,
        )
    else:
        gdf.plot(ax=ax, color="#d9d3c7", hatch="///", linewidth=0.12, edgecolor="#c9c2b4", legend=False)

    # Completeness mask. Texture, not tint: the colour ramp already owns lightness, so a
    # translucent veil would read as "fast". Dissolve through a 1 m buffer first — hexes
    # share edges only to floating-point precision, and the slivers left by a plain union
    # make the hatch outline all 7,000 of them.
    masked = np.zeros(len(gdf), dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    if masked.any():
        region = gdf[masked].geometry.buffer(1.0).union_all().buffer(-1.0)
        gpd.GeoSeries([region], crs=gdf.crs).plot(
            ax=ax, facecolor="none", edgecolor=MASK_INK, hatch="//", linewidth=0.8, zorder=5
        )

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    pad_x, pad_y = 0.03 * (xmax - xmin), 0.03 * (ymax - ymin)
    ax.set_xlim(xmin - pad_x, xmax + pad_x)
    ax.set_ylim(ymin - pad_y, ymax + pad_y)

    # Neatline
    ax.add_patch(
        Rectangle(
            (xmin - pad_x, ymin - pad_y),
            (xmax - xmin) + 2 * pad_x,
            (ymax - ymin) + 2 * pad_y,
            fill=False,
            edgecolor=INK,
            linewidth=1.1,
            zorder=6,
        )
    )

    # Title plate (top-left) — hairline, not a heavy black stamp
    fig_ax = fig.add_axes([0.08, 0.88, 0.55, 0.09])
    fig_ax.set_axis_off()
    fig_ax.set_xlim(0, 1)
    fig_ax.set_ylim(0, 1)
    fig_ax.add_patch(
        FancyBboxPatch(
            (0.0, 0.05),
            1.0,
            0.9,
            boxstyle="square,pad=0.0",
            facecolor=PAPER,
            edgecolor=INK,
            linewidth=0.8,
        )
    )
    fig_ax.text(0.03, 0.62, title, fontsize=13, fontweight="bold", color=INK, va="center")
    fig_ax.text(0.03, 0.28, city_name.upper(), fontsize=9, color="#3d7a74", va="center")

    # North arrow (top-right)
    arr_ax = fig.add_axes([0.84, 0.88, 0.08, 0.09])
    arr_ax.set_axis_off()
    arr_ax.set_xlim(0, 1)
    arr_ax.set_ylim(0, 1)
    arr_ax.add_patch(FancyArrow(0.5, 0.18, 0, 0.55, width=0.08, head_width=0.28, head_length=0.22, color=INK))
    arr_ax.text(0.5, 0.05, "N", ha="center", va="bottom", fontsize=9, fontweight="bold", color=INK)

    # Scale bar (metres in UTM)
    scalebar = ScaleBar(
        1,
        location="lower right",
        box_alpha=0.85,
        box_color=PAPER,
        color=INK,
        font_properties={"size": 8},
        border_pad=0.6,
    )
    ax.add_artist(scalebar)

    # Legend as labelled classes
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cax = fig.add_axes([0.08, 0.055, 0.84, 0.028])
    # Uniform spacing for the nominal classes: proportional would hand "Very far" 90% of
    # the bar wherever a city has a 200-minute tail, and the classes are ordinal anyway.
    cb = fig.colorbar(
        sm, cax=cax, orientation="horizontal", spacing="uniform" if nominal else "proportional"
    )
    # Label above the bar: ticks sit below it and used to collide with the vintage line.
    cb.ax.xaxis.set_label_position("top")
    cb.set_label(f"{column} ({units}) · {mode}", fontsize=8, color=INK, labelpad=6)
    if nominal:
        cb.set_ticks([(boundaries[i] + boundaries[i + 1]) / 2 for i in range(len(boundaries) - 1)])
        cb.ax.set_xticklabels(
            [f"{n}\n{r}" for n, r in zip(PT_CLASS_NAMES, PT_CLASS_RANGES)]
        )
        cb.ax.tick_params(length=0, labelsize=7.5, colors=INK)
    else:
        cb.ax.tick_params(labelsize=7, colors=INK)
    cb.outline.set_edgecolor(INK)

    if masked.any() and mask_label:
        ax.legend(
            handles=[
                Rectangle(
                    (0, 0), 1, 1, facecolor="none", edgecolor=MASK_INK, hatch="////", linewidth=0.7
                )
            ],
            labels=[mask_label],
            loc="upper left",
            fontsize=7.5,
            frameon=True,
            facecolor=PAPER,
            edgecolor=INK,
        )

    fig.text(
        0.08,
        0.012,
        f"{vintage} · {boundary_def}",
        ha="left",
        va="bottom",
        fontsize=6.5,
        color=INK,
    )

    outfile = Path(outfile) if outfile else MAPS / f"{city_name.lower().replace(' ', '_')}_{column}.png"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=220, facecolor=fig.get_facecolor())
    fig.savefig(outfile.with_suffix(".pdf"), facecolor=fig.get_facecolor())
    plt.close(fig)
    return outfile


def rebuild_pt_maps(slugs: list[str] | None = None) -> list[Path]:
    """Re-render PT_k from saved hexes and metrics, masked. Never re-routes."""
    out: list[Path] = []
    for slug in slugs or list(CITIES):
        hex_path = DATA_PROCESSED / f"{slug}_hexes.gpkg"
        met_path = DATA_PROCESSED / f"{slug}_metrics.csv"
        if not (hex_path.exists() and met_path.exists()):
            print(f"  {slug}: no hexes or metrics on disk, skipped", flush=True)
            continue
        hexes = gpd.read_file(hex_path)
        m = pd.read_csv(met_path).iloc[0]
        mask = hexes["off_network"].to_numpy(dtype=bool) if "off_network" in hexes else None
        share = float(np.mean(mask)) if mask is not None else 0.0
        png = framed_choropleth(
            hexes,
            "PT_k",
            title="Proximity time (health + education)",
            city_name=str(m["city"]),
            units="minutes",
            mode=f"{m['mode']} · n={int(m['n_dual'])}",
            vintage=(
                f"{m['pop_source']} · {m['health_source']} · {m['school_source']}"
                f" · hex side {int(m['hex_side_m'])} m"
            ),
            boundary_def=str(m["boundary"]),
            outfile=MAPS / f"{slug}_PT_k.png",
            mask=mask,
            mask_label=f"off the mapped walk network · {share:.0%} of hexagons",
        )
        out.append(png)
        print(f"  {slug} → {png.name} (masked {share:.1%})", flush=True)
    return out


if __name__ == "__main__":
    import sys

    rebuild_pt_maps(sys.argv[1:] or None)
