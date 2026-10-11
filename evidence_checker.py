import re
import time
from typing import Any, Dict, List, Optional

import requests

from napams_browser import (
    check_napams_registration,
)


GREENBOOK_URL = (
    "https://greenbook.nafdac.gov.ng/"
)

DETAIL_URL = (
    "https://greenbook.nafdac.gov.ng/"
    "products/details/{product_id}"
)

NAPAMS_URL = (
    "https://registration.nafdac.gov.ng/Home/"
)


REQUEST_HEADERS = {
    "Accept": (
        "application/json, "
        "text/javascript, */*; q=0.01"
    ),

    "X-Requested-With": (
        "XMLHttpRequest"
    ),

    "User-Agent": (
        "BeforeUse/0.3 "
        "(consumer product-safety prototype; "
        "NAFDAC public evidence lookup)"
    ),
}


TIMEOUT_SECONDS = 25


class EvidenceSourceError(
    RuntimeError
):
    """
    Raised when Greenbook cannot be queried safely.
    """


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


def _clean_text(
    value: Any,
) -> Optional[str]:

    if value is None:
        return None

    if isinstance(
        value,
        (
            dict,
            list,
        ),
    ):
        return None


    text = (
        str(value)
        .strip()
    )


    if not text:
        return None


    if text.lower() in {
        "na",
        "n/a",
        "nil",
        "null",
        "none",
        "-",
    }:
        return None


    return text


