"""OSM named districts — suburb / quarter / neighbourhood — for plate labels.

Wards are too coarse (Kabusa) or too many (Lagos). This class is Apo, Lokogoma,
Ikoyi, Sangotedo: the names people use. Source is OpenStreetMap `place=*` plus
named residential land, clipped to the study boundary. GRID3 settlement points
fill pinned names OSM never tagged as a place (Apo).
"""

from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.ops import nearest_points

from .cities import ABUJA_PLATE_WARDS, CITIES, City, LAGOS_PLATE_LGAS
from .overpass import fetch_districts, fetch_named
from .paths import DATA_PROCESSED, DATA_RAW
from .wards import settlement_points, tidy_label

PLACE_PRIORITY = {
    "suburb": 10,
    "quarter": 9,
    "neighbourhood": 8,
    "residential": 7,
    "locality": 6,
    "town": 5,
    "village": 5,
    "hamlet": 3,
    "city": 1,
}
FOREIGN_PLACES = {
    "abuja",
    "lagos",
    "kano",
    "ibadan",
    "enugu",
    "kaduna",
    "jos",
    "warri",
    "benin",
    "maiduguri",
    "calabar",
}
CORE_TYPES = ("suburb", "quarter", "neighbourhood")
NOISE = re.compile(
    r"\b(?:church|mosque|school|market|mall|hotel|plaza|clinic|hospital|"
    r"university|campus|junction|bus stop|filling|petrol|bridge|substation|"
    r"roundabout|apartments?|quarters?)\b",
    re.I,
)
RESIDENTIAL_NOISE = re.compile(r"\b(?:area|section|phase|estate|close|street|road)\b", re.I)
# Districts the plates must try to name when OSM or GRID3 has them.
PINNED = {
    "lagos": (
        "ikoyi",
        "falomo",
        "sangotedo",
        "victoria island",
        "lekki",
        "ajah",
        "surulere",
        "apapa",
        "yaba",
        "obalende",
        "lagos island",
        "eko atlantic",
        "tarkwa bay",
        "abraham adesanya",
        "ilado",
        "oko agbo",
        "ijora",
        "ikeja",
        "mushin",
        "shomolu",
        "bariga",
        "oshodi",
        "festac",
        "alimosho",
        "agege",
        "ketu",
        "maryland",
        "ojota",
        "gbagada",
    ),
    "abuja": (
        "apo",
        "lokogoma",
        "gwarinpa",
        "wuse",
        "garki",
        "nyanya",
        "karu",
        "maitama",
        "asokoro",
        "galadimawa",
        "lugbe",
        "kaura",
        "jabi",
        "utako",
        "gudu",
        "wuye",
        "durumi",
        "kabusa",
        "city centre",
        "central area",
        "kubwa",
        "dutse",
        "usuma",
    ),
    "kano": ("ungogo", "fagge", "nassarawa", "sabon gari", "kumbotso", "tarauni", "gwale", "dala"),
    "ibadan": (
        "bodija",
        "mokola",
        "dugbe",
        "challenge",
        "olopomewa",
        "agbowo",
        "sango",
        "ring road",
        "molete",
        "bashorun",
        "agodi",
        "eleyele",
        "agugu",
        "apata",
        "university of ibadan",
        "jericho",
    ),
    "port_harcourt": (
        "trans amadi",
        "diobu",
        "old gra",
        "rumuokoro",
        "rumuola",
        "eneka",
        "woji",
        "rumuomasi",
        "rumuoji eneka",
        "rumunduru",
        "mgbu minkpiti",
        "eagle island",
        "orogbum",
        "alakahia",
        "choba",
        "township vi",
        "rumuwoji ii",
        "rumuwoji iii",
    ),
}
# Win PAL when the cap would otherwise keep Wuse II and drop Apo.
MUST_SHOW = {
    "lagos": (
        "ikoyi",
        "falomo",
        "sangotedo",
        "victoria island",
        "lekki",
        "ajah",
        "apapa",
        "yaba",
        "surulere",
        "obalende",
        "mushin",
        "shomolu",
        "bariga",
        "eko atlantic",
        "tarkwa bay",
        "abraham adesanya",
        "ilado",
        "oko agbo",
        "ijora",
    ),
    "abuja": (
        "apo",
        "lokogoma",
        "nyanya",
        "karu",
        "gwarinpa",
        "wuse",
        "garki",
        "asokoro",
        "maitama",
        "lugbe",
        "kabusa",
        "kubwa",
        "dutse",
        "usuma",
    ),
    "kano": ("ungogo", "fagge", "nassarawa", "sabon gari", "kumbotso", "tarauni", "gwale", "dala"),
    "ibadan": (
        "bodija",
        "mokola",
        "dugbe",
        "challenge",
        "olopomewa",
        "agbowo",
        "sango",
        "molete",
        "bashorun",
        "agodi",
        "eleyele",
        "agugu",
        "apata",
    ),
    "port_harcourt": (
        "trans amadi",
        "diobu",
        "old gra",
        "rumuokoro",
        "eneka",
        "woji",
        "rumuomasi",
        "rumuoji eneka",
        "rumunduru",
        "mgbu minkpiti",
        "eagle island",
        "orogbum",
        "alakahia",
        "choba",
        "township vi",
        "rumuwoji ii",
        "rumuwoji iii",
    ),
}


