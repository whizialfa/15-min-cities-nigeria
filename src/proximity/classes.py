"""Shared map classification for proximity time.

Imported by both `proximity.cartography` (the PNG/PDF plates) and
`qgis/build_city_project.py`, so the two deliverables cannot drift apart. Kept
dependency-free on purpose: the QGIS builder runs under QGIS's bundled Python 3.9,
which has no geopandas, so anything it imports must be stdlib only.
"""

from __future__ import annotations

# Fixed for every city rather than fitted per city. Natural breaks would hand each city
# its own class edges, which is precisely what stops two cities being read side by side —
# and comparing cities is the whole point of a five-city panel. Jenks is right for
# population, where no universal threshold exists; it is wrong here, where 15 minutes is
# the standard the paper is built on.
#
# 15 is an edge, so classes 1-3 sum to F15 by construction: the green block *is* the
# 15-minute city. Verified against the data — the three sum to the reported F15 for all
# five cities, and no class holds more than 53.5% of anyone's population.
#
# The 60 edge exists for Abuja and Port Harcourt. Without it everything above 30 min
# collapses into one class holding 45.3% of Abuja, spanning a half-hour walk to a
# four-hour one — least discriminating in the two cities whose access failure is the
# whole point. Splitting gives Abuja 36.0/9.3 and Port Harcourt 13.6/2.2. The top class
# is near-empty in the dense cities (Lagos 0.4%, Kano 0.0%) and that is the intended
# behaviour, not waste: in a fixed cross-city scheme, "nobody in Kano is more than an
# hour from a clinic" is a result. Do not prune it to fit the best-served city.
PT_CLASS_EDGES: tuple[float, ...] = (5.0, 10.0, 15.0, 30.0, 60.0)

PT_CLASS_NAMES: tuple[str, ...] = (
    "Very close",
    "Close",
    "Moderate",
    "Far",
    "Very far",
    "Extremely far",
)

PT_CLASS_RANGES: tuple[str, ...] = (
    "\u2264 5 min",
    "5\u201310 min",
    "10\u201315 min",
    "15\u201330 min",
    "30\u201360 min",
    "60+ min",
)

# Green through amber to red. 15 minutes falls on the green-to-amber step, so the
# threshold is legible before anyone reads the legend.
PT_CLASS_RGB: tuple[tuple[int, int, int], ...] = (
    (27, 94, 32),
    (102, 167, 86),
    (205, 220, 57),
    (245, 145, 32),
    (183, 28, 28),
    (103, 0, 13),
)

PT_CLASS_MAX = 100_000.0


def pt_class_labels(with_range: bool = True) -> list[str]:
    if not with_range:
        return list(PT_CLASS_NAMES)
    return [f"{n} ({r})" for n, r in zip(PT_CLASS_NAMES, PT_CLASS_RANGES)]


def pt_class_bounds() -> list[tuple[float, float]]:
    """(lo, hi) per class, lowest first."""
    edges = [0.0, *PT_CLASS_EDGES, PT_CLASS_MAX]
    return [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]


def pt_hex_colors() -> list[str]:
    return ["#%02x%02x%02x" % rgb for rgb in PT_CLASS_RGB]
