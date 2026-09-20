"""GRID3 operational (vaccination) wards clipped to each city's metro LGAs.

ADM3 demarcation under the ADM2 metro boundary. Source file lives under Documents and
is symlinked into data/raw; nothing bulky is committed.

Name quality varies by state and is recorded per feature:

- `named` — Lagos, Kano, Oyo (Ibadan) and FCT carry real ward names.
- `numbered_locator` — Rivers ships placeholders (`Phward 3`, `Obward 1`) in both the
  ward and settlement layers. The locator is borrowed from the GRID3 settlement point
  inside the ward (primary settlement where flagged, else nearest the ward's
  representative point), falling back to OSM place / named residential polygons.

Wards with no settlement or OSM name keep the official number (`PH 7`), so every
feature that ships carries a `locator`. Port Harcourt LGA 6, 12 and 13 take their
INEC names (Township VI, Rumuwoji II, Rumuwoji III). Label on `locator`, never on
raw `wardname`.

No open source (GRID3 operational wards v2/v3, COD-AB ADM3, INEC on HDX,
geoBoundaries) publishes named Rivers ward geometry.

State LGA context (all 23 Rivers LGAs, all 20 Lagos LGAs) comes from COD-AB ADM2.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .cities import ABUJA_SATELLITE_WARDS, CITIES, City
from .gpkg_styles import embed_metro_lga_style, embed_ward_style
from .paths import DATA_PROCESSED, DATA_RAW
from .pipeline import metro_lga_polygons

DOCUMENTS = Path.home() / "Documents"
WARD_SOURCES = (
    DOCUMENTS
    / "Portfolio"
    / "Data"
    / "NGA_Ward_Boundaries_3226275098552792325"
    / "grid3_nga_boundary_vaccwards.shp",
)
SETTLEMENT_SOURCES = (
    DOCUMENTS
    / "Portfolio"
    / "Data"
    / "Settlements_in_Nigeria_-238198433911178935"
    / "grid3_nga_settlementpt.shp",
)
STATE_LGA_SOURCES = (
    DOCUMENTS / "Portfolio" / "Data" / "nga_admin_boundaries.shp" / "nga_admin2.shp",
)
SIDECARS = (".dbf", ".shx", ".prj", ".cpg")

# GRID3 placeholders look like "Phward 3", "Obward 12", "Aktward 1".
PLACEHOLDER = re.compile(r"^[a-z]{2,6}ward\s*(\d+)$", re.IGNORECASE)
# Some settlement points inherit the placeholder as their own name ("Phward 10",
# "Phaward 7", bare "Phward") — useless as a locator.
PLACEHOLDER_LOOSE = re.compile(r"^[a-z]{2,6}ward\s*\d*$", re.IGNORECASE)
# Vaccination-file leftovers: "Oritamerin / Ward 12 SW9 2"
WARD_CODE_TAIL = re.compile(r"\s*/\s*Ward\s+\d+(?:\s+[A-Z]{1,4}\d+)*(?:\s+\d+)?\s*$", re.I)
ROMAN = re.compile(r"^[IVXLCDM]+$", re.I)
SMALL_WORDS = {"of", "and", "the", "de", "da"}

# Short LGA tokens for duplicate locators and numbered Rivers wards.
LGA_SHORT = {
    "Amuwo Odofin": "Amuwo",
    "Ibadan North": "North",
    "Ibadan North East": "NE",
    "Ibadan North West": "NW",
    "Ibadan South East": "SE",
    "Ibadan South West": "SW",
    "Kano Municipal": "Municipal",
    "Municipal Area Council": "AMAC",
    "Obio/Akpor": "Obio",
    "Port-Harcourt": "PH",
    "Port Harcourt": "PH",
}

# One-off GRID3 spellings that read badly on a map.
RENAMES = {
    "city center 1": "City Centre",
    "city centre 1": "City Centre",
    "garki 1": "Garki",
    "nyanya 1": "Nyanya",
    "g r a": "GRA",
    "old gra": "Old GRA",
}

# INEC ward names for Rivers placeholders that GRID3 ships as Phward N.
# Port Harcourt LGA: 6 = Township VI, 12 = Rumuwoji (Two), 13 = Rumuwoji (Three).
INEC_WARD_NAMES = {
    ("port-harcourt", 6): "Township VI",
    ("port-harcourt", 12): "Rumuwoji II",
    ("port-harcourt", 13): "Rumuwoji III",
}


def short_lga(lganame: object) -> str:
    raw = re.sub(r"\s+", " ", str(lganame or "").strip())
    return LGA_SHORT.get(raw, raw)


def _title_token(tok: str, *, first: bool) -> str:
    if ROMAN.match(tok) and 1 <= len(tok) <= 6:
        return tok.upper()
    if tok.upper() == "GRA":
        return "GRA"
    lower = tok.lower()
    if lower in SMALL_WORDS and not first:
        return lower
    if tok.isupper() or tok.islower():
        return "-".join(part.capitalize() for part in tok.split("-"))
    return tok


def tidy_label(raw: object) -> str:
    """Whitespace, vaccination-code tails, GRA, and compound-name slashes."""
    s = unicodedata.normalize("NFKC", str(raw or "")).replace("\u00a0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    s = WARD_CODE_TAIL.sub("", s).strip(" /")
    s = re.sub(r"\bG\s*R\s*A\b", "GRA", s, flags=re.I)
    s = re.sub(r"\s*/\s*", "–", s)
    key = s.casefold()
    if key in RENAMES:
        return RENAMES[key]
    parts = [_title_token(p, first=i == 0) for i, p in enumerate(s.split(" "))]
    return " ".join(parts).strip(" –")


def numbered_label(lganame: object, number: int) -> str:
    return f"{short_lga(lganame)} {int(number)}"


def clean_ward_name(wardname: object, lganame: object) -> tuple[str, str]:
    """Return (label, name_quality) for one ward."""
    raw = str(wardname or "").strip()
    match = PLACEHOLDER.match(raw)
    if match:
        number = int(match.group(1))
        lga_key = re.sub(r"\s+", "-", str(lganame or "").strip()).casefold()
        alias = INEC_WARD_NAMES.get((lga_key, number))
        if alias:
            return alias, "named"
        return numbered_label(lganame, number), "numbered"
    return tidy_label(raw), "named"


def disambiguate_locators(wards: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Qualify names that repeat inside the city: Baruwa (Alimosho), Baruwa (Surulere)."""
    wards = wards.copy()
    key = wards["locator"].astype(str).str.casefold()
    counts = key.value_counts()
    dups = set(counts[counts > 1].index)
    if not dups:
        return wards

    def _label(row) -> str:
        name = str(row["locator"])
        if name.casefold() not in dups:
            return name
        return f"{name} ({short_lga(row['lganame'])})"

    wards["locator"] = wards.apply(_label, axis=1)
    return wards