def _cache_path(slug: str) -> Path:
    return DATA_RAW / f"{slug}_osm_places.geojson"


def _folded(name: object) -> str:
    key = re.sub(r"\s+", " ", str(name or "").casefold().strip())
    return re.sub(r"\s+district$", "", key)


def _canonical_pin(slug: str, name: object) -> str | None:
    key = _folded(name)
    if not key:
        return None
    for pin in PINNED.get(slug, ()):
        p = pin.casefold()
        if key == p:
            return p
        if re.fullmatch(rf"{re.escape(p)}(?:\s+(?:ii|iii|iv|[2-9]))?", key):
            return p
    return None


def _drop_generic(city: City, name: str) -> bool:
    key = _folded(name)
    if not key or len(key) < 3:
        return True
    if key in {city.name.casefold(), city.state.casefold(), "nigeria", "fct", "abuja municipal"}:
        return True
    first = key.split()[0]
    if first in FOREIGN_PLACES and not key.startswith(city.name.casefold()):
        return True
    return False


def _keep_row(slug: str, name: str, place: str) -> bool:
    if _drop_generic(CITIES[slug], name):
        return False
    pin = _canonical_pin(slug, name)
    if NOISE.search(name) and not pin:
        return False
    if NOISE.search(name) and pin and _folded(name) != pin:
        return False
    if RESIDENTIAL_NOISE.search(name) and not pin:
        return False
    if re.search(r"\s+[A-Z]\d{0,2}$", name) and not pin:
        return False
    if slug == "kano" and re.match(r"^(?:unguwar|tudun|layin)\b", name, re.I) and not pin:
        return False
    if place in CORE_TYPES:
        return True
    if pin and place in PLACE_PRIORITY:
        return True
    if place == "residential" and not RESIDENTIAL_NOISE.search(name) and len(name.split()) <= 4:
        return True
    return False


def load_raw_places(city: City, *, refresh: bool = False) -> gpd.GeoDataFrame:
    cache = _cache_path(city.slug)
    if cache.exists() and not refresh:
        return gpd.read_file(cache)
    try:
        gdf = fetch_districts(city)
    except Exception as exc:
        print(f"{city.slug} district fetch failed: {exc}", flush=True)
        gdf = gpd.GeoDataFrame(columns=["osm_id", "place", "name", "geometry"], crs=4326)
    have = _have_pins(gdf, city.slug) if not gdf.empty else set()
    missing = tuple(p for p in PINNED.get(city.slug, ()) if p.casefold() not in have)
    if missing:
        try:
            extra = fetch_named(city, missing)
        except Exception as exc:
            print(f"{city.slug} named fetch failed: {exc}", flush=True)
            extra = None
        if extra is not None and not extra.empty:
            gdf = (
                gpd.GeoDataFrame(pd.concat([gdf, extra], ignore_index=True), crs=4326)
                if not gdf.empty
                else extra
            )
    if not gdf.empty:
        gdf.to_file(cache, driver="GeoJSON")
    return gdf


