import json
import requests


URL = "https://greenbook.nafdac.gov.ng/"

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 BeforeUse-Debug/0.1",
}


def print_separator(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def run_test(name, params):
    print_separator(name)

    try:
        response = requests.get(
            URL,
            params=params,
            headers=HEADERS,
            timeout=30,
        )

        print("STATUS:", response.status_code)
        print("URL:", response.url)
        print(
            "CONTENT-TYPE:",
            response.headers.get("content-type"),
        )

        try:
            payload = response.json()

        except ValueError:
            print("\nNOT JSON.")
            print("FIRST 1200 CHARACTERS:")
            print(response.text[:1200])
            return

        print(
            "\nTOP-LEVEL TYPE:",
            type(payload).__name__,
        )

        if isinstance(payload, dict):

            print(
                "TOP-LEVEL KEYS:",
                list(payload.keys()),
            )

            print(
                "draw:",
                payload.get("draw"),
            )

            print(
                "recordsTotal:",
                payload.get("recordsTotal"),
            )

            print(
                "recordsFiltered:",
                payload.get("recordsFiltered"),
            )

            print(
                "error:",
                payload.get("error"),
            )

            rows = payload.get("data")

            print(
                "data type:",
                type(rows).__name__,
            )

            if isinstance(rows, list):

                print(
                    "rows returned:",
                    len(rows),
                )

                for index, row in enumerate(
                    rows[:5],
                    start=1,
                ):

                    print(f"\nROW {index}")

                    if isinstance(row, dict):

                        print(
                            "keys:",
                            list(row.keys()),
                        )

                        print(
                            json.dumps(
                                row,
                                indent=2,
                                ensure_ascii=False,
                            )[:2500]
                        )

                    else:

                        print(
                            repr(row)[:2500]
                        )

        else:

            print(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                )[:5000]
            )

    except Exception as error:

        print(
            "REQUEST FAILED:",
            type(error).__name__,
            str(error),
        )


# =========================================================
# TEST 1
# Minimal request
# =========================================================

run_test(
    "TEST 1 — MINIMAL DATATABLES REQUEST",
    {
        "draw": 1,
        "start": 0,
        "length": 5,
    },
)


# =========================================================
# TEST 2
# Global search for known NAFDAC number
# =========================================================

run_test(
    "TEST 2 — GLOBAL SEARCH FOR 04-0005",
    {
        "draw": 2,
        "start": 0,
        "length": 20,
        "search[value]": "04-0005",
        "search[regex]": "false",
    },
)


# =========================================================
# TEST 3
# Full DataTables-style request
# =========================================================

columns = [
    "product_name",
    "active_ingredients",
    "product_category",
    "nrn",
    "form",
    "roa",
    "strengths",
    "applicant_name",
    "approval_date",
    "status",
]


params = {
    "draw": 3,
    "start": 0,
    "length": 20,
    "search[value]": "04-0005",
    "search[regex]": "false",
}


for index, column in enumerate(columns):

    params[f"columns[{index}][data]"] = column
    params[f"columns[{index}][name]"] = column
    params[f"columns[{index}][searchable]"] = "true"
    params[f"columns[{index}][orderable]"] = "true"

    params[
        f"columns[{index}][search][value]"
    ] = ""

    params[
        f"columns[{index}][search][regex]"
    ] = "false"


params["order[0][column]"] = "0"
params["order[0][dir]"] = "asc"


run_test(
    "TEST 3 — FULL DATATABLES REQUEST FOR 04-0005",
    params,
)