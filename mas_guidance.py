from typing import Any, Dict, Optional


MAS_GUIDELINE_URL = (
    "https://www.nafdac.gov.ng/wp-content/uploads/"
    "Files/Resources/Guidelines/PVG_GUIDELINES/"
    "NAFDAC-MAS-Guidelines-Recent.pdf"
)


def _clean(
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


def classify_user_reported_mas_response(
    response_text: str,
) -> Dict[str, Any]:
    """
    Classify only the response the user says
    they received from the MAS system.

    Before Use does not independently send
    the PIN or verify the SMS with the provider.
    """

    text = _clean(
        response_text
    )

    if not text:

        return {
            "status": (
                "not_provided"
            ),

            "label": (
                "No MAS response recorded"
            ),

            "response_text": (
                None
            ),

            "claim_limit": (
                "Before Use has not independently "
                "checked a MAS response for this pack."
            ),
        }


    lower = (
        text.lower()
    )


    suspicious_terms = (
        "suspected fake",
        "fake",
        "invalid",
        "already used",
        "incorrect pin",
        "not genuine",
        "counterfeit",
    )


    positive_terms = (
        "genuine",
        "authentic",
        "valid product",
        "original",
    )


    if any(
        term in lower
        for term
        in suspicious_terms
    ):

        status = (
            "user_reported_concern"
        )

        label = (
            "User-reported MAS response "
            "indicates a concern"
        )


    elif any(
        term in lower
        for term
        in positive_terms
    ):

        status = (
            "user_reported_positive"
        )

        label = (
            "User-reported MAS response "
            "appears positive"
        )


    else:

        status = (
            "user_reported_unclassified"
        )

        label = (
            "User-reported MAS response recorded"
        )


    return {
        "status": (
            status
        ),

        "label": (
            label
        ),

        "response_text": (
            text
        ),

        "claim_limit": (
            "This is a user-reported MAS response. "
            "Before Use did not independently send "
            "the PIN, receive the SMS, or verify the "
            "response with the MAS provider."
        ),
    }