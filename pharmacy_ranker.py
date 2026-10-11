import json
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field


load_dotenv()

MODEL_ID = "gemini-3.5-flash-lite"


GENERIC_NAMES = {
    "pharmacy",
    "chemist",
    "drugstore",
    "drug store",
    "medicine store",
    "none",
    "unnamed pharmacy",
}


class PharmacyRanking(BaseModel):
    selected_ids: List[int] = Field(
        default_factory=list
    )


def _normalized_name(
    name: str,
) -> str:

    return re.sub(
        r"[^a-z0-9]+",
        "",
        (
            name
            or ""
        ).lower(),
    )


def _usable_name(
    name: str,
) -> bool:

    cleaned = (
        name
        or ""
    ).strip().lower().strip(
        "."
    )

    if (
        not cleaned
        or
        cleaned
        in GENERIC_NAMES
    ):
        return False

    return (
        len(
            _normalized_name(
                cleaned
            )
        )
        >=
        4
    )


def _quality_score(
    record: Dict[
        str,
        Any,
    ],
) -> float:

    score = 0.0

    if record.get(
        "address"
    ):
        score += 4

    if record.get(
        "phone"
    ):
        score += 2

    if record.get(
        "opening_hours"
    ):
        score += 1

    if record.get(
        "website"
    ):
        score += 1

    distance = record.get(
        "distance_m"
    )

    if isinstance(
        distance,
        (
            int,
            float,
        ),
    ):

        score += max(
            0.0,
            2.0
            -
            min(
                float(
                    distance
                ),
                10000.0,
            )
            /
            5000.0,
        )

    return score


def deterministic_cleanup(
    records: List[
        Dict[str, Any]
    ],
    limit: int = 8,
) -> List[
    Dict[str, Any]
]:

    grouped: Dict[
        str,
        Dict[str, Any],
    ] = {}

    for record in records:

        name = str(
            record.get(
                "name"
            )
            or ""
        ).strip()

        if not _usable_name(
            name
        ):
            continue

        key = (
            _normalized_name(
                name
            )
        )

        current = (
            grouped.get(
                key
            )
        )

        if current is None:

            grouped[
                key
            ] = record

            continue

        if (
            _quality_score(
                record
            )
            >
            _quality_score(
                current
            )
        ):

            grouped[
                key
            ] = record

        elif (
            _quality_score(
                record
            )
            ==
            _quality_score(
                current
            )
        ):

            if (
                record.get(
                    "distance_m",
                    10**9,
                )
                <
                current.get(
                    "distance_m",
                    10**9,
                )
            ):

                grouped[
                    key
                ] = record

    cleaned = list(
        grouped.values()
    )

    cleaned.sort(
        key=lambda item: (
            -_quality_score(
                item
            ),
            item.get(
                "distance_m",
                10**9,
            ),
        )
    )

    return (
        cleaned[
            :limit
        ]
    )


def rank_pharmacy_candidates(
    records: List[
        Dict[str, Any]
    ],
    limit: int = 8,
) -> List[
    Dict[str, Any]
]:

    base = (
        deterministic_cleanup(
            records,
            limit=max(
                limit * 2,
                limit,
            ),
        )
    )

    if not base:
        return []

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        return base[
            :limit
        ]

    candidates = []

    by_id: Dict[
        int,
        Dict[str, Any],
    ] = {}

    for index, record in enumerate(
        base,
        start=1,
    ):

        by_id[
            index
        ] = record

        candidates.append(
            {
                "id": index,

                "name": (
                    record.get(
                        "name"
                    )
                ),

                "address": (
                    record.get(
                        "address"
                    )
                ),

                "distance_m": (
                    record.get(
                        "distance_m"
                    )
                ),

                "opening_hours": (
                    record.get(
                        "opening_hours"
                    )
                ),

                "phone_present": bool(
                    record.get(
                        "phone"
                    )
                ),

                "website_present": bool(
                    record.get(
                        "website"
                    )
                ),
            }
        )

    prompt = f"""
You are ranking pharmacy-location candidates for Before Use.

Every candidate below came from OpenStreetMap.

Rules:
- You MUST NOT invent a pharmacy.
- You MUST NOT invent or change addresses.
- You MUST NOT invent opening hours.
- You MUST NOT invent phone numbers.
- You MUST NOT invent licensing or PCN status.
- You may ONLY return IDs that appear below.
- Remove weak or generic-looking candidates.
- Remove obvious duplicates.
- Prefer candidates with useful identifying information.
- Prefer closer candidates when quality is otherwise similar.
- Return at most {limit} candidate IDs.
- Return the best candidates first.

Candidates:
{json.dumps(candidates, ensure_ascii=False)}
"""

    try:

        client = genai.Client(
            api_key=api_key
        )

        response = (
            client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config={
                    "response_mime_type": (
                        "application/json"
                    ),
                    "response_schema": (
                        PharmacyRanking
                    ),
                    "temperature": 0,
                },
            )
        )

        parsed = (
            response.parsed
        )

        if parsed is None:
            return base[
                :limit
            ]

        if isinstance(
            parsed,
            PharmacyRanking,
        ):
            ranking = parsed

        else:

            ranking = (
                PharmacyRanking
                .model_validate(
                    parsed
                )
            )

        selected = []

        seen = set()

        for candidate_id in (
            ranking.selected_ids
        ):

            if (
                candidate_id
                in by_id
                and
                candidate_id
                not in seen
            ):

                selected.append(
                    by_id[
                        candidate_id
                    ]
                )

                seen.add(
                    candidate_id
                )

            if (
                len(
                    selected
                )
                >=
                limit
            ):
                break

        if not selected:
            return base[
                :limit
            ]

        return selected

    except Exception:

        return base[
            :limit
        ]