from typing import Any, Dict, Optional


NAFDAC_SF_REPORT_URL = (
    "https://greenbook.nafdac.gov.ng/report/sf"
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


def build_concern_summary(
    product: Dict[str, Any],
    evidence_result: Optional[
        Dict[str, Any]
    ] = None,
    mas_result: Optional[
        Dict[str, Any]
    ] = None,
    reason: Optional[str] = None,
) -> str:

    evidence_result = (
        evidence_result
        or {}
    )

    mas_result = (
        mas_result
        or {}
    )


    lines = [

        "BEFORE USE - PRODUCT CONCERN SUMMARY",

        "",

        (
            "Product: "
            f"{_clean(product.get('product_name')) or 'Not provided'}"
        ),

        (
            "NAFDAC number: "
            f"{_clean(product.get('nafdac_number')) or 'Not provided'}"
        ),

        (
            "Manufacturer: "
            f"{_clean(product.get('manufacturer')) or 'Not provided'}"
        ),

        (
            "Batch / lot: "
            f"{_clean(product.get('batch_number')) or 'Not provided'}"
        ),

        (
            "Expiry: "
            f"{_clean(product.get('expiry_date')) or 'Not provided'}"
        ),

        "",

        (
            "Evidence finding: "
            f"{_clean(evidence_result.get('headline')) or 'Not available'}"
        ),

        (
            "Evidence summary: "
            f"{_clean(evidence_result.get('summary')) or 'Not available'}"
        ),
    ]


    if (
        mas_result.get(
            "response_text"
        )
    ):

        lines.extend(
            [
                "",

                "User-reported MAS response:",

                str(
                    mas_result.get(
                        "response_text"
                    )
                ),

                "",

                "MAS evidence note:",

                str(
                    mas_result.get(
                        "claim_limit"
                    )
                    or
                    "User-reported only."
                ),
            ]
        )


    if _clean(
        reason
    ):

        lines.extend(
            [
                "",

                "Reason for concern:",

                _clean(
                    reason
                ),
            ]
        )


    lines.extend(
        [
            "",

            (
                "Important: This summary was prepared "
                "by Before Use to help the user report "
                "a concern. It is not a NAFDAC determination "
                "that the product is falsified, substandard, "
                "unsafe, or unregistered."
            ),
        ]
    )


    return "\n".join(
        lines
    )