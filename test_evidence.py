from evidence_checker import (
    GreenbookClient,
    check_greenbook_registration,
)
from result_engine import (
    build_registration_result,
)


def run_check(product_state):
    print("\n" + "=" * 72)
    print("Checking:", product_state)

    evidence = (
        check_greenbook_registration(
            product_state.get(
                "nafdac_number"
            )
        )
    )

    print(
        "\nSOURCE OK:",
        evidence["source_ok"],
    )

    print(
        "RECORDS FOUND:",
        len(evidence["records"]),
    )

    if evidence.get("error"):
        print(
            "SOURCE ERROR:",
            evidence["error"],
        )

    for index, record in enumerate(
        evidence["records"],
        start=1,
    ):
        print(
            f"\nOFFICIAL MATCH {index}"
        )

        print(
            "Product:",
            record.get("product_name"),
        )

        print(
            "NAFDAC:",
            record.get(
                "registration_number"
            ),
        )

        print(
            "Applicant:",
            record.get("applicant"),
        )

        print(
            "Status:",
            record.get("status"),
        )

        print(
            "Source:",
            record.get("source_url"),
        )

    result = build_registration_result(
        product_state,
        evidence,
    )

    print(
        "\nRESULT CODE:",
        result["code"],
    )

    print(
        "HEADLINE:",
        result["headline"],
    )

    print(
        "SUMMARY:",
        result["summary"],
    )

    print(
        "LIMIT:",
        result["claim_limit"],
    )

    print("\nFIELD CHECKS")

    for check in result.get(
        "field_checks",
        [],
    ):
        print(
            "-",
            check["field"],
            "=>",
            check["state"],
            "| user:",
            check["user_value"],
            "| official:",
            check["official_value"],
        )


run_check(
    {
        "product_name": (
            "Panadol Extra"
        ),
        "nafdac_number": "04-0005",
        "manufacturer": (
            "GlaxoSmithKline "
            "Consumer Nigeria PLC"
        ),
        "batch_number": "116Y",
        "expiry_date": (
            "December 2027"
        ),
    }
)


run_check(
    {
        "product_name": (
            "Panadol Extra"
        ),
        "nafdac_number": "A4-1409",
        "manufacturer": "Emzor",
        "batch_number": "258341B",
        "expiry_date": (
            "December 2027"
        ),
    }
)
