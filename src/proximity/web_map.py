"""Compact GeoJSON for the public web map. One city at a time in the browser."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from mapclassify import FisherJenks

from .cities import ABUJA_PLATE_WARDS, CITIES, LAGOS_PLATE_LGAS
from .metrics import gini
from .paths import DATA_PROCESSED, WEB_DATA

CITIES_DIR = WEB_DATA / "cities"
POP_MIN = 5.0
COORD_DECIMALS = 5
THRESHOLD_MIN = 15.0
# Extra MultiPolygon islands along GRID3 ward borders. Never independently
# simplify adjacent wards: that opens gap slivers along shared edges.
MIN_WARD_PART_M2 = 50_000.0
MIN_WARD_PART_SHARE = 0.10

# Same ColorBrewer YlOrRd 6 as qgis/build_city_project.py.
POP_YLORRD = ("#ffeda0", "#fed976", "#feb24c", "#fd8d3c", "#e31a1c", "#800026")

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
ALWAYS_SHOW_LABELS = {
    "abuja": ("Lugbe", "Apo", "Lokogoma", "Nyanya", "Karu", "Gwarinpa", "Kabusa", "Kubwa", "Dutse"),
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


def _load(path: Path, layer: str | None = None) -> gpd.GeoDataFrame | None:
    if not path.exists():
        return None
    kwargs = {"layer": layer} if layer else {}
    gdf = gpd.read_file(path, **kwargs)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326)


def _round_coords(obj, n: int = COORD_DECIMALS):
    if isinstance(obj, (float, int, np.floating, np.integer)):
        return round(float(obj), n)
    if isinstance(obj, (list, tuple)):
        return [_round_coords(x, n) for x in obj]
    return obj


def _write_fc(gdf: gpd.GeoDataFrame, path: Path, props: list[str], *, round_geom: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    features = []
    keep = [c for c in props if c in gdf.columns]
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        properties = {}
        for key in keep:
            val = row[key]
            if pd.isna(val):
                properties[key] = None
            elif isinstance(val, (np.floating, float)):
                properties[key] = None if not np.isfinite(val) else round(float(val), 2)
            elif isinstance(val, (np.integer, int)):
                properties[key] = int(val)
            elif isinstance(val, (np.bool_, bool)):
                properties[key] = bool(val)
            else:
                properties[key] = str(val)
        coords = geom.__geo_interface__["coordinates"]
        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": {
                    "type": geom.geom_type,
                    "coordinates": _round_coords(coords) if round_geom else coords,
                },
            }
        )
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")))


def _display_name(name: object) -> str:
    text = "" if name is None or (isinstance(name, float) and np.isnan(name)) else str(name).strip()
    if not text:
        return ""
    return SHORT_LABELS.get(text, text.replace("-", "‑"))


def _first_col(gdf: gpd.GeoDataFrame, names: tuple[str, ...]) -> pd.Series | None:
    for name in names:
        if name in gdf.columns:
            return gdf[name]
    return None


def _text(series: pd.Series | None, n: int) -> pd.Series:
    if series is None:
        return pd.Series([""] * n, dtype="object")
    return series.fillna("").astype(str).str.strip()


def _weighted(frame: pd.DataFrame, col: str, pop: np.ndarray) -> float:
    if col not in frame.columns:
        return float("nan")
    val = pd.to_numeric(frame[col], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(val) & np.isfinite(pop) & (pop > 0)
    if not ok.any():
        return float("nan")
    return float(np.average(val[ok], weights=pop[ok]))


def _share_within(frame: pd.DataFrame, col: str, pop: np.ndarray) -> float:
    if col not in frame.columns or pop.sum() <= 0:
        return float("nan")
    val = pd.to_numeric(frame[col], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(val)
    if not ok.any():
        return float("nan")
    return float(pop[ok & (val <= THRESHOLD_MIN)].sum() / pop.sum())


def _ward_hex_overlap(hexes: gpd.GeoDataFrame, wards: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Slice each hexagon across the wards it covers, so a tiny ward still gets people."""
    keep_h = [c for c in ("pop", "PT_k", "t_health", "t_school", "off_network", "geometry") if c in hexes.columns]
    keep_w = [c for c in ("locator", "lganame", "geometry") if c in wards.columns]
    if "locator" not in keep_w:
        return gpd.GeoDataFrame()
    utm = wards.estimate_utm_crs()
    h = hexes[keep_h].to_crs(utm).copy()
    w = wards[keep_w].to_crs(utm).copy()
    h.geometry = h.geometry.make_valid()
    w.geometry = w.geometry.make_valid()
    h["_hex_area"] = h.geometry.area.replace(0, np.nan)
    try:
        ov = gpd.overlay(h, w, how="intersection", keep_geom_type=False)
    except Exception:
        ov = gpd.GeoDataFrame()
    if ov is None or ov.empty:
        return gpd.GeoDataFrame()
    frac = (ov.geometry.area / ov["_hex_area"]).clip(0, 1).fillna(0)
    ov["_people"] = ov["pop"].fillna(0) * frac
    return ov