def _link(sources: tuple[Path, ...], label: str) -> Path:
    src = next((p for p in sources if p.exists()), None)
    if src is None:
        raise FileNotFoundError(f"{label} not found under Documents")
    dest = DATA_RAW / src.name
    if not dest.exists():
        dest.symlink_to(src)
    for ext in SIDECARS:
        side, side_dest = src.with_suffix(ext), dest.with_suffix(ext)
        if side.exists() and not side_dest.exists():
            side_dest.symlink_to(side)
    return dest


def link_ward_source() -> Path:
    return _link(WARD_SOURCES, "GRID3 ward boundaries")


def link_settlement_source() -> Path:
    return _link(SETTLEMENT_SOURCES, "GRID3 settlement points")


def settlement_points(city: City) -> gpd.GeoDataFrame:
    west, south, east, north = city.bbox
    pad = 0.05
    pts = gpd.read_file(
        link_settlement_source(), bbox=(west - pad, south - pad, east + pad, north + pad)
    )
    if pts.crs is None:
        pts = pts.set_crs(4326)
    return pts.to_crs(4326)


def add_locators(wards: gpd.GeoDataFrame, city: City) -> gpd.GeoDataFrame:
    """Borrow a settlement name for wards whose own name is a placeholder.

    Settlement points are matched by containment; the primary settlement wins, else
    the one nearest the ward's representative point.
    """
    wards = wards.copy()
    wards["locator"] = None
    wards["locator_source"] = None
    wards["n_settlements"] = 0
    if not (wards["name_quality"] == "numbered").any():
        return wards

    pts = settlement_points(city)
    if pts.empty or "set_name" not in pts.columns:
        return wards

    utm = wards.estimate_utm_crs()
    pts_utm = pts.to_crs(utm)
    usable = pts["set_name"].astype(str).str.strip()
    usable = usable.ne("") & ~usable.str.match(PLACEHOLDER_LOOSE)

    for idx, ward in wards.iterrows():
        if ward["name_quality"] != "numbered":
            continue
        inside = pts[pts.geometry.within(ward.geometry)]
        wards.at[idx, "n_settlements"] = int(len(inside))
        candidates = inside[usable.loc[inside.index]]
        if candidates.empty:
            continue
        if "is_primary" in candidates.columns:
            primary = candidates[candidates["is_primary"].astype(str).str.lower() == "yes"]
            if len(primary):
                candidates = primary
        anchor = (
            gpd.GeoSeries([ward.geometry], crs=wards.crs)
            .to_crs(utm)
            .representative_point()
            .iloc[0]
        )
        nearest = pts_utm.loc[candidates.index].distance(anchor).idxmin()
        wards.at[idx, "locator"] = tidy_label(pts.at[nearest, "set_name"])
        wards.at[idx, "locator_source"] = "grid3_settlement"

    return _osm_place_locators(wards, city, utm)


