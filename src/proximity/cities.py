"""Five urban centres. Bounding boxes clip; metro LGAs are the operational boundary until GHS UCDB is local."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    slug: str
    name: str
    state: str
    utm_epsg: int
    # west, south, east, north (WGS84)
    bbox: tuple[float, float, float, float]
    metro_lgas: tuple[str, ...]
    atlas_id: int | None = None
    notes: str = ""


# LGA names match geoBoundaries ADM2 `shapeName`. Bboxes drop homonyms (e.g. Nasarawa).
CITIES: dict[str, City] = {
    "lagos": City(
        slug="lagos",
        name="Lagos",
        state="Lagos",
        utm_epsg=32631,
        bbox=(3.05, 6.35, 3.72, 6.72),
        metro_lgas=(
            "Agege",
            "Ajeromi/Ifelodun",
            "Alimosho",
            "Amuwo Odofin",
            "Apapa",
            "Eti Osa",
            "Ifako/Ijaye",
            "Ikeja",
            "Kosofe",
            "Lagos Island",
            "Lagos Mainland",
            "Mushin",
            "Ojo",
            "Oshodi/Isolo",
            "Shomolu",
            "Surulere",
        ),
        atlas_id=4800,
        notes="Sony CSL atlas idcity=4800. Excludes Epe, Ibeju-Lekki, Badagry, Ikorodu.",
    ),
    "kano": City(
        slug="kano",
        name="Kano",
        state="Kano",
        utm_epsg=32632,
        bbox=(8.38, 11.84, 8.73, 12.12),
        metro_lgas=(
            "Dala",
            "Fagge",
            "Gwale",
            "Kano Municipal",
            "Kumbotso",
            "Nassarawa",
            "Tarauni",
            "Ungogo",
        ),
    ),
    "ibadan": City(
        slug="ibadan",
        name="Ibadan",
        state="Oyo",
        utm_epsg=32631,
        bbox=(3.78, 7.28, 4.08, 7.55),
        metro_lgas=(
            "Ibadan North",
            "Ibadan North East",
            "Ibadan North West",
            "Ibadan South East",
            "Ibadan South West",
        ),
    ),
    "abuja": City(
        slug="abuja",
        name="Abuja",
        state="Federal Capital Territory",
        utm_epsg=32632,
        bbox=(7.30, 8.90, 7.58, 9.20),
        metro_lgas=("Municipal Area Council",),
        notes="FCT urban core (not the entire territory).",
    ),
    "port_harcourt": City(
        slug="port_harcourt",
        name="Port Harcourt",
        state="Rivers",
        utm_epsg=32632,
        bbox=(6.90, 4.75, 7.15, 5.05),
        metro_lgas=("Port-Harcourt", "Obio/Akpor"),
    ),
}

# Plate clips (not the analysis boundary). Lagos keeps seven inner LGAs; Abuja keeps seven AMAC wards.
LAGOS_PLATE_LGAS = (
    "Eti Osa",
    "Lagos Island",
    "Apapa",
    "Lagos Mainland",
    "Surulere",
    "Mushin",
    "Shomolu",
)
ABUJA_PLATE_WARDS = (
    "Gwarinpa",
    "Wuse",
    "Nyanya",
    "Karu",
    "City Centre",
    "Garki",
    "Kabusa",
)

WALK_M_PER_MIN = 5000 / 60  # 5 km/h until OSRM
N_DUAL_DEFAULT = 20
N_DUAL_NONSUBSTITUTABLE = 5
HEX_SIDE_M = 200
POP_URBAN_THRESHOLD = 5.0
