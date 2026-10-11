from typing import Any, Dict, Optional

import requests


PCN_VERIFY_PREMISES_URL = (
    "https://pcncore.azurewebsites.net/"
    "PublicSearch/SearchForPremises"
)

PCN_HOME_URL = "https://pcn.gov.ng/"

TIMEOUT_SECONDS = 15

HEADERS = {
    "User-Agent": (
        "BeforeUse/0.4 "
        "(consumer medicine safety prototype)"
    )
}


def check_pcn_portal() -> Dict[str, Any]:
    """
    Confirm that the official PCN public premises-verification
    page is reachable.

    This does NOT verify a pharmacy. PCN does not publish a
    documented public API for programmatic premises matching.
    """
    try:
        response = requests.get(
            PCN_VERIFY_PREMISES_URL,
            headers=HEADERS,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        text = response.text.lower()

        expected = (
            "premises certificate verification"
            in text
            or "premises name" in text
        )

        return {
            "source_ok": bool(expected),
            "source_name": (
                "Pharmacy Council of Nigeria "
                "Premises Certificate Verification System"
            ),
            "source_url": PCN_VERIFY_PREMISES_URL,
            "error": (
                None
                if expected
                else "Unexpected response from PCN verification page."
            ),
        }

    except requests.RequestException as error:
        return {
            "source_ok": False,
            "source_name": (
                "Pharmacy Council of Nigeria "
                "Premises Certificate Verification System"
            ),
            "source_url": PCN_VERIFY_PREMISES_URL,
            "error": str(error),
        }


def build_pcn_verification_handoff(
    pharmacy: Dict[str, Any],
) -> Dict[str, Optional[str]]:
    """
    Build a conservative PCN verification state.

    Discovery data from OpenStreetMap is NOT sufficient to claim
    that a pharmacy is licensed by PCN. Until the official PCN
    portal returns a matching premises record, the status remains
    'not_confirmed'.

    The user is given the exact premises name plus the official
    PCN verification link to complete the check.
    """
    name = (
        str(
            pharmacy.get("name")
            or ""
        ).strip()
        or "Unnamed pharmacy"
    )

    return {
        "status": "not_confirmed",
        "label": "? PCN verification not confirmed",
        "premises_name": name,
        "source_name": (
            "Pharmacy Council of Nigeria "
            "Premises Certificate Verification System"
        ),
        "source_url": PCN_VERIFY_PREMISES_URL,
        "instruction": (
            f'Search the official PCN portal for "{name}". '
            "Before Use does not treat a missing or unconfirmed "
            "search result as proof that a premises is unlicensed."
        ),
    }