def _osm_place_locators(wards: gpd.GeoDataFrame, city: City, utm) -> gpd.GeoDataFrame:
    """Second pass for wards GRID3 could not name — dense cores are well mapped in OSM."""
    missing = (wards["name_quality"] == "numbered") & wards["locator"].isna()
    if not missing.any():
        return wards
    try:
        from .overpass import fetch_places

        places = fetch_places(city)
    except Exception as exc:
        print(f"OSM place lookup skipped for {city.name}: {exc}")
        return wards
    if places.empty:
        return wards

    places_utm = places.to_crs(utm)
    rank = {
        p: i
        for i, p in enumerate(
            ("suburb", "quarter", "neighbourhood", "town", "village", "hamlet", "residential", "city")
        )
    }
    for idx in wards.index[missing]:
        geom = wards.at[idx, "geometry"]
        inside = places[places.geometry.intersects(geom)]
        anchor = gpd.GeoSeries([geom], crs=wards.crs).to_crs(utm).representative_point().iloc[0]
        dist = places_utm.distance(anchor)
        if inside.empty:
            near = dist[dist <= 180.0]
            if near.empty:
                continue
            pick = near.idxmin()
            name = tidy_label(places.at[pick, "name"])
            if not name or PLACEHOLDER_LOOSE.match(name):
                continue
            wards.at[idx, "locator"] = name
            wards.at[idx, "locator_source"] = "osm_near"
            continue
        order = inside.assign(
            _rank=inside["place"].map(rank).fillna(99),
            _dist=dist.loc[inside.index],
        ).sort_values(["_rank", "_dist"])
        name = tidy_label(order.iloc[0]["name"])
        if not name or PLACEHOLDER_LOOSE.match(name):
            continue
        wards.at[idx, "locator"] = name
        wards.at[idx, "locator_source"] = "osm_place"
    return wards


