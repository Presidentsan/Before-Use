from pprint import pprint

from evidence_orchestrator import (
    check_all_evidence,
)


TESTS = [
    {
        "name": (
            "PANADOL CURRENT RECORD"
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
            "CADIPHEN HISTORICAL RECORD"
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
]


for test in TESTS:

    print(
        "\n"
        + "=" * 76
    )

    print(
        test["name"]
    )

    print(
        "=" * 76
    )


    result = (
        check_all_evidence(
            test["product"]
        )
    )


    print(
        "FINAL CODE:",
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
        "NEXT ACTION:",
        result["next_action"],
    )


    print(
        "\nGREENBOOK"
    )

    print(
        "source_ok:",
        result[
            "sources"
        ][
            "greenbook"
        ][
            "source_ok"
        ],
    )

    print(
        "records:",
        len(
            result[
                "sources"
            ][
                "greenbook"
            ][
                "records"
            ]
        ),
    )


    print(
        "\nHISTORICAL NAFDAC"
    )

    historical_records = (
        result[
            "sources"
        ][
            "historical_nafdac"
        ][
            "records"
        ]
    )

    print(
        "records:",
        len(
            historical_records
        ),
    )


    for record in historical_records:

        pprint(
            record
        )


    print(
        "\nNAFDAC ALERTS"
    )

    alerts = (
        result[
            "sources"
        ][
            "nafdac_alerts"
        ]
    )


    print(
        "source_ok:",
        alerts[
            "source_ok"
        ],
    )


    print(
        "records:",
        len(
            alerts[
                "records"
            ]
        ),
    )


    for record in alerts[
        "records"
    ][:3]:

        print(
            "-",
            record[
                "significance"
            ],
            record[
                "title"
            ],
        )

        print(
            "  Reasons:",
            record[
                "match_reasons"
            ],
        )

        print(
            "  URL:",
            record[
                "source_url"
            ],
        )