def normalize_greenbook_record(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    product_id = (
        row.get(
            "product_id"
        )
    )


    if product_id is not None:

        product_id = (
            str(product_id)
            .strip()
            or None
        )


    source_url = (
        GREENBOOK_URL
    )


    if product_id:

        source_url = (
            DETAIL_URL.format(
                product_id=product_id
            )
        )


    return {
        "product_id": (
            product_id
        ),

        "product_name": (
            _clean_text(
                row.get(
                    "product_name"
                )
            )
        ),

        "registration_number": (
            _clean_text(
                row.get(
                    "NAFDAC"
                )
            )
        ),

        "active_ingredients": (
            _clean_text(
                row.get(
                    "ingredient_name"
                )
            )
        ),

        "category": (
            _clean_text(
                row.get(
                    "category_name"
                )
            )
        ),

        "form": (
            _clean_text(
                row.get(
                    "form_name"
                )
            )
        ),

        "route": (
            _clean_text(
                row.get(
                    "route_name"
                )
            )
        ),

        "strength": (
            _clean_text(
                row.get(
                    "strength"
                )
            )
        ),

        "applicant": (
            _clean_text(
                row.get(
                    "applicant_name"
                )
            )
        ),

        "approval_date": (
            _clean_text(
                row.get(
                    "approval_date"
                )
            )
        ),

        "registration_expiry_date": (
            _clean_text(
                row.get(
                    "expiry_date"
                )
            )
        ),

        "status": (
            _clean_text(
                row.get(
                    "status"
                )
            )
        ),

        "source_name": (
            "NAFDAC Greenbook"
        ),

        "source_url": (
            source_url
        ),
    }


class GreenbookClient:

    COLUMNS = [
        "product_name",
        "ingredient_name",
        "category_name",
        "NAFDAC",
        "form_name",
        "route_name",
        "strength",
        "applicant_name",
        "approval_date",
        "status",
    ]


    def __init__(
        self,
        timeout: int = TIMEOUT_SECONDS,
        min_request_interval: float = 0.8,
    ):

        self.timeout = (
            timeout
        )

        self.min_request_interval = (
            min_request_interval
        )


        self.session = (
            requests.Session()
        )


        self.session.headers.update(
            REQUEST_HEADERS
        )


        self._last_request_at = (
            0.0
        )


    def _wait_if_needed(
        self,
    ):

        elapsed = (
            time.monotonic()
            - self._last_request_at
        )


        remaining = (
            self.min_request_interval
            - elapsed
        )


        if remaining > 0:

            time.sleep(
                remaining
            )


    def _build_params(
        self,
        search: str,
        *,
        draw: int = 1,
        start: int = 0,
        length: int = 50,
    ) -> Dict[str, Any]:

        params = {
            "draw": draw,
            "start": start,
            "length": length,
            "search[value]": search,
            "search[regex]": "false",
        }


        for index, column in enumerate(
            self.COLUMNS
        ):

            params[
                f"columns[{index}][data]"
            ] = column

            params[
                f"columns[{index}][name]"
            ] = column

            params[
                f"columns[{index}][searchable]"
            ] = "true"

            params[
                f"columns[{index}][orderable]"
            ] = "true"

            params[
                f"columns[{index}][search][value]"
            ] = ""

            params[
                f"columns[{index}][search][regex]"
            ] = "false"


        params[
            "order[0][column]"
        ] = "0"

        params[
            "order[0][dir]"
        ] = "asc"


        return params


    def _request_rows(
        self,
        search: str,
        *,
        length: int = 50,
    ) -> Dict[str, Any]:

        self._wait_if_needed()


        params = (
            self._build_params(
                search,
                length=length,
            )
        )


        try:

            response = (
                self.session.get(
                    GREENBOOK_URL,
                    params=params,
                    timeout=self.timeout,
                )
            )

        except requests.RequestException as error:

            raise EvidenceSourceError(
                "The NAFDAC Greenbook "
                "could not be reached."
            ) from error


        self._last_request_at = (
            time.monotonic()
        )


        if response.status_code in {
            401,
            403,
        }:

            raise EvidenceSourceError(
                "The NAFDAC Greenbook "
                "refused the lookup request."
            )


        if response.status_code == 429:

            raise EvidenceSourceError(
                "The NAFDAC Greenbook "
                "is rate-limiting requests."
            )


        if response.status_code >= 500:

            raise EvidenceSourceError(
                "The NAFDAC Greenbook "
                "is temporarily unavailable."
            )


        try:

            payload = (
                response.json()
            )

        except ValueError as error:

            raise EvidenceSourceError(
                "The NAFDAC Greenbook returned "
                "an unexpected response."
            ) from error


        if not isinstance(
            payload,
            dict,
        ):

            raise EvidenceSourceError(
                "Unexpected Greenbook format."
            )


        if payload.get(
            "error"
        ):

            raise EvidenceSourceError(
                "The NAFDAC Greenbook reported: "
                f"{payload['error']}"
            )


        rows = (
            payload.get(
                "data"
            )
        )


        if not isinstance(
            rows,
            list,
        ):

            raise EvidenceSourceError(
                "Greenbook did not return "
                "a product-record list."
            )


        return payload


    def search_registration(
        self,
        registration_number: str,
        *,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:

        target = (
            normalize_registration_number(
                registration_number
            )
        )


        if not target:
            return []


        payload = (
            self._request_rows(
                registration_number,
                length=max_results,
            )
        )


        rows = (
            payload.get(
                "data",
                [],
            )
        )


        exact_matches = []


        for row in rows:

            if not isinstance(
                row,
                dict,
            ):
                continue


            record = (
                normalize_greenbook_record(
                    row
                )
            )


            official_number = (
                normalize_registration_number(
                    record.get(
                        "registration_number"
                    )
                )
            )


            if official_number == target:

                exact_matches.append(
                    record
                )


        return exact_matches


    def search_product_name(
        self,
        product_name: str,
        *,
        max_results: int = 25,
    ) -> List[Dict[str, Any]]:

        if not product_name:
            return []


        query = (
            product_name.strip()
        )


        if not query:
            return []


        payload = (
            self._request_rows(
                query,
                length=max_results,
            )
        )


        rows = (
            payload.get(
                "data",
                [],
            )
        )


        records = []


        for row in rows:

            if isinstance(
                row,
                dict,
            ):

                records.append(
                    normalize_greenbook_record(
                        row
                    )
                )


        return records


def check_greenbook_registration(
    registration_number: str,
) -> Dict[str, Any]:
    """
    Main registration lookup used by Before Use.

    Flow:

        Greenbook
            ↓
        exact match?
            ├─ yes → return Greenbook evidence
            └─ no  → automatically check NAPAMS

    Keeping the original function name avoids breaking
    the rest of the Before Use application.
    """

    client = (
        GreenbookClient()
    )


    try:

        records = (
            client.search_registration(
                registration_number
            )
        )


        # ---------------------------------------------
        # GREENBOOK EXACT MATCH
        # ---------------------------------------------

        if records:

            return {
                "source_ok": True,

                "source_name": (
                    "NAFDAC Greenbook"
                ),

                "query": (
                    registration_number
                ),

                "records": (
                    records
                ),

                "error": None,

                "greenbook_exact_match_found": (
                    True
                ),

                "napams_checked": (
                    False
                ),

                "napams": None,
            }


        # ---------------------------------------------
        # GREENBOOK MISS → NAPAMS AUTOMATION
        # ---------------------------------------------

        napams_result = (
            check_napams_registration(
                registration_number
            )
        )


        return {
            "source_ok": True,

            "source_name": (
                "NAFDAC Greenbook + NAPAMS"
            ),

            "query": (
                registration_number
            ),

            "records": [],

            "error": None,

            "greenbook_exact_match_found": (
                False
            ),

            "napams_checked": (
                True
            ),

            "napams": (
                napams_result
            ),

            "broader_registry_name": (
                "NAFDAC NAPAMS"
            ),

            "broader_registry_url": (
                NAPAMS_URL
            ),
        }


    except EvidenceSourceError as error:

        # Even when Greenbook itself fails, try the
        # broader registry independently.

        napams_result = (
            check_napams_registration(
                registration_number
            )
        )


        return {
            "source_ok": (
                bool(
                    napams_result.get(
                        "source_ok"
                    )
                )
            ),

            "source_name": (
                "NAFDAC Greenbook + NAPAMS"
            ),

            "query": (
                registration_number
            ),

            "records": [],

            "error": (
                str(error)
            ),

            "greenbook_exact_match_found": (
                False
            ),

            "napams_checked": (
                True
            ),

            "napams": (
                napams_result
            ),

            "broader_registry_name": (
                "NAFDAC NAPAMS"
            ),

            "broader_registry_url": (
                NAPAMS_URL
            ),
        }