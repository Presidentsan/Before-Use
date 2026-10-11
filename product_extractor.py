import re


def extract_product_details(text):
    """
    Extract candidate product details from an N-ATLAS transcript.

    This is the local fallback used if the AI interpreter
    is unavailable.

    It normalizes formatting where safe but does not invent
    missing letters, numbers, or dates.
    """

    details = {
        "product_name": None,
        "nafdac_number": None,
        "manufacturer": None,
        "batch_number": None,
        "expiry_date": None,
    }

    if not text:
        return details

    cleaned_text = text.strip()

    # -----------------------------------------------------
    # PRODUCT NAME
    # -----------------------------------------------------
    #
    # Handles speech variations such as:
    #
    # I'm checking Panadol Extra
    # I'm checking a pack of Panadol Extra
    # I'm taking Panadol Extra
    # I'm holding Panadol Extra
    # The product is Panadol Extra
    # Product name is Panadol Extra
    # -----------------------------------------------------

    product_patterns = [
        (
            r"(?:i['’]?m\s+)?checking\s+a\s+pack\s+of\s+"
            r"(.+?)(?=[.!?]|$)"
        ),
        (
            r"(?:i['’]?m\s+)?checking\s+"
            r"(.+?)(?=[.!?]|$)"
        ),
        (
            r"(?:i['’]?m\s+)?taking\s+"
            r"(.+?)(?=[.!?]|$)"
        ),
        (
            r"(?:i['’]?m\s+)?holding\s+"
            r"(.+?)(?=[.!?]|$)"
        ),
        (
            r"(?:the\s+)?product(?:\s+name)?"
            r"\s+(?:is|says)\s+"
            r"(.+?)(?=[.!?]|$)"
        ),
    ]

    for pattern in product_patterns:
        match = re.search(
            pattern,
            cleaned_text,
            flags=re.IGNORECASE,
        )

        if match:
            details["product_name"] = (
                match.group(1)
                .strip()
                .rstrip(",.;")
            )
            break

    # -----------------------------------------------------
    # NAFDAC REGISTRATION NUMBER
    # -----------------------------------------------------
    #
    # Accept:
    # A4-1409
    # A4 1409
    # A41409
    #
    # Formatting may be normalized.
    # Missing characters must NOT be invented.
    # -----------------------------------------------------

    registration_match = re.search(
        r"\b([A-Za-z])(\d)[-\s]?(\d{4,6})\b",
        cleaned_text,
    )

    if registration_match:
        letter = registration_match.group(1).upper()
        first_digit = registration_match.group(2)
        remaining_digits = registration_match.group(3)

        details["nafdac_number"] = (
            f"{letter}{first_digit}-{remaining_digits}"
        )

    # -----------------------------------------------------
    # MANUFACTURER / APPLICANT
    # -----------------------------------------------------

    manufacturer_patterns = [
        (
            r"(?:the\s+)?"
            r"(?:manufacturer(?:'s)?(?:\s+name)?|"
            r"applicant(?:'s)?(?:\s+name)?)"
            r"\s+(?:is|says)\s+"
            r"(.+?)"
            r"(?=\s*[,.;]?\s*(?:and\s+)?"
            r"(?:batch|batches|lot|expiry|expire|expires|"
            r"expiration|expiridate|expiridates)"
            r"\b|[.!?]|$)"
        ),
        (
            r"(?:manufactured|made)\s+by\s+"
            r"(.+?)"
            r"(?=\s*[,.;]?\s*(?:and\s+)?"
            r"(?:batch|batches|lot|expiry|expire|expires|"
            r"expiration|expiridate|expiridates)"
            r"\b|[.!?]|$)"
        ),
    ]

    for pattern in manufacturer_patterns:
        match = re.search(
            pattern,
            cleaned_text,
            flags=re.IGNORECASE,
        )

        if match:
            details["manufacturer"] = (
                match.group(1)
                .strip()
                .rstrip(",.;")
            )
            break

    # -----------------------------------------------------
    # BATCH / LOT NUMBER
    # -----------------------------------------------------

    batch_match = re.search(
        (
            r"\b(?:batch|batches|lot)"
            r"(?:\s+(?:number|no\.?))?"
            r"(?:\s+(?:is|says))?"
            r"[\s:,-]+"
            r"([A-Za-z0-9\-/]+)"
        ),
        cleaned_text,
        flags=re.IGNORECASE,
    )

    if batch_match:
        details["batch_number"] = (
            batch_match.group(1)
            .strip()
            .rstrip(",.;")
            .upper()
        )

    # -----------------------------------------------------
    # EXPIRY DATE
    # -----------------------------------------------------
    #
    # Handles common N-ATLAS variations:
    #
    # expiry date is December 2027
    # expire date is December 2027
    # expirydate is December 2027
    # expiridate is December 2027
    # expiridates December 2027
    # expires December 2027
    # -----------------------------------------------------

    expiry_patterns = [
        (
            r"(?:expiry|expire|expiration)"
            r"\s*date"
            r"\s+(?:is|says)?\s*"
            r"(?:in\s+|on\s+)?"
            r"(.+?)"
            r"(?=[.!?]|$)"
        ),
        (
            r"(?:expirydate|expiridate|expiridates)"
            r"\s+(?:is|says)?\s*"
            r"(?:in\s+|on\s+)?"
            r"(.+?)"
            r"(?=[.!?]|$)"
        ),
        (
            r"(?:it\s+)?expires?"
            r"\s+(?:on\s+|in\s+)?"
            r"(.+?)"
            r"(?=[.!?]|$)"
        ),
    ]

    for pattern in expiry_patterns:
        match = re.search(
            pattern,
            cleaned_text,
            flags=re.IGNORECASE,
        )

        if match:
            details["expiry_date"] = (
                match.group(1)
                .strip()
                .rstrip(",.;")
            )
            break

    return details


