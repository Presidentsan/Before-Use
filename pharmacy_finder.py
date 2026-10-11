import math
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from pharmacy_ranker import (
    rank_pharmacy_candidates,
)


NOMINATIM_SEARCH_URL = (
    "https://nominatim.openstreetmap.org/search"
)


OVERPASS_ENDPOINTS = [
    (
        "Kumi Overpass",
        "https://overpass.kumi.systems/api/interpreter",
    ),
    (
        "Main Overpass",
        "https://overpass-api.de/api/interpreter",
    ),
]


HEADERS = {
    "User-Agent": (
        "BeforeUse/0.7 "
        "(consumer medicine safety prototype)"
    ),

    "Accept": (
        "application/json"
    ),
}


GEOCODE_TIMEOUT_SECONDS = 15
OVERPASS_TIMEOUT_SECONDS = 18

NOMINATIM_FALLBACK_TIMEOUT_SECONDS = (
    15
)


def _clean_text(
    value: Any,
) -> Optional[str]:

    if value is None:
        return None

    text = str(
        value
    ).strip()

    return (
        text
        or None
    )


def _safe_float(
    value: Any,
) -> Optional[float]:

    try:

        return (
            None
            if value is None
            else float(
                value
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


def _distance_metres(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> int:

    earth_radius = (
        6_371_000
    )

    phi1 = math.radians(
        lat1
    )

    phi2 = math.radians(
        lat2
    )

    d_phi = math.radians(
        lat2 - lat1
    )

    d_lambda = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(
            d_phi / 2
        ) ** 2

        +
        math.cos(
            phi1
        )
        *
        math.cos(
            phi2
        )
        *
        math.sin(
            d_lambda / 2
        ) ** 2
    )

    c = (
        2
        *
        math.atan2(
            math.sqrt(
                a
            ),
            math.sqrt(
                1 - a
            ),
        )
    )

    return round(
        earth_radius
        *
        c
    )


def geocode_location(
    location_query: str,
) -> Dict[str, Any]:

    query = str(
        location_query
        or ""
    ).strip()

    if not query:

        return {
            "source_ok": False,

            "error": (
                "Enter an area, neighbourhood, "
                "city or landmark."
            ),

            "location": None,
        }

    try:

        response = requests.get(
            NOMINATIM_SEARCH_URL,

            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "ng",
                "addressdetails": 1,
            },

            headers=HEADERS,

            timeout=(
                GEOCODE_TIMEOUT_SECONDS
            ),
        )

        response.raise_for_status()

        rows = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as error:

        return {
            "source_ok": False,
            "error": str(
                error
            ),
            "location": None,
        }

    if not rows:

        return {
            "source_ok": True,
            "error": None,
            "location": None,
        }

    first = rows[0]

    lat = _safe_float(
        first.get(
            "lat"
        )
    )

    lon = _safe_float(
        first.get(
            "lon"
        )
    )

    if (
        lat is None
        or
        lon is None
    ):

        return {
            "source_ok": False,

            "error": (
                "Location service returned "
                "incomplete coordinates."
            ),

            "location": None,
        }

    return {
        "source_ok": True,

        "error": None,

        "location": {
            "query": query,

            "display_name": (
                first.get(
                    "display_name"
                )
            ),

            "lat": lat,

            "lon": lon,
        },
    }


def _address_from_tags(
    tags: Dict[
        str,
        Any,
    ],
) -> Optional[str]:

    full = (
        _clean_text(
            tags.get(
                "addr:full"
            )
        )
    )

    if full:
        return full

    values = [
        _clean_text(
            tags.get(
                "addr:housenumber"
            )
        ),

        _clean_text(
            tags.get(
                "addr:street"
            )
        ),

        _clean_text(
            tags.get(
                "addr:suburb"
            )
            or
            tags.get(
                "addr:district"
            )
        ),

        _clean_text(
            tags.get(
                "addr:city"
            )
            or
            tags.get(
                "addr:town"
            )
        ),

        _clean_text(
            tags.get(
                "addr:state"
            )
        ),
    ]

    parts: List[
        str
    ] = []

    for value in values:

        if (
            value
            and
            value not in parts
        ):

            parts.append(
                value
            )

    return (
        ", ".join(
            parts
        )
        or
        None
    )


def _element_location(
    element: Dict[
        str,
        Any,
    ],
) -> Tuple[
    Optional[float],
    Optional[float],
]:

    lat = _safe_float(
        element.get(
            "lat"
        )
    )

    lon = _safe_float(
        element.get(
            "lon"
        )
    )

    if (
        lat is not None
        and
        lon is not None
    ):

        return (
            lat,
            lon,
        )

    center = (
        element.get(
            "center"
        )
        or {}
    )

    return (
        _safe_float(
            center.get(
                "lat"
            )
        ),

        _safe_float(
            center.get(
                "lon"
            )
        ),
    )


def _build_overpass_query(
    latitude: float,
    longitude: float,
    radius_m: int,
) -> str:

    return f"""
    [out:json][timeout:12];

    nwr
      ["amenity"="pharmacy"]
      (around:{int(radius_m)},{latitude},{longitude});

    out center tags;
    """


def _query_overpass_endpoint(
    endpoint_name: str,
    endpoint_url: str,
    query: str,
) -> Dict[str, Any]:

    try:

        response = requests.post(
            endpoint_url,

            data={
                "data": query
            },

            headers=HEADERS,

            timeout=(
                OVERPASS_TIMEOUT_SECONDS
            ),
        )

        if (
            response.status_code
            in {
                429,
                502,
                503,
                504,
            }
        ):

            return {
                "source_ok": False,

                "source_name": (
                    endpoint_name
                ),

                "elements": [],

                "error": (
                    f"{response.status_code} "
                    f"from {endpoint_name}"
                ),
            }

        response.raise_for_status()

        payload = (
            response.json()
        )

        return {
            "source_ok": True,

            "source_name": (
                endpoint_name
            ),

            "elements": (
                payload.get(
                    "elements"
                )
                or []
            ),

            "error": None,
        }

    except (
        requests.RequestException,
        ValueError,
    ) as error:

        return {
            "source_ok": False,

            "source_name": (
                endpoint_name
            ),

            "elements": [],

            "error": str(
                error
            ),
        }


def _parse_overpass_records(
    elements: List[
        Dict[str, Any]
    ],
    search_lat: float,
    search_lon: float,
    radius_m: int,
    source_name: str,
) -> List[
    Dict[str, Any]
]:

    records = []

    for element in elements:

        tags = (
            element.get(
                "tags"
            )
            or {}
        )

        name = (
            _clean_text(
                tags.get(
                    "name"
                )
                or
                tags.get(
                    "operator"
                )
            )
        )

        if not name:
            continue

        lat, lon = (
            _element_location(
                element
            )
        )

        if (
            lat is None
            or
            lon is None
        ):
            continue

        distance_m = (
            _distance_metres(
                search_lat,
                search_lon,
                lat,
                lon,
            )
        )

        if (
            distance_m
            >
            radius_m * 1.1
        ):
            continue

        records.append(
            {
                "name": name,

                "lat": lat,

                "lon": lon,

                "distance_m": (
                    distance_m
                ),

                "address": (
                    _address_from_tags(
                        tags
                    )
                ),

                "phone": (
                    _clean_text(
                        tags.get(
                            "phone"
                        )
                        or
                        tags.get(
                            "contact:phone"
                        )
                    )
                ),

                "website": (
                    _clean_text(
                        tags.get(
                            "website"
                        )
                        or
                        tags.get(
                            "contact:website"
                        )
                    )
                ),

                "opening_hours": (
                    _clean_text(
                        tags.get(
                            "opening_hours"
                        )
                    )
                ),

                "osm_type": (
                    element.get(
                        "type"
                    )
                ),

                "osm_id": (
                    element.get(
                        "id"
                    )
                ),

                "discovery_source": (
                    source_name
                ),
            }
        )

    return records


def _nominatim_pharmacy_fallback(
    search_lat: float,
    search_lon: float,
    radius_m: int,
) -> Dict[str, Any]:

    degrees_lat = (
        radius_m
        /
        111_320
    )

    longitude_scale = max(
        math.cos(
            math.radians(
                search_lat
            )
        ),
        0.2,
    )

    degrees_lon = (
        radius_m
        /
        (
            111_320
            *
            longitude_scale
        )
    )

    left = (
        search_lon
        -
        degrees_lon
    )

    right = (
        search_lon
        +
        degrees_lon
    )

    top = (
        search_lat
        +
        degrees_lat
    )

    bottom = (
        search_lat
        -
        degrees_lat
    )

    try:

        response = requests.get(
            NOMINATIM_SEARCH_URL,

            params={
                "q": "pharmacy",
                "format": "jsonv2",
                "limit": 20,
                "countrycodes": "ng",
                "addressdetails": 1,
                "bounded": 1,
                "viewbox": (
                    f"{left},"
                    f"{top},"
                    f"{right},"
                    f"{bottom}"
                ),
            },

            headers=HEADERS,

            timeout=(
                NOMINATIM_FALLBACK_TIMEOUT_SECONDS
            ),
        )

        response.raise_for_status()

        rows = (
            response.json()
        )

    except (
        requests.RequestException,
        ValueError,
    ) as error:

        return {
            "source_ok": False,

            "source_name": (
                "OpenStreetMap "
                "Nominatim fallback"
            ),

            "records": [],

            "error": str(
                error
            ),
        }

    records = []

    for row in rows:

        lat = (
            _safe_float(
                row.get(
                    "lat"
                )
            )
        )

        lon = (
            _safe_float(
                row.get(
                    "lon"
                )
            )
        )

        if (
            lat is None
            or
            lon is None
        ):
            continue

        distance_m = (
            _distance_metres(
                search_lat,
                search_lon,
                lat,
                lon,
            )
        )

        if (
            distance_m
            >
            radius_m * 1.1
        ):
            continue

        address_data = (
            row.get(
                "address"
            )
            or {}
        )

        name = (
            _clean_text(
                row.get(
                    "name"
                )
            )
        )

        if not name:

            display = (
                _clean_text(
                    row.get(
                        "display_name"
                    )
                )
                or ""
            )

            name = (
                display
                .split(
                    ","
                )[0]
                .strip()
                or
                None
            )

        address_parts = []

        for key in [
            "road",
            "suburb",
            "neighbourhood",
            "city",
            "town",
            "state",
        ]:

            value = (
                _clean_text(
                    address_data.get(
                        key
                    )
                )
            )

            if (
                value
                and
                value not in address_parts
            ):

                address_parts.append(
                    value
                )

        records.append(
            {
                "name": name,

                "lat": lat,

                "lon": lon,

                "distance_m": (
                    distance_m
                ),

                "address": (
                    ", ".join(
                        address_parts
                    )
                    or
                    _clean_text(
                        row.get(
                            "display_name"
                        )
                    )
                ),

                "phone": None,

                "website": None,

                "opening_hours": None,

                "osm_type": (
                    row.get(
                        "osm_type"
                    )
                ),

                "osm_id": (
                    row.get(
                        "osm_id"
                    )
                ),

                "discovery_source": (
                    "OpenStreetMap "
                    "Nominatim fallback"
                ),
            }
        )

    return {
        "source_ok": True,

        "source_name": (
            "OpenStreetMap "
            "Nominatim fallback"
        ),

        "records": (
            records
        ),

        "error": None,
    }


def find_nearby_pharmacies(
    location_query: str,
    radius_m: int = 5000,
    limit: int = 8,
) -> Dict[str, Any]:

    geocoded = (
        geocode_location(
            location_query
        )
    )

    if not geocoded.get(
        "source_ok"
    ):

        return {
            "source_ok": False,
            "source_name": (
                "OpenStreetMap"
            ),
            "location": None,
            "records": [],
            "error": (
                geocoded.get(
                    "error"
                )
            ),
            "used_fallback": False,
        }

    location = (
        geocoded.get(
            "location"
        )
    )

    if not location:

        return {
            "source_ok": True,
            "source_name": (
                "OpenStreetMap"
            ),
            "location": None,
            "records": [],
            "error": None,
            "used_fallback": False,
        }

    latitude = (
        location[
            "lat"
        ]
    )

    longitude = (
        location[
            "lon"
        ]
    )

    radius_m = max(
        500,
        min(
            int(
                radius_m
            ),
            10_000,
        ),
    )

    limit = max(
        1,
        min(
            int(
                limit
            ),
            10,
        ),
    )

    query = (
        _build_overpass_query(
            latitude,
            longitude,
            radius_m,
        )
    )

    errors = []

    for (
        endpoint_name,
        endpoint_url,
    ) in OVERPASS_ENDPOINTS:

        result = (
            _query_overpass_endpoint(
                endpoint_name,
                endpoint_url,
                query,
            )
        )

        if not result.get(
            "source_ok"
        ):

            errors.append(
                f"{endpoint_name}: "
                f"{result.get('error')}"
            )

            time.sleep(
                0.4
            )

            continue

        raw_records = (
            _parse_overpass_records(
                result.get(
                    "elements"
                )
                or [],
                latitude,
                longitude,
                radius_m,
                endpoint_name,
            )
        )

        ranked_records = (
            rank_pharmacy_candidates(
                raw_records,
                limit=limit,
            )
        )

        return {
            "source_ok": True,

            "source_name": (
                endpoint_name
            ),

            "location": (
                location
            ),

            "records": (
                ranked_records
            ),

            "raw_record_count": (
                len(
                    raw_records
                )
            ),

            "error": None,

            "used_fallback": (
                endpoint_name
                !=
                "Kumi Overpass"
            ),
        }

    fallback = (
        _nominatim_pharmacy_fallback(
            latitude,
            longitude,
            radius_m,
        )
    )

    if fallback.get(
        "source_ok"
    ):

        raw_records = (
            fallback.get(
                "records"
            )
            or []
        )

        ranked_records = (
            rank_pharmacy_candidates(
                raw_records,
                limit=limit,
            )
        )

        return {
            "source_ok": True,

            "source_name": (
                fallback.get(
                    "source_name"
                )
            ),

            "location": (
                location
            ),

            "records": (
                ranked_records
            ),

            "raw_record_count": (
                len(
                    raw_records
                )
            ),

            "error": None,

            "used_fallback": True,
        }

    if fallback.get(
        "error"
    ):

        errors.append(
            "Nominatim fallback: "
            f"{fallback.get('error')}"
        )

    return {
        "source_ok": False,

        "source_name": (
            "OpenStreetMap pharmacy discovery"
        ),

        "location": (
            location
        ),

        "records": [],

        "error": (
            " | ".join(
                errors
            )
            or
            "All pharmacy discovery "
            "sources failed."
        ),

        "used_fallback": True,
    }