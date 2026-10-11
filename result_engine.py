import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional


def _normalise_text(
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


def _similarity(
    left: Optional[str],
    right: Optional[str],
) -> Optional[float]:

    left_norm = (
        _normalise_text(
            left
        )
    )

    right_norm = (
        _normalise_text(
            right
        )
    )


    if not left_norm or not right_norm:
        return None


    return (
        SequenceMatcher(
            None,
            left_norm,
            right_norm,
        )
        .ratio()
    )


def _field_check(
    *,
    field: str,
    user_value: Optional[str],
    official_value: Optional[str],
    threshold: float,
) -> Dict[str, Any]:

    if not user_value:

        return {
            "field": field,
            "user_value": None,
            "official_value": official_value,
            "state": "not_provided",
            "similarity": None,
        }


    if not official_value:

        return {
            "field": field,
            "user_value": user_value,
            "official_value": None,
            "state": (
                "not_available_officially"
            ),
            "similarity": None,
        }


    similarity = (
        _similarity(
            user_value,
            official_value,
        )
    )


    state = (
        "match"
        if similarity is not None
        and similarity >= threshold
        else "mismatch"
    )


    return {
        "field": field,
        "user_value": user_value,
        "official_value": official_value,
        "state": state,
        "similarity": (
            round(
                similarity,
                3,
            )
            if similarity is not None
            else None
        ),
    }


def _record_score(
    product_state: Dict[str, Any],
    record: Dict[str, Any],
) -> float:

    scores = []


    product_similarity = (
        _similarity(
            product_state.get(
                "product_name"
            ),
            record.get(
                "product_name"
            ),
        )
    )


    if product_similarity is not None:

        scores.append(
            product_similarity
        )


    applicant_similarity = (
        _similarity(
            product_state.get(
                "manufacturer"
            ),
            record.get(
                "applicant"
            ),
        )
    )


    if applicant_similarity is not None:

        scores.append(
            applicant_similarity
        )


    if not scores:
        return 0.0


    return (
        sum(scores)
        / len(scores)
    )


def _build_napams_result(
    product_state: Dict[str, Any],
    greenbook_result: Dict[str, Any],
) -> Dict[str, Any]:

    registration_number = (
        product_state.get(
            "nafdac_number"
        )
    )


    napams = (
        greenbook_result.get(
            "napams"
        )
        or {}
    )


    napams_status = (
        napams.get(
            "status"
        )
    )


    # =====================================================
    # NAPAMS EXACT PRODUCT RESULT FOUND
    # =====================================================

    if (
        napams.get(
            "source_ok"
        )
        and
        napams.get(
            "found"
        )
        and
        napams_status
        == "match_found"
    ):

        record = (
            napams.get(
                "record"
            )
            or {}
        )


        field_checks = [
            {
                "field": (
                    "NAFDAC registration number"
                ),

                "user_value": (
                    registration_number
                ),

                "official_value": (
                    record.get(
                        "registration_number"
                    )
                    or registration_number
                ),

                "state": (
                    "match"
                ),

                "similarity": (
                    1.0
                ),
            }
        ]


        if record.get(
            "product_name"
        ):

            field_checks.append(
                _field_check(
                    field=(
                        "Product name"
                    ),
                    user_value=(
                        product_state.get(
                            "product_name"
                        )
                    ),
                    official_value=(
                        record.get(
                            "product_name"
                        )
                    ),
                    threshold=0.72,
                )
            )


        if record.get(
            "applicant"
        ):

            field_checks.append(
                _field_check(
                    field=(
                        "Manufacturer / applicant"
                    ),
                    user_value=(
                        product_state.get(
                            "manufacturer"
                        )
                    ),
                    official_value=(
                        record.get(
                            "applicant"
                        )
                    ),
                    threshold=0.65,
                )
            )


        mismatches = [
            item

            for item in field_checks

            if item.get(
                "state"
            )
            == "mismatch"
        ]


        if mismatches:

            names = ", ".join(
                item[
                    "field"
                ]

                for item
                in mismatches
            )


            return {
                "code": (
                    "details_mismatch"
                ),

                "level": (
                    "warning"
                ),

                "headline": (
                    "Some details do not match "
                    "the NAPAMS record"
                ),

                "summary": (
                    "NAPAMS returned the confirmed "
                    "NAFDAC registration number, "
                    "but Before Use found a mismatch "
                    f"in: {names}."
                ),

                "claim_limit": (
                    "A valid registration number can "
                    "appear on another physical product. "
                    "This does not prove that the item "
                    "in your hand is genuine."
                ),

                "next_action": (
                    "Compare the product label carefully "
                    "with the NAPAMS result before use."
                ),

                "field_checks": (
                    field_checks
                ),

                "official_record": (
                    record
                ),

                "candidate_count": (
                    1
                ),

                "registry_used": (
                    "NAFDAC NAPAMS"
                ),

                "napams_result_text": (
                    napams.get(
                        "result_text"
                    )
                ),
            }


        return {
            "code": (
                "napams_record_match"
            ),

            "level": (
                "positive"
            ),

            "headline": (
                "NAFDAC registration found in NAPAMS"
            ),

            "summary": (
                "The confirmed NAFDAC number was "
                "returned by the official NAPAMS "
                "product-verification service."
            ),

            "claim_limit": (
                "This confirms an official "
                "registration-record result. It does "
                "not prove that the individual product "
                "is genuine, untampered, correctly "
                "stored, or safe to use."
            ),

            "next_action": (
                "Continue checking the physical "
                "product and any relevant safety alerts."
            ),

            "field_checks": (
                field_checks
            ),

            "official_record": (
                record
            ),

            "candidate_count": (
                1
            ),

            "registry_used": (
                "NAFDAC NAPAMS"
            ),

            "napams_result_text": (
                napams.get(
                    "result_text"
                )
            ),
        }


    # =====================================================
    # NAPAMS EXPLICITLY RETURNED NO RESULT
    # =====================================================

    if (
        napams.get(
            "source_ok"
        )
        and
        napams_status
        == "not_found"
    ):

        return {
            "code": (
                "registration_not_found_in_connected_sources"
            ),

            "level": (
                "warning"
            ),

            "headline": (
                "Registration not found in connected "
                "NAFDAC sources"
            ),

            "summary": (
                "Before Use did not find the confirmed "
                "registration number in Greenbook, and "
                "NAPAMS displayed no matching product "
                "during this check."
            ),

            "claim_limit": (
                "This still does not prove that the "
                "individual product is counterfeit. "
                "Records and public systems can change "
                "or be temporarily incomplete."
            ),

            "next_action": (
                "Recheck the NAFDAC number on the "
                "product and confirm it directly with "
                "NAFDAC if necessary."
            ),

            "field_checks": [],

            "official_record": None,

            "candidate_count": 0,

            "registry_used": (
                "Greenbook + NAPAMS"
            ),
        }


    # =====================================================
    # NAPAMS COULD NOT BE CLASSIFIED
    # =====================================================

    return {
        "code": (
            "broader_registry_check_inconclusive"
        ),

        "level": (
            "limited"
        ),

        "headline": (
            "Broader NAFDAC verification incomplete"
        ),

        "summary": (
            "No exact Greenbook record was found. "
            "Before Use also attempted the broader "
            "NAPAMS verification, but the automated "
            "browser check could not safely classify "
            "the result."
        ),

        "claim_limit": (
            "An inconclusive automated lookup is not "
            "evidence that the product is unregistered, "
            "fake, or unsafe."
        ),

        "next_action": (
            "Open the official NAPAMS verification "
            "page and check the same NAFDAC number "
            "manually."
        ),

        "field_checks": [],

        "official_record": None,

        "candidate_count": 0,

        "registry_used": (
            "Greenbook + NAPAMS"
        ),

        "napams_error": (
            napams.get(
                "error"
            )
        ),
    }


def build_registration_result(
    product_state: Dict[str, Any],
    greenbook_result: Dict[str, Any],
) -> Dict[str, Any]:

    registration_number = (
        product_state.get(
            "nafdac_number"
        )
    )


    if not registration_number:

        return {
            "code": (
                "insufficient_input"
            ),

            "level": (
                "unknown"
            ),

            "headline": (
                "Registration number needed"
            ),

            "summary": (
                "Before Use does not have a "
                "NAFDAC registration number to "
                "compare with official records."
            ),

            "claim_limit": (
                "A product-name search alone is not "
                "enough to confirm registration."
            ),

            "next_action": (
                "Check the product label for its "
                "NAFDAC registration number."
            ),

            "field_checks": [],

            "official_record": None,

            "candidate_count": 0,
        }


    records: List[
        Dict[str, Any]
    ] = (
        greenbook_result.get(
            "records"
        )
        or []
    )


    # =====================================================
    # NO GREENBOOK RESULT
    #
    # Use automated NAPAMS result.
    # =====================================================

    if not records:

        return (
            _build_napams_result(
                product_state,
                greenbook_result,
            )
        )


    # =====================================================
    # GREENBOOK EXACT MATCH
    # =====================================================

    ranked = sorted(
        records,

        key=lambda record: (
            _record_score(
                product_state,
                record,
            )
        ),

        reverse=True,
    )


    record = (
        ranked[0]
    )


    product_check = (
        _field_check(
            field=(
                "Product name"
            ),

            user_value=(
                product_state.get(
                    "product_name"
                )
            ),

            official_value=(
                record.get(
                    "product_name"
                )
            ),

            threshold=0.72,
        )
    )


    applicant_check = (
        _field_check(
            field=(
                "Manufacturer / applicant"
            ),

            user_value=(
                product_state.get(
                    "manufacturer"
                )
            ),

            official_value=(
                record.get(
                    "applicant"
                )
            ),

            threshold=0.65,
        )
    )


    field_checks = [
        {
            "field": (
                "NAFDAC registration number"
            ),

            "user_value": (
                registration_number
            ),

            "official_value": (
                record.get(
                    "registration_number"
                )
            ),

            "state": (
                "match"
            ),

            "similarity": (
                1.0
            ),
        },

        product_check,

        applicant_check,
    ]


    status = (
        record.get(
            "status"
        )
        or ""
    ).strip().lower()


    mismatches = [
        item

        for item
        in field_checks

        if item.get(
            "state"
        )
        == "mismatch"
    ]


    if (
        status
        and
        status != "active"
    ):

        return {
            "code": (
                "registration_inactive"
            ),

            "level": (
                "warning"
            ),

            "headline": (
                "Registration record is not active"
            ),

            "summary": (
                "The NAFDAC registration exists in "
                "Greenbook, but the record is listed "
                f"as {record.get('status')}."
            ),

            "claim_limit": (
                "Registration status alone does not "
                "prove whether the individual product "
                "is genuine."
            ),

            "next_action": (
                "Confirm the current status directly "
                "with NAFDAC before using the product."
            ),

            "field_checks": (
                field_checks
            ),

            "official_record": (
                record
            ),

            "candidate_count": (
                len(records)
            ),

            "registry_used": (
                "NAFDAC Greenbook"
            ),
        }


    if mismatches:

        mismatch_names = (
            ", ".join(
                item[
                    "field"
                ]

                for item
                in mismatches
            )
        )


        return {
            "code": (
                "details_mismatch"
            ),

            "level": (
                "warning"
            ),

            "headline": (
                "Some details do not match "
                "the record"
            ),

            "summary": (
                "The registration number exists in "
                "Greenbook, but Before Use found a "
                f"mismatch in: {mismatch_names}."
            ),

            "claim_limit": (
                "Matching a NAFDAC number alone does "
                "not prove that the physical product "
                "is genuine."
            ),

            "next_action": (
                "Compare the product carefully with "
                "the official record."
            ),

            "field_checks": (
                field_checks
            ),

            "official_record": (
                record
            ),

            "candidate_count": (
                len(records)
            ),

            "registry_used": (
                "NAFDAC Greenbook"
            ),
        }


    return {
        "code": (
            "records_match"
        ),

        "level": (
            "positive"
        ),

        "headline": (
            "Registration record matches"
        ),

        "summary": (
            "The confirmed NAFDAC registration "
            "number was found as an active Greenbook "
            "record, and the other comparable details "
            "provided match."
        ),

        "claim_limit": (
            "This confirms a registration-record "
            "match. It does not prove that the "
            "individual product is genuine, "
            "untampered, properly stored, or "
            "safe to use."
        ),

        "next_action": (
            "Continue checking available safety "
            "alerts and the physical product."
        ),

        "field_checks": (
            field_checks
        ),

        "official_record": (
            record
        ),

        "candidate_count": (
            len(records)
        ),

        "registry_used": (
            "NAFDAC Greenbook"
        ),
    }