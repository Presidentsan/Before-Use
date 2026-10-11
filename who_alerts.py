import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


WHO_ALERTS_URL = (
    "https://www.who.int/teams/"
    "regulation-prequalification/"
    "incidents-and-SF/"
    "full-list-of-who-medical-product-alerts"
)

WHO_BASE_URL = "https://www.who.int"

TIMEOUT_SECONDS = 20

HEADERS = {
    "User-Agent": (
        "BeforeUse/0.3 "
        "(consumer product safety prototype)"
    )
}


class WHOAlertSourceError(RuntimeError):
    pass


def _normalize_text(
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


def _normalize_identifier(
    value: Optional[str],
) -> str:
    if not value:
        return ""

    return re.sub(
        r"[^A-Z0-9]",
        "",
        str(value).upper(),
    )


def _important_tokens(
    value: Optional[str],
) -> List[str]:
    if not value:
        return []

    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "oral",
        "tablet",
        "tablets",
        "capsule",
        "capsules",
        "syrup",
        "solution",
        "injection",
        "caplet",
        "caplets",
        "medicine",
        "drug",
        "pharmaceuticals",
        "limited",
        "ltd",
        "plc",
        "nigeria",
    }

    tokens = re.findall(
        r"[a-z0-9]+",
        str(value).lower(),
    )

    return [
        token
        for token in tokens
        if (
            token not in stop_words
            and len(token) >= 3
        )
    ]


def _extract_visible_text(
    html_text: str,
) -> str:
    soup = BeautifulSoup(
        html_text,
        "html.parser",
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
        ]
    ):
        tag.decompose()

    return " ".join(
        soup.stripped_strings
    )