def _nice(value: float) -> float:
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


def _pop_breaks(hexes: gpd.GeoDataFrame) -> list[dict]:
    y = hexes.loc[hexes["pop"].fillna(0) > POP_MIN, "pop"].to_numpy(dtype=float)
    y = y[np.isfinite(y)]
    if y.size < 6:
        lo, hi = (float(y.min()), float(y.max())) if y.size else (0.0, 1.0)
        return [{"lo": lo, "hi": hi, "color": POP_YLORRD[-1], "label": f"{lo:,.0f}–{hi:,.0f}"}]
    k = min(6, max(3, len(np.unique(np.round(y)))))
    try:
        clf = FisherJenks(y, k=k)
        edges = _round_edges([float(y.min())] + [float(b) for b in clf.bins])
    except ValueError:
        qs = np.quantile(y, np.linspace(0, 1, k + 1))
        edges = _round_edges([float(v) for v in qs])
    n = len(edges) - 1
    breaks = []
    for i in range(n):
        lo, hi = edges[i], edges[i + 1]
        color = POP_YLORRD[round(i * (len(POP_YLORRD) - 1) / max(n - 1, 1))]
        label = f"{lo:,.0f}+" if i == n - 1 else f"{lo:,.0f}–{hi:,.0f}"
        breaks.append({"lo": round(lo), "hi": round(hi), "color": color, "label": label})
    return breaks


def _ward_reading(row: pd.Series, city_f15: float) -> str:
    f15 = row.get("f15")
    if pd.isna(f15) or row.get("people", 0) <= 0:
        return "Too few people in scored neighbourhoods here to quote a walking share."
    f15 = float(f15)
    if f15 >= 85:
        lead = "Most people here already finish inside 15 minutes."
    elif f15 >= 50:
        lead = "About half the people here can walk to clinics and schools in 15 minutes."
    elif f15 >= 15:
        lead = "Most people here walk longer than 15 minutes."
    else:
        lead = "Almost nobody here is within a 15-minute walk of clinics and schools."
    health = row.get("f15_health")
    school = row.get("f15_school")
    split = ""
    if pd.notna(health) and pd.notna(school):
        gap = float(health) - float(school)
        if gap <= -8:
            split = " Clinics are the weaker of the two services."
        elif gap >= 8:
            split = " Schools are the weaker of the two services."
        else:
            split = " Clinics and schools are about even."
    versus = ""
    if np.isfinite(city_f15):
        diff = f15 - city_f15
        if abs(diff) >= 5:
            versus = f" That is {abs(diff):.0f} points {'above' if diff > 0 else 'below'} the city as a whole."
    street = ""
    off = row.get("off_pct")
    if pd.notna(off) and float(off) >= 5:
        street = " Some of the long walks sit off the mapped street network."
    return lead + split + versus + street


def _union(gdf: gpd.GeoDataFrame | None):
    if gdf is None or gdf.empty:
        return None
    geom = gdf.geometry.union_all()
    if geom is None or geom.is_empty:
        return None
    return geom


def _frame_mask(slug: str):
    """Study outline on the web map: Lagos-7 LGAs, Abuja-7 wards, metro for the rest."""
    if slug == "lagos":
        lgas = _load(DATA_PROCESSED / f"{slug}_metro_lgas.gpkg")
        if lgas is not None and not lgas.empty:
            field = "shapeName" if "shapeName" in lgas.columns else "lganame"
            sub = lgas[lgas[field].isin(LAGOS_PLATE_LGAS)]
            mask = _union(sub)
            if mask is not None:
                return mask
    if slug == "abuja":
        wards = _load(DATA_PROCESSED / f"{slug}_wards.gpkg", layer=f"{slug}_wards")
        if wards is not None and "locator" in wards.columns:
            sub = wards[wards["locator"].isin(ABUJA_PLATE_WARDS)]
            mask = _union(sub)
            if mask is not None:
                return mask
    bound = _load(DATA_PROCESSED / f"{slug}_study_boundary.gpkg")
    return _union(bound)