def ward_polygons(city: City) -> gpd.GeoDataFrame:
    """Wards whose centroid falls inside the city's metro LGA union."""
    path = link_ward_source()
    west, south, east, north = city.bbox
    pad = 0.05
    wards = gpd.read_file(path, bbox=(west - pad, south - pad, east + pad, north + pad))
    if wards.crs is None:
        wards = wards.set_crs(4326)
    wards = wards.to_crs(4326)
    metro = metro_lga_polygons(city).to_crs(4326)
    union = metro.union_all()
    inside = wards[wards.geometry.representative_point().within(union)].copy()
    if city.slug == "abuja":
        extra = wards[wards["wardname"].isin(ABUJA_SATELLITE_WARDS)]
        if not extra.empty:
            inside = pd.concat([inside, extra], ignore_index=True)
            if "wardcode" in inside.columns:
                inside = inside.drop_duplicates(subset=["wardcode"])
    if inside.empty:
        raise RuntimeError(f"No wards resolved inside {city.name} metro LGAs")
    cleaned = [clean_ward_name(w, l) for w, l in zip(inside["wardname"], inside["lganame"])]
    inside["ward_official"] = [c[0] for c in cleaned]
    inside["name_quality"] = [c[1] for c in cleaned]
    inside = add_locators(inside, city)

    names, quality = [], []
    for _, row in inside.iterrows():
        if row["name_quality"] != "numbered":
            names.append(tidy_label(row["ward_official"]))
            quality.append("named")
        elif row["locator"]:
            names.append(tidy_label(row["locator"]))
            quality.append("numbered_locator")
        else:
            names.append(row["ward_official"])
            quality.append("numbered")
    inside["locator"] = names
    inside["name_quality"] = quality
    inside["locator_source"] = inside["locator_source"].fillna("grid3_ward")
    inside = disambiguate_locators(inside)
    numbered = int((inside["name_quality"] == "numbered").sum())
    if numbered:
        print(f"  {city.name}: {numbered} ward(s) kept on official numbers")

    keep = [
        "locator",
        "name_quality",
        "locator_source",
        "ward_official",
        "n_settlements",
        "wardname",
        "wardcode",
        "lganame",
        "lgacode",
        "statename",
        "urban",
        "geometry",
    ]
    return inside[[c for c in keep if c in inside.columns]].reset_index(drop=True)


def state_lga_polygons(city: City) -> gpd.GeoDataFrame:
    """Every LGA in the city's state (COD-AB ADM2), not just the metro subset."""
    path = _link(STATE_LGA_SOURCES, "COD-AB ADM2 LGA boundaries")
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    match = gdf["adm1_name"].astype(str).str.casefold() == city.state.casefold()
    state = gdf[match].copy()
    if state.empty:
        raise RuntimeError(f"No LGAs found for state {city.state!r}")
    state = state.rename(columns={"adm2_name": "shapeName", "adm1_name": "stateName"})
    keep = ["shapeName", "stateName", "adm2_pcode", "area_sqkm", "geometry"]
    return state[[c for c in keep if c in state.columns]].reset_index(drop=True)


def write_state_lgas(slug: str) -> Path:
    city = CITIES[slug]
    lgas = state_lga_polygons(city)
    out = DATA_PROCESSED / f"{slug}_state_lgas.gpkg"
    lgas.to_file(out, driver="GPKG")
    embed_metro_lga_style(out)
    return out


def write_city_wards(slug: str) -> Path:
    city = CITIES[slug]
    wards = ward_polygons(city)
    out = DATA_PROCESSED / f"{slug}_wards.gpkg"
    wards.to_file(out, driver="GPKG")
    embed_ward_style(out)
    return out


if __name__ == "__main__":
    import sys

    slugs = sys.argv[1:] or list(CITIES)
    for slug in slugs:
        try:
            path = write_city_wards(slug)
            g = gpd.read_file(path)
            quality = g["name_quality"].value_counts().to_dict()
            state = gpd.read_file(write_state_lgas(slug))
            print(
                f"{slug:<15} {len(g):>4} wards {quality} e.g. {g['locator'].iloc[0]!r}"
                f" | state LGAs: {len(state)}"
            )
        except Exception as exc:
            print(f"{slug:<15} skipped: {exc}")