class WHOAlertClient:

    def __init__(
        self,
        timeout: int = TIMEOUT_SECONDS,
        min_request_interval: float = 0.5,
    ):
        self.timeout = timeout

        self.min_request_interval = (
            min_request_interval
        )

        self.session = requests.Session()

        self.session.headers.update(
            HEADERS
        )

        self._last_request = 0.0


    def _wait(self):
        elapsed = (
            time.monotonic()
            -
            self._last_request
        )

        remaining = (
            self.min_request_interval
            -
            elapsed
        )

        if remaining > 0:
            time.sleep(
                remaining
            )


    def _get(
        self,
        url: str,
    ):
        self._wait()

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
            )

        except requests.RequestException as error:
            raise WHOAlertSourceError(
                "WHO Medical Product Alerts "
                "could not be reached."
            ) from error

        self._last_request = (
            time.monotonic()
        )

        if response.status_code == 429:
            raise WHOAlertSourceError(
                "WHO is temporarily "
                "rate-limiting requests."
            )

        if response.status_code >= 500:
            raise WHOAlertSourceError(
                "WHO Medical Product Alerts "
                "are temporarily unavailable."
            )

        response.raise_for_status()

        return response


    def _get_alert_index(
        self,
    ) -> List[Dict[str, str]]:

        response = self._get(
            WHO_ALERTS_URL
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        alerts = []

        seen_urls = set()

        for anchor in soup.find_all(
            "a",
            href=True,
        ):
            title = anchor.get_text(
                " ",
                strip=True,
            )

            href = anchor.get(
                "href",
                "",
            )

            lowered = (
                f"{title} {href}"
            ).lower()

            if (
                "medical product alert"
                not in lowered
                and
                "medical-product-alert"
                not in lowered
            ):
                continue

            url = urljoin(
                WHO_BASE_URL,
                href,
            )

            if (
                "who.int"
                not in url
            ):
                continue

            if url in seen_urls:
                continue

            seen_urls.add(
                url
            )

            alerts.append(
                {
                    "title": title,
                    "url": url,
                }
            )

        return alerts


    def _candidate_alerts(
        self,
        *,
        product_name=None,
        manufacturer=None,
    ):

        index = (
            self._get_alert_index()
        )

        product_tokens = (
            _important_tokens(
                product_name
            )
        )

        manufacturer_tokens = (
            _important_tokens(
                manufacturer
            )
        )

        useful_tokens = (
            product_tokens
            +
            manufacturer_tokens
        )

        if not useful_tokens:
            return []


        candidates = []

        for alert in index:

            searchable = (
                _normalize_text(
                    alert["title"]
                )
            )

            matched_tokens = [
                token
                for token
                in useful_tokens
                if token in searchable
            ]

            if matched_tokens:

                item = dict(
                    alert
                )

                item[
                    "index_matched_tokens"
                ] = matched_tokens

                candidates.append(
                    item
                )


        return candidates[:15]


    def search(
        self,
        *,
        product_name=None,
        registration_number=None,
        batch_number=None,
        manufacturer=None,
    ) -> Dict[str, Any]:

        candidates = (
            self._candidate_alerts(
                product_name=(
                    product_name
                ),
                manufacturer=(
                    manufacturer
                ),
            )
        )


        normalized_product = (
            _normalize_text(
                product_name
            )
        )

        product_tokens = (
            _important_tokens(
                product_name
            )
        )

        manufacturer_tokens = (
            _important_tokens(
                manufacturer
            )
        )

        target_batch = (
            _normalize_identifier(
                batch_number
            )
        )

        target_registration = (
            _normalize_identifier(
                registration_number
            )
        )


        matches = []


        for candidate in candidates:

            try:
                response = self._get(
                    candidate["url"]
                )

            except Exception:
                continue


            page_text = (
                _extract_visible_text(
                    response.text
                )
            )

            normalized_page = (
                _normalize_text(
                    page_text
                )
            )

            identifier_page = (
                _normalize_identifier(
                    page_text
                )
            )


            exact_product_match = bool(
                normalized_product
                and
                normalized_product
                in normalized_page
            )


            product_token_matches = [
                token
                for token
                in product_tokens
                if token in normalized_page
            ]


            manufacturer_token_matches = [
                token
                for token
                in manufacturer_tokens
                if token in normalized_page
            ]


            batch_match = bool(
                target_batch
                and
                target_batch
                in identifier_page
            )


            registration_match = bool(
                target_registration
                and
                target_registration
                in identifier_page
            )


            reasons = []


            if batch_match:
                reasons.append(
                    "exact_batch_match"
                )


            if registration_match:
                reasons.append(
                    "exact_registration_match"
                )


            if exact_product_match:
                reasons.append(
                    "exact_product_name_match"
                )

            elif product_token_matches:
                reasons.append(
                    "product_name_relevance"
                )


            if manufacturer_token_matches:
                reasons.append(
                    "manufacturer_relevance"
                )


            if not reasons:
                continue


            # ---------------------------------------------
            # Significance hierarchy
            # ---------------------------------------------
            #
            # high:
            # exact batch or exact identifier appears.
            #
            # relevant:
            # exact product name appears in WHO alert.
            #
            # possible:
            # weaker token-level relevance only.
            #
            # None of these is an authenticity percentage.
            # ---------------------------------------------

            if (
                batch_match
                or
                registration_match
            ):

                significance = "high"


            elif exact_product_match:

                significance = "relevant"


            else:

                significance = "possible"


            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            heading = soup.find(
                "h1"
            )

            if heading:
                title = heading.get_text(
                    " ",
                    strip=True,
                )
            else:
                title = candidate[
                    "title"
                ]


            matches.append(
                {
                    "title": title,
                    "source_name": (
                        "World Health Organization"
                    ),
                    "source_url": (
                        candidate["url"]
                    ),
                    "significance": (
                        significance
                    ),
                    "match_reasons": (
                        reasons
                    ),
                    "batch_match": (
                        batch_match
                    ),
                    "registration_match": (
                        registration_match
                    ),
                    "exact_product_match": (
                        exact_product_match
                    ),
                    "product_token_matches": (
                        product_token_matches
                    ),
                    "manufacturer_token_matches": (
                        manufacturer_token_matches
                    ),
                    "excerpt": (
                        page_text[:1000]
                    ),
                }
            )


        priority = {
            "high": 0,
            "relevant": 1,
            "possible": 2,
        }


        matches.sort(
            key=lambda item: (
                priority.get(
                    item[
                        "significance"
                    ],
                    9,
                )
            )
        )


        return {
            "source_ok": True,
            "source_name": (
                "WHO Medical Product Alerts"
            ),
            "source_url": (
                WHO_ALERTS_URL
            ),
            "query": {
                "product_name": (
                    product_name
                ),
                "registration_number": (
                    registration_number
                ),
                "batch_number": (
                    batch_number
                ),
                "manufacturer": (
                    manufacturer
                ),
            },
            "records": (
                matches
            ),
            "error": None,
        }


def check_who_safety_alerts(
    *,
    product_name=None,
    registration_number=None,
    batch_number=None,
    manufacturer=None,
) -> Dict[str, Any]:

    client = WHOAlertClient()

    try:

        return client.search(
            product_name=(
                product_name
            ),
            registration_number=(
                registration_number
            ),
            batch_number=(
                batch_number
            ),
            manufacturer=(
                manufacturer
            ),
        )

    except WHOAlertSourceError as error:

        return {
            "source_ok": False,
            "source_name": (
                "WHO Medical Product Alerts"
            ),
            "source_url": (
                WHO_ALERTS_URL
            ),
            "query": {
                "product_name": (
                    product_name
                ),
                "registration_number": (
                    registration_number
                ),
                "batch_number": (
                    batch_number
                ),
                "manufacturer": (
                    manufacturer
                ),
            },
            "records": [],
            "error": str(
                error
            ),
        }