from evidence_orchestrator import (
    check_all_evidence,
)


TESTS = [
    {
        "name": (
            "PANADOL"
        ),

        "product": {
            "product_name": (
                "Panadol Extra"
            ),
            "nafdac_number": (
                "04-0005"
            ),
            "manufacturer": (
                "GlaxoSmithKline "
                "Consumer Nigeria PLC"
            ),
            "batch_number": (
                "116Y"
            ),
            "expiry_date": (
                "December 2027"
            ),
        },
    },

    {
        "name": (
            "CADIPHEN"
        ),

        "product": {
            "product_name": (
                "Cadiphen Cough "
                "Expectorant"
            ),
            "nafdac_number": (
                "04-1876"
            ),
            "manufacturer": (
                "Cadila Pharmaceuticals"
            ),
            "batch_number": (
                "116Y"
            ),
            "expiry_date": (
                "October 2028"
            ),
        },
    },

    {
        "name": (
            "WHO ALERT TEST"
        ),

        "product": {
            "product_name": (
                "DARZALEX"
            ),
            "nafdac_number": None,
            "manufacturer": None,
            "batch_number": None,
            "expiry_date": None,
        },
    },
]


for test in TESTS:

    print(
        "\n"
        +
        "=" * 70
    )

    print(
        test["name"]
    )

    print(
        "=" * 70
    )


    result = (
        check_all_evidence(
            test["product"]
        )
    )


    print(
        "FINAL CODE:",
        result[
            "code"
        ],
    )


    print(
        "HEADLINE:",
        result[
            "headline"
        ],
    )


    print(
        "SUMMARY:",
        result[
            "summary"
        ],
    )


    print(
        "\nSOURCE COUNTS"
    )


    for source_name, source in (
        result[
            "sources"
        ].items()
    ):

        print(
            source_name,
            ":",
            len(
                source.get(
                    "records",
                    [],
                )
            ),
            "records",
            "| source_ok =",
            source.get(
                "source_ok"
            ),
        )


    who_records = (
        result[
            "sources"
        ][
            "who_alerts"
        ].get(
            "records",
            [],
        )
    )


    if who_records:

        print(
            "\nWHO MATCHES"
        )

        for alert in who_records[:3]:

            print(
                "-",
                alert.get(
                    "significance"
                ),
                "|",
                alert.get(
                    "title"
                ),
            )

            print(
                " ",
                alert.get(
                    "source_url"
                ),
            )