def extract_field_answer(text, field):
    """
    Extract a candidate answer from a follow-up voice response.
    """

    if not text:
        return None

    answer = text.strip()

    # -----------------------------------------------------
    # REMOVE COMMON OPENERS
    # -----------------------------------------------------

    answer = re.sub(
        r"^(?:yes|yeah|yep|okay|ok|alright)[,\s]+",
        "",
        answer,
        flags=re.IGNORECASE,
    )

    # -----------------------------------------------------
    # FIELD-SPECIFIC CLEANUP
    # -----------------------------------------------------

    patterns = {
        "product_name": [
            r"^(?:the\s+)?product(?:\s+name)?\s+(?:is|says)\s+",
            r"^(?:it\s+is|it's)\s+",
        ],

        "nafdac_number": [
            r"^(?:the\s+)?nafdac(?:\s+(?:registration\s+)?number)?\s+(?:is|says)\s+",
            r"^(?:the\s+)?registration(?:\s+number)?\s+(?:is|says)\s+",
            r"^(?:the\s+)?number\s+(?:is|says)\s+",
        ],

        "manufacturer": [
            r"^(?:the\s+)?manufacturer(?:'s)?(?:\s+name)?\s+(?:is|says)\s+",
            r"^(?:the\s+)?applicant(?:'s)?(?:\s+name)?\s+(?:is|says)\s+",
            r"^(?:it\s+is\s+)?(?:manufactured|made)\s+by\s+",
        ],

        "batch_number": [
            r"^(?:the\s+)?batch(?:\s+(?:number|no\.?))?\s+(?:is|says)\s+",
            r"^(?:the\s+)?batch(?:\s+(?:number|no\.?))?\s+",
            r"^(?:the\s+)?batches?\s+(?:is|says)?\s*",
            r"^(?:the\s+)?lot(?:\s+(?:number|no\.?))?\s+(?:is|says)\s+",
            r"^(?:the\s+)?lot(?:\s+(?:number|no\.?))?\s+",
        ],

        "expiry_date": [
            r"^(?:the\s+)?expiry\s*date\s+(?:is|says)\s+",
            r"^(?:the\s+)?expire\s*date\s+(?:is|says)\s+",
            r"^(?:the\s+)?expirydate\s+(?:is|says)\s+",
            r"^(?:the\s+)?expiridates?\s+(?:is|says)?\s*",
            r"^(?:the\s+)?expiration(?:\s+date)?\s+(?:is|says)\s+",
            r"^(?:it\s+)?expires?\s+(?:on\s+|in\s+)?",
        ],
    }

    field_patterns = patterns.get(field, [])

    for pattern in field_patterns:
        cleaned_answer = re.sub(
            pattern,
            "",
            answer,
            flags=re.IGNORECASE,
        )

        if cleaned_answer != answer:
            answer = cleaned_answer
            break

    answer = answer.strip().rstrip(".!?,")

    # -----------------------------------------------------
    # NORMALIZE NAFDAC FORMAT
    # -----------------------------------------------------

    if field == "nafdac_number":
        registration_match = re.fullmatch(
            r"([A-Za-z])(\d)[-\s]?(\d{4,6})",
            answer,
        )

        if registration_match:
            letter = registration_match.group(1).upper()
            first_digit = registration_match.group(2)
            remaining_digits = registration_match.group(3)

            answer = (
                f"{letter}{first_digit}-{remaining_digits}"
            )
        else:
            answer = answer.upper()

    # -----------------------------------------------------
    # NORMALIZE BATCH NUMBER
    # -----------------------------------------------------

    if field == "batch_number":
        answer = answer.upper()

    return answer or None