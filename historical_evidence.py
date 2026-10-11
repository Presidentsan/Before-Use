import re
from typing import Any, Dict, List, Optional


# =========================================================
# VERIFIED HISTORICAL NAFDAC INDEX
# =========================================================

HISTORICAL_RECORDS = [
    {
        "product_name": "CADIPHEN",
        "registration_number": "04-1876",
        "manufacturer": "Cadila Pharmaceuticals Limited",
        "product_class": "Respiratory System Drugs",
        "evidence_year": 2019,
        "source_name": (
            "NAFDAC Central Drug Control Laboratory "
            "— List of Products Analysed in CDCL, 2019"
        ),
        "source_url": (
            "https://www.nafdac.gov.ng/wp-content/uploads/"
            "Files/Resources/Directorate_Resources/"
            "Lab_Services_CDCL/"
            "List-Of-Products-Analysed-In-CDCL-2019.pdf"
        ),
        "source_type": "official_nafdac_historical_record",
        "note": (
            "This historical source associates registration "
            "04-1876 with CADIPHEN and Cadila Pharmaceuticals. "
            "It does not prove that the registration is currently active."
        ),
    },
]


def normalize_registration_number(
    value: Optional[str],
) -> str:
    if not value:
        return ""

    return re.sub(
        r"[^A-Z0-9]",
        "",
        str(value).upper(),
    )


def _normalize_text(
    value: Optional[str],
) -> str:
    if not value:
        return ""

    return " ".join(
        re.findall(
            r"[a-z0-9]+",
            str(value).lower(),
        )
    )


def _text_similarity(
    left: Optional[str],
    right: Optional[str],
) -> float:
    """
    Lightweight token overlap.

    Used only to assess consistency between the user's
    product/manufacturer wording and the historical record.
    """

    left_tokens = set(
        _normalize_text(
            left
        ).split()
    )

    right_tokens = set(
        _normalize_text(
            right
        ).split()
    )

    if not left_tokens or not right_tokens:
        return 0.0

    intersection = (
        left_tokens
        &
        right_tokens
    )

    union = (
        left_tokens
        |
        right_tokens
    )

    return (
        len(intersection)
        /
        len(union)
    )


def find_historical_evidence(
    *,
    registration_number: Optional[str] = None,
    product_name: Optional[str] = None,
    manufacturer: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search Before Use's curated historical NAFDAC evidence.

    Historical evidence is deliberately kept separate from the
    current Greenbook.

    An exact normalized registration-number match is required
    before a historical record is returned.
    """

    target_registration = (
        normalize_registration_number(
            registration_number
        )
    )

    matches: List[
        Dict[str, Any]
    ] = []

    for record in HISTORICAL_RECORDS:

        official_registration = (
            normalize_registration_number(
                record.get(
                    "registration_number"
                )
            )
        )

        registration_matches = bool(
            target_registration
            and official_registration
            and (
                target_registration
                ==
                official_registration
            )
        )

        if not registration_matches:
            continue

        product_score = (
            _text_similarity(
                product_name,
                record.get(
                    "product_name"
                ),
            )
        )

        manufacturer_score = (
            _text_similarity(
                manufacturer,
                record.get(
                    "manufacturer"
                ),
            )
        )

        matched_record = dict(
            record
        )

        matched_record[
            "registration_match"
        ] = True

        if product_name:
            matched_record[
                "product_name_consistent"
            ] = (
                product_score
                >= 0.30
            )
        else:
            matched_record[
                "product_name_consistent"
            ] = None

        if manufacturer:
            matched_record[
                "manufacturer_consistent"
            ] = (
                manufacturer_score
                >= 0.25
            )
        else:
            matched_record[
                "manufacturer_consistent"
            ] = None

        matches.append(
            matched_record
        )

    return {
        "source_ok": True,
        "source_name": (
            "Historical NAFDAC evidence"
        ),
        "query": {
            "registration_number": (
                registration_number
            ),
            "product_name": (
                product_name
            ),
            "manufacturer": (
                manufacturer
            ),
        },
        "records": matches,
        "error": None,
    }