def tidy_places(city: City, raw: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if raw.empty:
        return raw
    gdf = raw.to_crs(4326).copy()
    gdf["place"] = gdf["place"].fillna("residential").astype(str)
    gdf["name"] = gdf["name"].map(tidy_label)
    gdf["name"] = gdf["name"].str.replace(r"\s+District$", "", regex=True, flags=re.I)
    gdf["name"] = [
        str(n).split(",")[-1].strip()
        if "," in str(n) and _canonical_pin(city.slug, str(n).split(",")[-1])
        else n
        for n in gdf["name"]
    ]
    keep = [
        _keep_row(city.slug, str(n), p)
        for n, p in zip(gdf["name"], gdf["place"])
    ]
    gdf = gdf[keep]
    if gdf.empty:
        return gdf
    gdf["rank"] = gdf["place"].map(PLACE_PRIORITY).fillna(1).astype(int)
    gdf["pinned"] = gdf["name"].map(lambda n: int(_canonical_pin(city.slug, str(n)) is not None))
    gdf["key"] = gdf["name"].str.casefold()
    gdf = gdf.sort_values(["pinned", "rank"], ascending=False).drop_duplicates("key")
    have = set(gdf["name"].str.casefold())
    drop_ii = [
        bool(re.search(r"\s+II$", str(n))) and re.sub(r"\s+II$", "", str(n)).casefold() in have
        for n in gdf["name"]
    ]
    gdf = gdf[[not x for x in drop_ii]]
    must = set(MUST_SHOW.get(city.slug, ()))
    gdf["priority"] = [
        10 if _folded(n) in must else (8 if p else 4)
        for n, p in zip(gdf["name"], gdf["pinned"])
    ]
    return gdf.drop(columns=["key"]).reset_index(drop=True)


def clip_to_boundary(places: gpd.GeoDataFrame, slug: str) -> gpd.GeoDataFrame:
    path = DATA_PROCESSED / f"{slug}_study_boundary.gpkg"
    if places.empty or not path.exists():
        return places
    bound = gpd.read_file(path).to_crs(4326)
    union = bound.union_all()
    return places[places.geometry.within(union) | places.geometry.intersects(union)].copy()


def _have_pins(places: gpd.GeoDataFrame, slug: str) -> set[str]:
    if places.empty:
        return set()
    found = set()
    for name in places["name"].astype(str):
        pin = _canonical_pin(slug, name)
        if pin:
            found.add(pin)
    return found


def fill_missing_pins(city: City, places: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """GRID3 settlement points for pinned names OSM did not tag as a district."""
    missing = [p for p in PINNED.get(city.slug, ()) if p.casefold() not in _have_pins(places, city.slug)]
    missing = [p for p in missing if p.casefold() not in HARD_PINS.get(city.slug, {})]
    if not missing:
        return places
    try:
        pts = settlement_points(city)
    except FileNotFoundError:
        return places
    if pts.empty or "set_name" not in pts.columns:
        return places
    rows = []
    names = pts["set_name"].astype(str).map(tidy_label)
    folded = names.str.casefold()
    bound_path = DATA_PROCESSED / f"{city.slug}_study_boundary.gpkg"
    union = _plate_mask(city.slug)
    if union is None and bound_path.exists():
        union = gpd.read_file(bound_path).to_crs(4326).union_all()
    for pin in missing:
        hit = pts[folded == pin.casefold()]
        if hit.empty:
            hit = pts[folded.str.startswith(pin.casefold() + " ")]
        if hit.empty:
            continue
        geom = None
        for g in hit.geometry:
            if union is None or g.within(union) or g.intersects(union):
                geom = g
                break
        if geom is None:
            continue
        rows.append(
            {
                "osm_id": None,
                "place": "locality",
                "name": tidy_label(pin),
                "rank": 8,
                "pinned": 1,
                "priority": 10 if pin.casefold() in MUST_SHOW.get(city.slug, ()) else 8,
                "geometry": geom,
            }
        )
    if not rows:
        return places
    extra = gpd.GeoDataFrame(rows, crs=pts.crs).to_crs(4326)
    extra = clip_to_boundary(extra, city.slug)
    if extra.empty:
        return places
    if places.empty:
        return extra
    return gpd.GeoDataFrame(pd.concat([places, extra], ignore_index=True), crs=4326)


def _label_point(geom):
    """Centre of a polygon if it lies inside; otherwise a point on the surface."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Point":
        return geom
    if geom.geom_type == "MultiPoint":
        return geom.representative_point()
    centre = geom.centroid
    try:
        if centre.within(geom):
            return centre
    except Exception:
        pass
    try:
        return nearest_points(centre, geom)[1]
    except Exception:
        return geom.representative_point()


def _admin_sources(city: City) -> list[gpd.GeoDataFrame]:
    sources: list[gpd.GeoDataFrame] = []
    for path, field in (
        (DATA_PROCESSED / f"{city.slug}_metro_lgas.gpkg", "shapeName"),
        (DATA_PROCESSED / f"{city.slug}_wards.gpkg", "locator"),
    ):
        if not path.exists():
            continue
        gdf = gpd.read_file(path).to_crs(4326)
        if gdf.empty or field not in gdf.columns:
            continue
        gdf = gdf.copy()
        gdf["_label"] = gdf[field].astype(str).map(tidy_label)
        gdf["_key"] = gdf["_label"].str.casefold()
        sources.append(gdf)
    return sources


def _match_admin(city: City, name: str, sources: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame | None:
    key = _folded(name)
    pin = _canonical_pin(city.slug, name)
    for gdf in sources:
        exact = gdf[gdf["_key"] == key]
        if exact.empty and pin and pin != key:
            exact = gdf[gdf["_key"] == pin]
        if not exact.empty:
            return exact
    if not pin:
        return None
    for gdf in sources:
        loose = gdf[gdf["_key"].str.contains(rf"\b{re.escape(pin)}\b", na=False)]
        loose = loose[
            [
                _canonical_pin(city.slug, gdf.loc[i, "_label"]) in {None, pin}
                for i in loose.index
            ]
        ]
        if not loose.empty:
            return loose
    return None


def _fixed_pin_keys(slug: str) -> set[str]:
    keys = {n.casefold() for n in STAY_ON_FAR.get(slug, ())}
    keys |= {n.casefold() for n in HARD_PINS.get(slug, {})}
    return keys


def reanchor_to_polygons(city: City, places: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Move each name onto the centre of the LGA or ward polygon it names."""
    if places.empty:
        return places
    sources = _admin_sources(city)
    if not sources:
        return places
    skip = _fixed_pin_keys(city.slug)
    geoms = list(places.geometry)
    for i, name in enumerate(places["name"].astype(str)):
        key = _folded(name)
        pin = _canonical_pin(city.slug, name)
        if key in skip or (pin and pin in skip):
            continue
        hit = _match_admin(city, name, sources)
        if hit is None or hit.empty:
            continue
        pt = _label_point(hit.geometry.union_all())
        if pt is not None:
            geoms[i] = pt
    out = places.copy()
    out.geometry = geoms
    return out


GREEN_PT = 10.0
FAR_PT = 15.0
NUMBERED_WARD = re.compile(r"^(?:ph|ward)\s*\d+$", re.I)
GREEN_FILL_N = {"kano": 8, "ibadan": 6, "port_harcourt": 8, "abuja": 4, "lagos": 8}
FAR_FILL_N = {"kano": 8, "ibadan": 5, "port_harcourt": 8, "abuja": 8, "lagos": 6}
GREEN_MIN_SEP_M = {"kano": 500, "ibadan": 450, "port_harcourt": 500, "abuja": 500, "lagos": 500}
FAR_MIN_SEP_M = {"kano": 800, "ibadan": 650, "port_harcourt": 750, "abuja": 700, "lagos": 800}
# Keep these on the yellow/red mass; a green pull would slide them onto Apapa / VI.
STAY_ON_FAR = {
    "lagos": (
        "abraham adesanya",
        "tarkwa bay",
        "eko atlantic",
        "ijora",
        "ilado",
        "oko agbo",
    ),
}
# Pins with no OSM district, or whose GRID3 namesake sits off the plate.
HARD_PINS = {
    "lagos": {
        "eko atlantic": (3.4150, 6.4200),  # VI south shore, inside Eti-Osa
        "ilado": (3.36235, 6.41802),  # Ilado–Tomaro island, on the seven-LGA clip
        "oko agbo": (3.38109, 6.40882),  # Abagbo / Light House, creek south of Apapa
        "abraham adesanya": (3.37814, 6.42238),  # Apapa harbour bulge, not Lekki namesake
    },
    "port_harcourt": {
        "township vi": (6.99397, 4.79764),
        "rumuwoji ii": (6.99353, 4.79250),
        "rumuwoji iii": (6.98949, 4.79074),
    },
}


def _plate_mask(slug: str):
    if slug == "abuja":
        path = DATA_PROCESSED / "abuja_wards.gpkg"
        if not path.exists():
            return None
        gdf = gpd.read_file(path).to_crs(4326)
        return gdf[gdf["locator"].isin(ABUJA_PLATE_WARDS)].geometry.union_all()
    if slug == "lagos":
        path = DATA_PROCESSED / "lagos_metro_lgas.gpkg"
        if not path.exists():
            return None
        gdf = gpd.read_file(path).to_crs(4326)
        return gdf[gdf["shapeName"].isin(LAGOS_PLATE_LGAS)].geometry.union_all()
    path = DATA_PROCESSED / f"{slug}_study_boundary.gpkg"
    if not path.exists():
        return None
    return gpd.read_file(path).to_crs(4326).geometry.union_all()


def _hex_band(city: City, *, lo: float | None, hi: float | None) -> gpd.GeoDataFrame:
    path = DATA_PROCESSED / f"{city.slug}_hexes.gpkg"
    if not path.exists():
        return gpd.GeoDataFrame(columns=["pop", "PT_k", "geometry"], crs=4326)
    hexes = gpd.read_file(path).to_crs(4326)
    band = hexes
    if lo is not None:
        band = band[band["PT_k"] > lo]
    if hi is not None:
        band = band[band["PT_k"] <= hi]
    band = band.copy()
    mask = _plate_mask(city.slug)
    if mask is not None and not band.empty:
        band = band[band.geometry.intersects(mask)].copy()
    if "pop" not in band.columns:
        band["pop"] = 1.0
    return band


def _band_label_point(gdf: gpd.GeoDataFrame):
    """Centre of the largest patch in the band, always on a hex."""
    if gdf.empty:
        return None
    union = gdf.geometry.union_all()
    if union is None or union.is_empty:
        return None
    if union.geom_type == "MultiPolygon" and "pop" in gdf.columns:
        parts = list(union.geoms)
        union = max(parts, key=lambda part: float(gdf[gdf.intersects(part)]["pop"].sum()))
    return _label_point(union)


def _min_dist_m(pt: Point, others: gpd.GeoSeries, epsg: int) -> float:
    if others is None or len(others) == 0:
        return 1e9
    here = gpd.GeoSeries([pt], crs=4326).to_crs(epsg).iloc[0]
    there = gpd.GeoSeries(others, crs=4326).to_crs(epsg)
    return float(there.distance(here).min())


def _skip_green_ward(slug: str, name: str) -> bool:
    if NUMBERED_WARD.match(name.strip()):
        return True
    if re.search(r"\s+[A-Z]\d{1,2}$", name):
        return True
    if slug == "kano" and re.match(r"^(?:unguwar|tudun|layin|unguwa)\b", name, re.I):
        return True
    if slug == "port_harcourt" and re.match(r"^ph\s*\d+", name, re.I):
        return True
    return False


def _fill_band(
    city: City,
    places: gpd.GeoDataFrame,
    band: gpd.GeoDataFrame,
    *,
    take_n: int,
    min_sep: float,
    min_hex: int,
    min_pop: float,
) -> gpd.GeoDataFrame:
    """Add ward names on unlabeled patches of one colour band."""
    if band.empty or take_n <= 0:
        return places
    wards_path = DATA_PROCESSED / f"{city.slug}_wards.gpkg"
    if not wards_path.exists():
        return places
    wards = gpd.read_file(wards_path).to_crs(4326)
    mask = _plate_mask(city.slug)
    if mask is not None:
        wards = wards[wards.geometry.intersects(mask)].copy()
    if wards.empty:
        return places
    cents = band.copy()
    cents.geometry = cents.geometry.centroid
    joined = gpd.sjoin(cents, wards[["locator", "geometry"]], predicate="within", how="left")
    stats = (
        joined.dropna(subset=["locator"])
        .groupby("locator")
        .agg(n=("PT_k", "size"), pop=("pop", "sum"))
        .sort_values(["pop", "n"], ascending=False)
    )
    have = {_folded(n) for n in places["name"].astype(str)} if not places.empty else set()
    if not places.empty:
        have |= _have_pins(places, city.slug)
    pts = list(places.geometry) if not places.empty else []
    rows = []
    for loc, row in stats.iterrows():
        if len(rows) >= take_n:
            break
        name = tidy_label(loc)
        if _skip_green_ward(city.slug, name):
            continue
        if _folded(name) in have:
            continue
        if any(_folded(part) in have for part in re.split(r"[–/-]", name) if part.strip()):
            continue
        if int(row["n"]) < min_hex and float(row["pop"]) < min_pop:
            continue
        chunk = joined[joined["locator"] == loc]
        if chunk.empty:
            continue
        chunk_hex = band.loc[band.index.intersection(chunk.index)]
        pt = _band_label_point(chunk_hex if not chunk_hex.empty else chunk)
        if pt is None:
            continue
        if pts and _min_dist_m(pt, gpd.GeoSeries(pts, crs=4326), city.utm_epsg) < min_sep:
            continue
        pts.append(pt)
        have.add(_folded(name))
        rows.append(
            {
                "name": name,
                "place": "ward",
                "rank": 10,
                "pinned": 1,
                "priority": 10,
                "osm_id": None,
                "geometry": pt,
            }
        )
    if not rows:
        return places
    extra = gpd.GeoDataFrame(rows, crs=4326)
    if places.empty:
        return extra
    return gpd.GeoDataFrame(pd.concat([places, extra], ignore_index=True), crs=4326)


def label_colour_cores(city: City, places: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Name the green cores and any large unlabeled yellow/red gaps."""
    green = _hex_band(city, lo=None, hi=GREEN_PT)
    far = _hex_band(city, lo=FAR_PT, hi=None)
    empty_cols = ["name", "place", "rank", "pinned", "priority", "osm_id", "geometry"]
    out = (
        places.copy()
        if not places.empty
        else gpd.GeoDataFrame(columns=empty_cols, crs=4326)
    )
    sources = _admin_sources(city)
    if not out.empty and not green.empty:
        geoms = list(out.geometry)
        prios = list(out["priority"]) if "priority" in out.columns else [8] * len(out)
        stay_far = {n.casefold() for n in STAY_ON_FAR.get(city.slug, ())}
        for i, name in enumerate(out["name"].astype(str)):
            if _folded(name) in stay_far:
                continue
            hit = _match_admin(city, name, sources) if sources else None
            if hit is not None and not hit.empty:
                nearby = green[green.geometry.intersects(hit.geometry.union_all())]
            else:
                nearby = green[green.geometry.intersects(geoms[i].buffer(0.002))]
            if nearby.empty:
                continue
            pt = _band_label_point(nearby)
            if pt is None:
                continue
            geoms[i] = pt
            prios[i] = max(int(prios[i] or 0), 10)
        out = out.copy()
        out.geometry = geoms
        out["priority"] = prios
    out = _fill_band(
        city,
        out,
        green,
        take_n=GREEN_FILL_N.get(city.slug, 6),
        min_sep=GREEN_MIN_SEP_M.get(city.slug, 500),
        min_hex=5,
        min_pop=8000,
    )
    out = _fill_band(
        city,
        out,
        far,
        take_n=FAR_FILL_N.get(city.slug, 6),
        min_sep=FAR_MIN_SEP_M.get(city.slug, 750),
        min_hex=18,
        min_pop=15000,
    )
    return out


def fill_missing_from_admin(city: City, places: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ward or LGA representative points when OSM and GRID3 both lack a pin."""
    missing = [p for p in PINNED.get(city.slug, ()) if p.casefold() not in _have_pins(places, city.slug)]
    missing = [p for p in missing if p.casefold() not in HARD_PINS.get(city.slug, {})]
    if not missing:
        return places
    sources = (
        (DATA_PROCESSED / f"{city.slug}_wards.gpkg", "locator"),
        (DATA_PROCESSED / f"{city.slug}_metro_lgas.gpkg", "shapeName"),
    )
    rows = []
    still = list(missing)
    for path, field in sources:
        if not still or not path.exists():
            continue
        gdf = gpd.read_file(path).to_crs(4326)
        if gdf.empty or field not in gdf.columns:
            continue
        labels = gdf[field].astype(str).map(tidy_label)
        folded = labels.str.casefold()
        kept = []
        for pin in still:
            hit = gdf[folded == pin]
            if hit.empty:
                loose = gdf[folded.str.contains(rf"\b{re.escape(pin)}\b", na=False)]
                hit = loose[
                    [
                        _canonical_pin(city.slug, labels.loc[i]) in {None, pin}
                        for i in loose.index
                    ]
                ]
            if hit.empty:
                kept.append(pin)
                continue
            hit = hit.assign(_n=labels.loc[hit.index].str.len()).sort_values("_n")
            geom = hit.geometry.iloc[0]
            if geom is None or geom.is_empty:
                kept.append(pin)
                continue
            pt = _label_point(geom)
            rows.append(
                {
                    "osm_id": None,
                    "place": "locality",
                    "name": labels.loc[hit.index[0]],
                    "rank": 8,
                    "pinned": 1,
                    "priority": 10 if pin.casefold() in MUST_SHOW.get(city.slug, ()) else 8,
                    "geometry": pt,
                }
            )
        still = kept
    if not rows:
        return places
    extra = gpd.GeoDataFrame(rows, crs=4326)
    extra = clip_to_boundary(extra, city.slug)
    if extra.empty:
        return places
    if places.empty:
        return extra
    return gpd.GeoDataFrame(pd.concat([places, extra], ignore_index=True), crs=4326)


def fill_hard_pins(city: City, places: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Force coordinates for names OSM, GRID3 or the ward layer would misplace."""
    hard = HARD_PINS.get(city.slug, {})
    if not hard:
        return places
    empty_cols = ["osm_id", "place", "name", "rank", "pinned", "priority", "geometry"]
    out = (
        places.copy()
        if not places.empty
        else gpd.GeoDataFrame(columns=empty_cols, crs=4326)
    )
    if not out.empty:
        geoms = list(out.geometry)
        for i, name in enumerate(out["name"].astype(str)):
            key = _canonical_pin(city.slug, name) or _folded(name)
            xy = hard.get(key)
            if xy:
                geoms[i] = Point(xy[0], xy[1])
        out.geometry = geoms
    have = _have_pins(out, city.slug)
    rows = []
    for pin, xy in hard.items():
        if pin in have:
            continue
        rows.append(
            {
                "osm_id": None,
                "place": "locality",
                "name": tidy_label(pin),
                "rank": 8,
                "pinned": 1,
                "priority": 10 if pin in MUST_SHOW.get(city.slug, ()) else 8,
                "geometry": Point(xy[0], xy[1]),
            }
        )
    if not rows:
        return out
    extra = gpd.GeoDataFrame(rows, crs=4326)
    extra = clip_to_boundary(extra, city.slug)
    if extra.empty:
        return out
    if out.empty:
        return extra
    return gpd.GeoDataFrame(pd.concat([out, extra], ignore_index=True), crs=4326)


def write_city_places(slug: str, *, refresh: bool = False) -> Path:
    city = CITIES[slug]
    raw = load_raw_places(city, refresh=refresh)
    places = tidy_places(city, raw)
    places = clip_to_boundary(places, slug)
    places = fill_missing_pins(city, places)
    places = fill_missing_from_admin(city, places)
    places = fill_hard_pins(city, places)
    places = reanchor_to_polygons(city, places)
    places = label_colour_cores(city, places)
    extra_n = {"abuja": 0, "kano": 0, "lagos": 0, "ibadan": 0, "port_harcourt": 0}.get(slug, 0)
    if not places.empty:
        places["key"] = places["name"].str.casefold()
        places = (
            places.sort_values(["pinned", "priority", "rank"], ascending=False)
            .drop_duplicates("key")
            .drop(columns=["key"])
            .reset_index(drop=True)
        )
        if "pinned" in places.columns:
            pin = places[places["pinned"] == 1]
            rest = places[places["pinned"] != 1].sort_values("rank", ascending=False).head(extra_n)
            places = gpd.GeoDataFrame(pd.concat([pin, rest], ignore_index=True), crs=places.crs)
    out = DATA_PROCESSED / f"{slug}_places.gpkg"
    keep = [c for c in ("name", "place", "rank", "pinned", "priority", "osm_id", "geometry") if c in places.columns]
    if places.empty:
        gpd.GeoDataFrame(columns=keep, crs=4326).to_file(out, driver="GPKG")
    else:
        places[keep].to_file(out, driver="GPKG")
    print(f"{slug:<15} {len(places):>4} places  pinned={int(places['pinned'].sum()) if len(places) else 0}")
    return out


if __name__ == "__main__":
    import sys

    slugs = [s for s in sys.argv[1:] if s != "--refresh"]
    refresh = "--refresh" in sys.argv[1:]
    order = ("abuja", "ibadan", "kano", "port_harcourt", "lagos")
    for slug in slugs or [s for s in order if s in CITIES]:
        write_city_places(slug, refresh=refresh)