def _drop_holes(geom, min_hole_m2: float):
    from shapely.geometry import MultiPolygon, Polygon

    if geom is None or geom.is_empty:
        return geom
    if geom.geom_type == "Polygon":
        holes = [ring for ring in geom.interiors if Polygon(ring).area >= min_hole_m2]
        return Polygon(geom.exterior, holes)
    if geom.geom_type == "MultiPolygon":
        return MultiPolygon([_drop_holes(part, min_hole_m2) for part in geom.geoms])
    return geom


def _clean_admin(gdf: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame | None:
    """Drop leftover islands on ward/LGA polygons. Do not simplify shared edges."""
    if gdf is None or gdf.empty:
        return gdf
    utm = gdf.estimate_utm_crs()
    work = gdf.to_crs(utm).copy()
    work["_src"] = np.arange(len(work))
    parts = work.explode(index_parts=False).reset_index(drop=True)
    parts["_part_area"] = parts.geometry.area
    totals = parts.groupby("_src")["_part_area"].transform("sum")
    parts["_share"] = parts["_part_area"] / totals.replace(0, np.nan)
    keep = (parts["_part_area"] >= MIN_WARD_PART_M2) | (parts["_share"].fillna(0) >= MIN_WARD_PART_SHARE)
    largest_idx = parts.sort_values("_part_area").groupby("_src", as_index=False).tail(1).index
    parts = parts.loc[keep | parts.index.isin(largest_idx)].copy()
    parts["geometry"] = parts.geometry.map(lambda geom: _drop_holes(geom, MIN_WARD_PART_M2))
    parts = parts.dissolve(by="_src", as_index=False, aggfunc="first")
    drop = [c for c in ("_src", "_part_area", "_share") if c in parts.columns]
    return parts.drop(columns=drop).to_crs(4326).reset_index(drop=True)


def _rows_in_mask(gdf: gpd.GeoDataFrame | None, mask_wgs) -> gpd.GeoDataFrame | None:
    """Keep rows whose representative point sits inside the map frame."""
    if gdf is None or gdf.empty or mask_wgs is None:
        return gdf
    poly = gpd.GeoDataFrame({"geometry": [mask_wgs]}, crs=4326)
    pts = gdf.copy()
    pts["geometry"] = pts.geometry.representative_point()
    joined = gpd.sjoin(pts, poly, predicate="within", how="inner")
    return gdf.loc[joined.index.unique()].copy().reset_index(drop=True)


def _points_in_mask(gdf: gpd.GeoDataFrame | None, mask_wgs) -> gpd.GeoDataFrame | None:
    if gdf is None or gdf.empty or mask_wgs is None:
        return gdf
    poly = gpd.GeoDataFrame({"geometry": [mask_wgs]}, crs=4326)
    pts = gdf.copy()
    pts["geometry"] = pts.geometry.centroid
    joined = gpd.sjoin(pts, poly, predicate="within", how="inner")
    return joined.drop(columns=["index_right"], errors="ignore").reset_index(drop=True)


def _road_kind(value) -> str:
    text = str(value or "").lower()
    if any(tag in text for tag in ("motorway", "trunk", "primary")):
        return "main"
    return "street"


def _roads(slug: str, mask) -> gpd.GeoDataFrame | None:
    """Walking streets for the map. Keep the carriageways, drop service tracks."""
    gdf = _load(DATA_PROCESSED / f"{slug}_walk_edges.gpkg", layer=f"{slug}_walk_edges")
    if gdf is None or gdf.empty:
        return None
    if "highway" in gdf.columns:
        hwy = gdf["highway"].astype(str).str.lower()
        drop = hwy.str.contains("service|track|path|footway|steps|cycleway|construction", regex=True)
        gdf = gdf.loc[~drop].copy()
    if mask is not None:
        frame = gpd.GeoDataFrame({"geometry": [mask]}, crs=4326)
        try:
            gdf = gpd.clip(gdf, frame, keep_geom_type=True)
        except Exception:
            gdf = gdf[gdf.intersects(mask)].copy()
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if gdf.empty:
        return None
    gdf["kind"] = gdf["highway"].map(_road_kind) if "highway" in gdf.columns else "street"
    utm = gdf.estimate_utm_crs()
    work = gdf[["kind", "geometry"]].to_crs(utm)
    work["geometry"] = work.geometry.simplify(30.0, preserve_topology=False)
    work = work[work.geometry.notna() & ~work.geometry.is_empty]
    work = work[work.geometry.length >= 40]
    if work.empty:
        return None
    if len(work) > 18000:
        main = work[work["kind"] == "main"]
        street = work[work["kind"] != "main"].iloc[::2]
        work = gpd.GeoDataFrame(pd.concat([main, street], ignore_index=True), geometry="geometry", crs=utm)
    return work.to_crs(4326)


def _count_in(points: gpd.GeoDataFrame | None, wards: gpd.GeoDataFrame) -> pd.Series:
    empty = pd.Series(0, index=wards.index, dtype=int)
    if points is None or points.empty or "locator" not in wards.columns:
        return empty
    pts = points[["geometry"]].copy()
    pts.geometry = pts.geometry.centroid
    joined = gpd.sjoin(pts, wards[["locator", "geometry"]], predicate="within", how="left")
    counts = joined.groupby("locator").size()
    return wards["locator"].map(counts).fillna(0).astype(int)


def _hexes(slug: str, wards: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame | None:
    gdf = _load(DATA_PROCESSED / f"{slug}_hexes.gpkg", layer=f"{slug}_hexes")
    if gdf is None:
        return None
    gdf = gdf[gdf["pop"].fillna(0) > POP_MIN].copy().reset_index(drop=True)
    gdf["minutes"] = gdf["PT_k"]
    gdf["people"] = gdf["pop"].fillna(0).round().astype(int)
    gdf["clinic_min"] = gdf["t_health"] if "t_health" in gdf.columns else np.nan
    gdf["school_min"] = gdf["t_school"] if "t_school" in gdf.columns else np.nan
    gdf["k_clinic"] = pd.to_numeric(gdf["k_health"], errors="coerce") if "k_health" in gdf.columns else np.nan
    gdf["k_school"] = pd.to_numeric(gdf["k_school"], errors="coerce") if "k_school" in gdf.columns else np.nan
    gdf["within_15"] = np.isfinite(gdf["PT_k"]) & (gdf["PT_k"] <= THRESHOLD_MIN)
    if "off_network" in gdf.columns:
        gdf["off_street"] = gdf["off_network"].fillna(False).astype(bool)
    else:
        gdf["off_street"] = False
    gdf["ward"] = ""
    gdf["lga"] = ""
    if wards is not None and not wards.empty:
        pts = gdf[["geometry"]].copy()
        pts.geometry = pts.geometry.representative_point()
        keep = [c for c in ("locator", "lganame", "geometry") if c in wards.columns]
        joined = gpd.sjoin(pts, wards[keep], predicate="within", how="left")
        joined = joined[~joined.index.duplicated(keep="first")]
        gdf["ward"] = joined.reindex(gdf.index)["locator"].fillna("").astype(str).values
        if "lganame" in joined.columns:
            gdf["lga"] = joined.reindex(gdf.index)["lganame"].fillna("").astype(str).values
    return gdf


def _points(slug: str, kind: str) -> gpd.GeoDataFrame | None:
    gdf = _load(DATA_PROCESSED / f"{slug}_{kind}_points.gpkg")
    if gdf is None or gdf.empty:
        return None
    n = len(gdf)
    out = gpd.GeoDataFrame({"geometry": gdf.geometry.centroid}, crs=gdf.crs)
    if kind == "health":
        out["name"] = _text(_first_col(gdf, ("facility_n", "facility_name", "name")), n)
        out["ownership"] = _text(_first_col(gdf, ("ownership", "facility_ownership")), n)
        out["level"] = _text(_first_col(gdf, ("facility_l", "facility_level")), n)
        out["kind_detail"] = _text(_first_col(gdf, ("facility_2", "facility_type")), n)
        out["lga"] = _text(_first_col(gdf, ("lga", "lga_standard", "lganame")), n)
        out["ward"] = _text(_first_col(gdf, ("ward", "ward_standard", "wardname")), n)
        out["kind"] = "clinic"
    else:
        out["name"] = _text(_first_col(gdf, ("name",)), n)
        out["ownership"] = _text(_first_col(gdf, ("management",)), n)
        out["level"] = _text(_first_col(gdf, ("education", "subtype")), n)
        out["kind_detail"] = _text(_first_col(gdf, ("category", "poi_type")), n)
        out["lga"] = _text(_first_col(gdf, ("lganame", "lga")), n)
        out["ward"] = _text(_first_col(gdf, ("wardname", "ward")), n)
        out["kind"] = "school"
    return out


def _places(slug: str) -> gpd.GeoDataFrame | None:
    gdf = _load(DATA_PROCESSED / f"{slug}_places.gpkg")
    if gdf is None or gdf.empty:
        return None
    out = gdf.copy()
    out.geometry = out.geometry.centroid
    out["label"] = out["name"].map(_display_name)
    always = {n.casefold() for n in ALWAYS_SHOW_LABELS.get(slug, ())}
    names = out["name"].astype(str)
    out["always"] = names.str.casefold().isin(always) | out["label"].astype(str).str.casefold().isin(always)
    out["always"] = out["always"].astype(int)
    if "pinned" in out.columns:
        out["pinned"] = pd.to_numeric(out["pinned"], errors="coerce").fillna(0).astype(int)
    else:
        out["pinned"] = 0
    if "priority" in out.columns:
        out["priority"] = pd.to_numeric(out["priority"], errors="coerce").fillna(5).astype(int)
    else:
        out["priority"] = np.where(out["pinned"] == 1, 10, 6)
    if "rank" in out.columns:
        out["rank"] = pd.to_numeric(out["rank"], errors="coerce").fillna(5).astype(int)
    return out


def _wards(slug: str, hexes_all: gpd.GeoDataFrame | None, clinics, schools) -> gpd.GeoDataFrame | None:
    gdf = _load(DATA_PROCESSED / f"{slug}_wards.gpkg", layer=f"{slug}_wards")
    if gdf is None:
        return None
    gdf = gdf.copy()
    if slug == "lagos" and "lganame" in gdf.columns:
        gdf = gdf[gdf["lganame"].isin(LAGOS_PLATE_LGAS)].copy()
    elif slug == "abuja" and "locator" in gdf.columns:
        gdf = gdf[gdf["locator"].isin(ABUJA_PLATE_WARDS)].copy()
    if gdf.empty:
        return gdf
    gdf["name"] = gdf["locator"] if "locator" in gdf.columns else ""
    gdf["label"] = gdf["name"].map(_display_name)
    gdf["lga"] = gdf["lganame"] if "lganame" in gdf.columns else ""

    city_f15 = float("nan")
    city_pop = 0.0
    if hexes_all is not None and not hexes_all.empty:
        pop_all = hexes_all["pop"].fillna(0).to_numpy(dtype=float)
        city_pop = float(pop_all.sum())
        pt = hexes_all["PT_k"].to_numpy(dtype=float) if "PT_k" in hexes_all.columns else np.full(len(hexes_all), np.nan)
        mapped = np.isfinite(pt)
        if mapped.any() and pop_all[mapped].sum() > 0:
            city_f15 = float(pop_all[mapped & (pt <= THRESHOLD_MIN)].sum() / pop_all.sum()) * 100.0

        ov = _ward_hex_overlap(hexes_all, gdf)
        if ov is None or ov.empty:
            pts = hexes_all.copy()
            pts.geometry = pts.geometry.representative_point()
            keep = [c for c in ("locator", "lganame", "geometry") if c in gdf.columns]
            ov = gpd.sjoin(pts, gdf[keep], predicate="within", how="inner")
            ov["_people"] = ov["pop"].fillna(0)

        rows = []
        for (locator, lga), chunk in ov.groupby(["locator", "lganame"], dropna=False):
            pop = chunk["_people"].to_numpy(dtype=float) if "_people" in chunk.columns else chunk["pop"].fillna(0).to_numpy(dtype=float)
            people = float(pop.sum())
            f15 = _share_within(chunk, "PT_k", pop)
            f15_h = _share_within(chunk, "t_health", pop)
            f15_s = _share_within(chunk, "t_school", pop)
            off = float("nan")
            if "off_network" in chunk.columns and people > 0:
                off = float(pop[chunk["off_network"].fillna(False).to_numpy()].sum() / people * 100.0)
            pt_vals = pd.to_numeric(chunk["PT_k"], errors="coerce").to_numpy(dtype=float) if "PT_k" in chunk.columns else np.array([])
            rows.append(
                {
                    "locator": locator,
                    "lganame": lga,
                    "people": int(round(people)),
                    "walk": _weighted(chunk, "PT_k", pop),
                    "walk_clinic": _weighted(chunk, "t_health", pop),
                    "walk_school": _weighted(chunk, "t_school", pop),
                    "f15": f15 * 100.0 if np.isfinite(f15) else np.nan,
                    "f15_health": f15_h * 100.0 if np.isfinite(f15_h) else np.nan,
                    "f15_school": f15_s * 100.0 if np.isfinite(f15_s) else np.nan,
                    "beyond": int(round(people * (1.0 - f15))) if np.isfinite(f15) else None,
                    "off_pct": off,
                    "hexes": int(len(chunk)),
                    "gini": gini(pt_vals, pop) if pt_vals.size else np.nan,
                    "share": (people / city_pop * 100.0) if city_pop else np.nan,
                }
            )
        stats = pd.DataFrame(rows)
        gdf = gdf.merge(stats, on=["locator", "lganame"], how="left")

    gdf["clinics"] = _count_in(clinics, gdf)
    gdf["schools"] = _count_in(schools, gdf)

    scored = gdf["f15"].notna() & (gdf["people"].fillna(0) > 0)
    gdf["of"] = int(scored.sum())
    gdf["rank"] = np.nan
    if scored.any():
        # 1 = highest F15 (best served).
        order = gdf.loc[scored, "f15"].rank(method="min", ascending=False)
        gdf.loc[scored, "rank"] = order.astype(int)

    readings = []
    for _, row in gdf.iterrows():
        readings.append(_ward_reading(row, city_f15))
    gdf["reading"] = readings
    return gdf


def _boundary(slug: str) -> gpd.GeoDataFrame | None:
    gdf = _load(DATA_PROCESSED / f"{slug}_study_boundary.gpkg")
    if gdf is None:
        return None
    gdf = gdf.copy()
    gdf["name"] = CITIES[slug].name
    return gdf[["name", "geometry"]]


def _nstar(slug: str) -> gpd.GeoDataFrame | None:
    gdf = _load(DATA_PROCESSED / f"{slug}_nstar_sites.gpkg")
    if gdf is None or gdf.empty:
        return None
    out = gdf.copy()
    out.geometry = out.geometry.centroid
    if "rank" not in out.columns:
        out["rank"] = range(1, len(out) + 1)
    return out[["rank", "geometry"]]


def _city_blurb(slug: str) -> str:
    return {
        "lagos": "This map is the seven inner local government areas, not the sixteen-LGA metro. The long walks sit on the Lekki corridor.",
        "ibadan": "The most compact city in the set, and the closest street map. Olopomewa is the hole that still moves the city score.",
        "kano": "Denser than Lagos, but the later population lives in Ungogo and Kumbotso while the clinics stayed in the old city.",
        "port_harcourt": "Crowded, and still far. The old township is walkable. Most people now live in Obio/Akpor, and the clinics did not move with them.",
        "abuja": "This map is seven AMAC wards plus Kubwa, Dutse and Usuma in Bwari, not the whole municipal area. Some of the empty cells are missing streets.",
    }.get(slug, "")


def _metrics(pop_breaks: dict[str, list[dict]]) -> dict:
    metrics = pd.read_csv(DATA_PROCESSED / "city_metrics.csv")
    nstar = pd.read_csv(DATA_PROCESSED / "nstar.csv")
    complete = pd.read_csv(DATA_PROCESSED / "completeness.csv")
    plate = (
        pd.read_csv(DATA_PROCESSED / "plate_metrics.csv")
        if (DATA_PROCESSED / "plate_metrics.csv").exists()
        else pd.DataFrame()
    )
    cities = {}
    for slug, city in CITIES.items():
        row = metrics[metrics["slug"] == slug]
        ns = nstar[nstar["slug"] == slug]
        cm = complete[complete["slug"] == slug]
        if row.empty:
            continue
        r = row.iloc[0]
        n = ns.iloc[0] if len(ns) else None
        c = cm.iloc[0] if len(cm) else None
        entry = {
            "name": city.name,
            "state": city.state,
            "slug": slug,
            "bbox": list(city.bbox),
            "blurb": _city_blurb(slug),
            "pop": int(round(float(r["pop_total"]))),
            "pt": round(float(r["PT_city"]), 1),
            "f15": round(float(r["F15"]) * 100, 1),
            "gini": round(float(r["Gini_PT"]), 3),
            "clinics": int(r["health_n"]),
            "schools": int(r["school_n"]),
            "n_dual": int(r["n_dual"]),
            "speed": "5 km/h",
            "people_breaks": pop_breaks.get(slug, []),
        }
        if n is not None:
            entry.update(
                {
                    "nstar": int(n["N_star"]),
                    "nstar_per_100k": round(float(n["N_star_per_100k"]), 1),
                    "clinics_cover": round(float(n["pop_covered"]) * 100, 1),
                    "nstar_vs_stock": round(float(n["sites_vs_existing"]), 2),
                }
            )
        if c is not None:
            entry.update(
                {
                    "median_snap_m": round(float(c["median_snap_m"])),
                    "people_off_street": round(float(c["pop_share_offnetwork"]) * 100, 1),
                }
            )
        if not plate.empty:
            cuts = plate[plate["city"] == city.name]
            if len(cuts):
                entry["cuts"] = [
                    {
                        "cut": rec["cut"],
                        "units": rec["units"],
                        "pop": int(round(float(rec["pop"]))),
                        "f15": round(float(rec["F15"]) * 100, 1),
                        "pt": round(float(rec["PT_city"]), 1),
                    }
                    for rec in cuts.to_dict("records")
                ]
                plate_row = cuts[cuts["cut"] == "plate"]
                if slug in ("lagos", "abuja") and len(plate_row):
                    p = plate_row.iloc[0]
                    entry["metro_f15"] = entry["f15"]
                    entry["metro_pt"] = entry["pt"]
                    entry["metro_pop"] = entry["pop"]
                    entry["metro_gini"] = entry["gini"]
                    entry["f15"] = round(float(p["F15"]) * 100, 1)
                    entry["pt"] = round(float(p["PT_city"]), 1)
                    entry["pop"] = int(round(float(p["pop"])))
                    entry["gini"] = round(float(p["Gini_PT"]), 3)
                    entry["frame"] = str(p["units"])
                    entry["frame_note"] = (
                        f"Scores on this map are the {p['units']}. "
                        "The paper headline is still the metro."
                    )
        cities[slug] = entry
    return {
        "title": "Fifteen minutes on foot",
        "subtitle": "Walking to clinics and schools in Lagos, Kano, Ibadan, Abuja and Port Harcourt",
        "author": "Wisdom Akpabio",
        "year": 2026,
        "mode": "OSM walk graph, 5 km/h, five nearest clinics and five nearest schools",
        "inventory": "GRID3 clinics and schools. OpenStreetMap streets, not amenities.",
        "order": ["lagos", "ibadan", "kano", "port_harcourt", "abuja"],
        "cities": cities,
    }


def _boundary_from_mask(slug: str, mask):
    if mask is None:
        return _boundary(slug)
    gdf = gpd.GeoDataFrame({"name": [CITIES[slug].name], "geometry": [mask]}, crs=4326)
    return gdf


def _places_in_frame(places: gpd.GeoDataFrame | None, mask, slug: str) -> gpd.GeoDataFrame | None:
    if places is None or places.empty:
        return places
    if mask is None:
        return places
    inside = _points_in_mask(places, mask)
    always = {n.casefold() for n in ALWAYS_SHOW_LABELS.get(slug, ())}
    extra = places[
        places["name"].astype(str).str.casefold().isin(always)
        | places["label"].astype(str).str.casefold().isin(always)
    ]
    frames = [frame for frame in (inside, extra) if frame is not None and not frame.empty]
    if not frames:
        return inside
    out = pd.concat(frames, ignore_index=True)
    out = gpd.GeoDataFrame(out, geometry="geometry", crs=places.crs)
    return out.drop_duplicates(subset=["name"], keep="first").reset_index(drop=True)


def export_city(slug: str) -> dict:
    out = CITIES_DIR / slug
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    mask = _frame_mask(slug)
    wards_raw = _load(DATA_PROCESSED / f"{slug}_wards.gpkg", layer=f"{slug}_wards")
    hexes_all = _load(DATA_PROCESSED / f"{slug}_hexes.gpkg", layer=f"{slug}_hexes")
    hexes_stats = _rows_in_mask(hexes_all, mask)
    clinics = _points_in_mask(_points(slug, "health"), mask)
    schools = _points_in_mask(_points(slug, "school"), mask)
    hexes = _hexes(slug, wards_raw)
    hexes = _rows_in_mask(hexes, mask)
    if hexes is not None and not hexes.empty:
        _write_fc(
            hexes,
            out / "hexes.geojson",
            [
                "minutes",
                "people",
                "clinic_min",
                "school_min",
                "k_clinic",
                "k_school",
                "within_15",
                "off_street",
                "ward",
                "lga",
            ],
        )
        written["hexes"] = len(hexes)
        written["people_breaks"] = _pop_breaks(hexes_stats if hexes_stats is not None else hexes)
        written["map_pop"] = int(hexes["people"].fillna(0).sum()) if "people" in hexes.columns else 0
    if clinics is not None and not clinics.empty:
        _write_fc(clinics, out / "clinics.geojson", ["name", "kind", "ownership", "level", "kind_detail", "lga", "ward"])
        written["clinics"] = len(clinics)
    if schools is not None and not schools.empty:
        _write_fc(schools, out / "schools.geojson", ["name", "kind", "ownership", "level", "kind_detail", "lga", "ward"])
        written["schools"] = len(schools)
    wards = _clean_admin(_wards(slug, hexes_stats, clinics, schools))
    if wards is not None and not wards.empty:
        _write_fc(
            wards,
            out / "wards.geojson",
            [
                "name",
                "label",
                "lga",
                "people",
                "walk",
                "walk_clinic",
                "walk_school",
                "f15",
                "f15_health",
                "f15_school",
                "beyond",
                "clinics",
                "schools",
                "off_pct",
                "hexes",
                "gini",
                "share",
                "rank",
                "of",
                "reading",
            ],
            round_geom=False,
        )
        written["wards"] = len(wards)
    if wards is not None and not wards.empty:
        utm = wards.estimate_utm_crs()
        outline = wards.to_crs(utm).geometry.union_all()
        outline = _drop_holes(outline, 1.0e12)
        bound = gpd.GeoDataFrame(
            {"name": [CITIES[slug].name], "geometry": [outline]},
            crs=utm,
        ).to_crs(4326)
    else:
        bound = _boundary_from_mask(slug, mask)
    if bound is not None:
        _write_fc(bound, out / "boundary.geojson", ["name"], round_geom=False)
        written["boundary"] = len(bound)
    places = _places_in_frame(_places(slug), mask, slug)
    if places is not None and not places.empty:
        _write_fc(places, out / "places.geojson", ["name", "label", "place", "rank", "pinned", "priority", "always"])
        written["places"] = len(places)
    roads = _roads(slug, mask)
    if roads is not None and not roads.empty:
        _write_fc(roads, out / "roads.geojson", ["kind"])
        written["roads"] = len(roads)
    print(f"  {slug}: {written}", flush=True)
    return written


def export() -> Path:
    CITIES_DIR.mkdir(parents=True, exist_ok=True)
    pop_breaks = {}
    map_counts = {}
    for slug in CITIES:
        written = export_city(slug)
        if "people_breaks" in written:
            pop_breaks[slug] = written.pop("people_breaks")
        map_counts[slug] = {
            "clinics": written.get("clinics"),
            "schools": written.get("schools"),
        }
    meta = _metrics(pop_breaks)
    for slug, counts in map_counts.items():
        city = meta["cities"].get(slug)
        if not city:
            continue
        if counts.get("clinics") is not None:
            city["clinics"] = counts["clinics"]
        if counts.get("schools") is not None:
            city["schools"] = counts["schools"]
    (WEB_DATA / "metrics.json").write_text(json.dumps(meta, indent=2))
    return WEB_DATA / "metrics.json"


if __name__ == "__main__":
    print(export())
