"""Optional Overpass pull when HDX files are not on disk yet."""

from __future__ import annotations

import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import geopandas as gpd
from shapely.geometry import Point

from .cities import City
from .download import USER_AGENT

# Main instance first: the two mirrors below hang for the full 180 s timeout far more
# often than they answer, so leading with them costs six minutes per city on every miss.
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)


def _query(south: float, west: float, north: float, east: float, amenities: list[str]) -> str:
    ors = "".join(
        f'  nwr["amenity"="{a}"]({south},{west},{north},{east});\n' for a in amenities
    )
    return f"[out:json][timeout:90];\n(\n{ors});\nout center;"


def _count_query(south: float, west: float, north: float, east: float, amenities: list[str]) -> str:
    ors = "".join(
        f'  nwr["amenity"="{a}"]({south},{west},{north},{east});\n' for a in amenities
    )
    return f"[out:json][timeout:90];\n(\n{ors});\nout count;"


def count_amenities(city: City, amenities: list[str]) -> int:
    """Element total over the city bbox. `out count` answers where `out center` 504s."""
    west, south, east, north = city.bbox
    payload = _run(_count_query(south, west, north, east, amenities))
    for el in payload.get("elements", []):
        if el.get("type") == "count":
            return int(el["tags"]["total"])
    return 0


PLACE_RANKS = ("city", "town", "suburb", "quarter", "neighbourhood", "village", "hamlet")
DISTRICT_RANKS = ("suburb", "quarter", "neighbourhood")


def _place_query(south: float, west: float, north: float, east: float, places: tuple[str, ...]) -> str:
    ors = "".join(
        f'  nwr["place"="{p}"]["name"]({south},{west},{north},{east});\n' for p in places
    )
    ors += f'  nwr["landuse"="residential"]["name"]({south},{west},{north},{east});\n'
    return f"[out:json][timeout:120];\n(\n{ors});\nout center;"


def _run(query: str, timeout: int = 90) -> dict:
    body = urlencode({"data": query}).encode()
    last_exc: Exception | None = None
    payload = None
    for url in OVERPASS_ENDPOINTS:
        try:
            req = Request(
                url,
                data=body,
                headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
            )
            with urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode())
            break
        except Exception as exc:
            last_exc = exc
            print(f"Overpass {url} failed: {exc}")
    if payload is None:
        raise last_exc or RuntimeError("Overpass failed")
    return payload


def fetch_districts(city: City) -> gpd.GeoDataFrame:
    """Named OSM districts for plate labels — suburb, quarter, neighbourhood only.

    The full place+residential query is too heavy for Lagos and times out.
    """
    west, south, east, north = city.bbox
    ors = "".join(
        f'  nwr["place"="{p}"]["name"]({south},{west},{north},{east});\n'
        for p in DISTRICT_RANKS
    )
    query = f"[out:json][timeout:45];\n(\n{ors});\nout center;"
    payload = _run(query, timeout=55)
    rows = []
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None or not tags.get("name"):
            continue
        rows.append(
            {
                "osm_id": el.get("id"),
                "place": tags.get("place") or "suburb",
                "name": tags["name"],
                "geometry": Point(lon, lat),
            }
        )
    if not rows:
        return gpd.GeoDataFrame(columns=["osm_id", "place", "name", "geometry"], crs=4326)
    return gpd.GeoDataFrame(rows, crs=4326)


# Names OSM stores as landuse=residential, not place=suburb (Lokogoma).
RESIDENTIAL_PINS = frozenset({"lokogoma"})


def fetch_named(city: City, names: tuple[str, ...]) -> gpd.GeoDataFrame:
    """Pick up pinned names tagged as place=* or, for a few, residential land."""
    if not names:
        return gpd.GeoDataFrame(columns=["osm_id", "place", "name", "geometry"], crs=4326)
    west, south, east, north = city.bbox
    long = [n for n in names if len(n) >= 4]
    pattern = "|".join(re.escape(n) for n in long) if long else "a^"
    residential = [n for n in names if n.casefold() in RESIDENTIAL_PINS]
    res_ors = "".join(
        f'  nwr["name"~"{re.escape(n)}",i]["landuse"="residential"]({south},{west},{north},{east});\n'
        for n in residential
    )
    query = (
        f"[out:json][timeout:45];\n"
        f"(\n"
        f'  nwr["name"~"{pattern}",i]["place"]({south},{west},{north},{east});\n'
        f"{res_ors}"
        f");\nout center;"
    )
    payload = _run(query, timeout=55)
    rows = []
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None or not tags.get("name"):
            continue
        rows.append(
            {
                "osm_id": el.get("id"),
                "place": tags.get("place") or tags.get("landuse") or "locality",
                "name": tags["name"],
                "geometry": Point(lon, lat),
            }
        )
    if not rows:
        return gpd.GeoDataFrame(columns=["osm_id", "place", "name", "geometry"], crs=4326)
    return gpd.GeoDataFrame(rows, crs=4326)


def fetch_places(city: City, places: tuple[str, ...] = PLACE_RANKS) -> gpd.GeoDataFrame:
    """Named OSM place nodes — locators for wards whose official name is a number."""
    west, south, east, north = city.bbox
    payload = _run(_place_query(south, west, north, east, places))
    rows = []
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None or not tags.get("name"):
            continue
        rows.append(
            {
                "osm_id": el.get("id"),
                "place": tags.get("place") or "residential",
                "name": tags["name"],
                "geometry": Point(lon, lat),
            }
        )
    if not rows:
        return gpd.GeoDataFrame(columns=["osm_id", "place", "name", "geometry"], crs=4326)
    return gpd.GeoDataFrame(rows, crs=4326)


def fetch_amenities(city: City, amenities: list[str]) -> gpd.GeoDataFrame:
    west, south, east, north = city.bbox
    payload = _run(_query(south, west, north, east, amenities))

    rows = []
    for el in payload.get("elements", []):
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        rows.append(
            {
                "osm_id": el.get("id"),
                "amenity": (el.get("tags") or {}).get("amenity"),
                "name": (el.get("tags") or {}).get("name"),
                "geometry": Point(lon, lat),
            }
        )
    if not rows:
        return gpd.GeoDataFrame(columns=["osm_id", "amenity", "name", "geometry"], crs=4326)
    return gpd.GeoDataFrame(rows, crs=4326)
