import re
import time
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


NAFDAC_BASE_URL = "https://nafdac.gov.ng/"

# Hard live budget for the safety-alert source.
# The source must never hold the whole Evidence Passport
# for minutes.
TOTAL_BUDGET_SECONDS = 5.0

# One individual NAFDAC request must also be short.
PER_REQUEST_TIMEOUT_SECONDS = 2.0

MAX_CANDIDATE_URLS = 6
MAX_RESULTS = 3


HEADERS = {
    "User-Agent": (
        "BeforeUse/0.6 "
        "(consumer product safety prototype)"
    )
}


ALERT_URL_MARKERS = (
    "public-alert",
    "recall",
    "safety-alert",
    "recalls-and-alerts",
)


GENERIC_PRODUCT_WORDS: Set[str] = {
    "tablet",
    "tablets",
    "caplet",
    "caplets",
    "capsule",
    "capsules",
    "syrup",
    "syrups",
    "cough",
    "mixture",
    "suspension",
    "solution",
    "oral",
    "liquid",
    "cream",
    "ointment",
    "injection",
    "injectable",
    "drops",
    "medicine",
    "medicines",
    "medication",
    "medications",
    "drug",
    "drugs",
    "product",
    "products",
    "paediatric",
    "pediatric",
    "adult",
    "children",
    "child",
    "powder",
    "gel",
    "lotion",
    "soap",
    "wash",
}


GENERIC_COMPANY_WORDS: Set[str] = {
    "limited",
    "ltd",
    "plc",
    "inc",
    "company",
    "companies",
    "co",
    "industry",
    "industries",
    "pharmaceutical",
    "pharmaceuticals",
    "pharma",
    "laboratory",
    "laboratories",
    "labs",
    "pvt",
    "private",
    "nigeria",
    "nigerian",
    "consumer",
    "healthcare",
    "health",
    "products",
    "product",
    "group",
    "international",
}


class SafetyAlertSourceError(
    RuntimeError
):
    pass


class SafetyAlertBudgetExceeded(
    RuntimeError
):
    pass


# =========================================================
# NORMALISATION
# =========================================================

def _normalize(
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
    """
    Formatting normalisation only.

    Important:
    O23479 and 023479 remain different.

    Before Use must never silently convert
    a letter O to the number zero.
    """

    if not value:
        return ""

    return re.sub(
        r"[^A-Z0-9]",
        "",
        str(value).upper(),
    )


def _tokenize(
    value: Optional[str],
) -> List[str]:

    return re.findall(
        r"[a-z0-9]+",
        str(
            value
            or ""
        ).lower(),
    )


def _distinctive_tokens(
    value: Optional[str],
    *,
    generic_words: Set[str],
    min_length: int = 3,
) -> List[str]:

    return [
        token
        for token
        in _tokenize(
            value
        )
        if (
            token
            not in generic_words
            and
            len(token)
            >= min_length
        )
    ]


# =========================================================
# HTML / URL HELPERS
# =========================================================

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


def _looks_like_alert_url(
    url: str,
    anchor_text: str = "",
) -> bool:

    value = (
        f"{url} {anchor_text}"
    ).lower()

    return any(
        marker in value
        for marker
        in ALERT_URL_MARKERS
    )


def _is_generic_alert_index_url(
    url: str,
    title: str = "",
) -> bool:

    parsed = urlparse(
        url
    )

    path = (
        parsed.path
        or ""
    ).strip(
        "/"
    ).lower()

    title_norm = (
        _normalize(
            title
        )
    )

    if (
        "/category/"
        in
        f"/{path}/"
    ):
        return True

    if path.startswith(
        "category/"
    ):
        return True

    if path.startswith(
        "tag/"
    ):
        return True

    if path.startswith(
        "author/"
    ):
        return True

    generic_paths = {
        "recalls-and-alerts",
        "safety-alerts",
        "recalls",
    }

    if path in generic_paths:
        return True

    generic_titles = {
        "recalls and safety alerts nafdac",
        "recalls and alerts nafdac",
        "safety alerts nafdac",
    }

    if (
        title_norm
        in generic_titles
    ):
        return True

    return False


# =========================================================
# SIMILARITY HELPERS
# =========================================================

def _best_window_similarity(
    target: Optional[str],
    page_text: str,
    *,
    extra_window_tokens: int = 3,
) -> float:

    target_norm = (
        _normalize(
            target
        )
    )

    if not target_norm:
        return 0.0

    page_norm = (
        _normalize(
            page_text
        )
    )

    if not page_norm:
        return 0.0

    if (
        target_norm
        in page_norm
    ):
        return 1.0

    target_tokens = (
        _tokenize(
            target_norm
        )
    )

    page_tokens = (
        _tokenize(
            page_norm
        )
    )

    if (
        not target_tokens
        or
        not page_tokens
    ):
        return 0.0

    target_len = len(
        target_tokens
    )

    min_size = max(
        1,
        target_len - 1,
    )

    max_size = min(
        len(
            page_tokens
        ),
        target_len
        +
        extra_window_tokens,
    )

    best = 0.0

    for size in range(
        min_size,
        max_size + 1,
    ):

        for start in range(
            0,
            len(
                page_tokens
            )
            -
            size
            +
            1,
        ):

            window = " ".join(
                page_tokens[
                    start:
                    start + size
                ]
            )

            score = (
                SequenceMatcher(
                    None,
                    target_norm,
                    window,
                )
                .ratio()
            )

            if (
                score
                >
                best
            ):
                best = score

            if (
                best
                >=
                0.97
            ):
                return best

    return best


def _token_similarity(
    left: str,
    right: str,
) -> float:

    return (
        SequenceMatcher(
            None,
            left,
            right,
        )
        .ratio()
    )


# =========================================================
# PRODUCT MATCHING
# =========================================================

def _product_match(
    product_name: Optional[str],
    page_text: str,
) -> Tuple[
    bool,
    float,
]:

    target_norm = (
        _normalize(
            product_name
        )
    )

    if not target_norm:
        return (
            False,
            0.0,
        )

    distinctive = (
        _distinctive_tokens(
            product_name,
            generic_words=(
                GENERIC_PRODUCT_WORDS
            ),
            min_length=3,
        )
    )

    # Generic descriptions such as
    # "cough syrup" must never identify
    # a specific product by themselves.
    if not distinctive:
        return (
            False,
            0.0,
        )

    page_norm = (
        _normalize(
            page_text
        )
    )

    if (
        target_norm
        in page_norm
    ):
        return (
            True,
            1.0,
        )

    page_tokens = set(
        _tokenize(
            page_norm
        )
    )

    best_token_score = 0.0
    matched_tokens = 0

    for target_token in (
        distinctive
    ):

        token_best = 0.0

        for page_token in (
            page_tokens
        ):

            if (
                abs(
                    len(
                        target_token
                    )
                    -
                    len(
                        page_token
                    )
                )
                >
                3
            ):
                continue

            score = (
                _token_similarity(
                    target_token,
                    page_token,
                )
            )

            token_best = max(
                token_best,
                score,
            )

        best_token_score = max(
            best_token_score,
            token_best,
        )

        if (
            token_best
            >=
            0.84
        ):
            matched_tokens += 1

    window_score = (
        _best_window_similarity(
            product_name,
            page_text,
        )
    )

    score = max(
        best_token_score,
        window_score,
    )

    if (
        matched_tokens
        >=
        1
    ):
        return (
            True,
            score,
        )

    if (
        window_score
        >=
        0.82
    ):
        return (
            True,
            score,
        )

    return (
        False,
        score,
    )


# =========================================================
# MANUFACTURER MATCHING
# =========================================================

def _manufacturer_match(
    manufacturer: Optional[str],
    page_text: str,
) -> Tuple[
    bool,
    float,
]:
    """
    Manufacturer matching is deliberately strict.

    Generic company words cannot establish
    manufacturer identity.
    """

    target_norm = (
        _normalize(
            manufacturer
        )
    )

    if not target_norm:
        return (
            False,
            0.0,
        )

    page_norm = (
        _normalize(
            page_text
        )
    )

    if not page_norm:
        return (
            False,
            0.0,
        )

    distinctive = (
        _distinctive_tokens(
            manufacturer,
            generic_words=(
                GENERIC_COMPANY_WORDS
            ),
            min_length=4,
        )
    )

    if not distinctive:
        return (
            False,
            0.0,
        )

    if (
        target_norm
        in page_norm
    ):
        return (
            True,
            1.0,
        )

    page_tokens = set(
        _tokenize(
            page_norm
        )
    )

    token_scores = []

    for target_token in (
        distinctive
    ):

        best = 0.0

        for page_token in (
            page_tokens
        ):

            if (
                len(
                    target_token
                )
                <
                5
            ):
                continue

            if (
                len(
                    page_token
                )
                <
                5
            ):
                continue

            if (
                abs(
                    len(
                        target_token
                    )
                    -
                    len(
                        page_token
                    )
                )
                >
                3
            ):
                continue

            score = (
                _token_similarity(
                    target_token,
                    page_token,
                )
            )

            best = max(
                best,
                score,
            )

        token_scores.append(
            best
        )

    strongest_token = (
        max(
            token_scores
        )
        if token_scores
        else
        0.0
    )

    window_score = (
        _best_window_similarity(
            manufacturer,
            page_text,
        )
    )

    reported_score = max(
        window_score,
        strongest_token,
    )

    if (
        strongest_token
        >=
        0.88
    ):
        return (
            True,
            reported_score,
        )

    if (
        window_score
        >=
        0.88
    ):
        return (
            True,
            reported_score,
        )

    return (
        False,
        reported_score,
    )


# =========================================================
# RESULT FILTERING
# =========================================================

def _has_exact_identifier_match(
    record: Dict,
) -> bool:

    return bool(
        record.get(
            "batch_match"
        )
        or
        record.get(
            "registration_match"
        )
    )


def _filter_matches_for_display(
    matches: List[Dict],
) -> List[Dict]:

    if not matches:
        return []

    exact_identifier_matches = [
        record
        for record
        in matches
        if (
            _has_exact_identifier_match(
                record
            )
        )
    ]

    # Exact batch / registration evidence
    # takes priority over weaker evidence.
    if exact_identifier_matches:
        return (
            exact_identifier_matches
        )

    medium_matches = [
        record
        for record
        in matches
        if (
            record.get(
                "significance"
            )
            ==
            "medium"
        )
    ]

    if medium_matches:
        return (
            medium_matches
        )

    possible_matches = [
        record
        for record
        in matches
        if (
            record.get(
                "significance"
            )
            ==
            "possible"
        )
    ]

    return (
        possible_matches[
            :MAX_RESULTS
        ]
    )


# =========================================================
# NAFDAC CLIENT
# =========================================================

class NafdacSafetyAlertClient:

    def __init__(
        self,
        *,
        total_budget_seconds: float = (
            TOTAL_BUDGET_SECONDS
        ),
        request_timeout_seconds: float = (
            PER_REQUEST_TIMEOUT_SECONDS
        ),
    ):

        self.total_budget_seconds = float(
            total_budget_seconds
        )

        self.request_timeout_seconds = float(
            request_timeout_seconds
        )

        self.session = (
            requests.Session()
        )

        self.session.headers.update(
            HEADERS
        )

        self.started_at = (
            time.monotonic()
        )

        self.deadline = (
            self.started_at
            +
            self.total_budget_seconds
        )

        self.checked_urls: List[
            str
        ] = []

        self.discovery_methods: List[
            str
        ] = []

    # =====================================================
    # BUDGET
    # =====================================================

    def _remaining(
        self,
    ) -> float:

        return max(
            0.0,
            self.deadline
            -
            time.monotonic(),
        )

    def _require_budget(
        self,
        minimum: float = 0.15,
    ):

        if (
            self._remaining()
            <=
            minimum
        ):
            raise (
                SafetyAlertBudgetExceeded(
                    "NAFDAC safety-alert lookup "
                    "reached its "
                    f"{self.total_budget_seconds:.0f}"
                    "-second live-check budget."
                )
            )

    # =====================================================
    # HTTP
    # =====================================================

    def _get(
        self,
        url,
        *,
        params=None,
    ):

        self._require_budget()

        remaining = (
            self._remaining()
        )

        timeout = min(
            self.request_timeout_seconds,
            max(
                0.25,
                remaining,
            ),
        )

        try:

            response = (
                self.session.get(
                    url,
                    params=params,
                    timeout=(
                        min(
                            timeout,
                            1.5,
                        ),
                        timeout,
                    ),
                )
            )

        except (
            requests.Timeout
        ) as error:

            if (
                self._remaining()
                <=
                0.25
            ):
                raise (
                    SafetyAlertBudgetExceeded(
                        "NAFDAC safety-alert lookup "
                        "reached its "
                        f"{self.total_budget_seconds:.0f}"
                        "-second live-check budget."
                    )
                ) from error

            raise (
                SafetyAlertSourceError(
                    "A NAFDAC safety-alert "
                    "request timed out."
                )
            ) from error

        except (
            requests.RequestException
        ) as error:

            raise (
                SafetyAlertSourceError(
                    "NAFDAC safety-alert pages "
                    "could not be reached."
                )
            ) from error

        if (
            response.status_code
            ==
            429
        ):
            raise (
                SafetyAlertSourceError(
                    "NAFDAC is temporarily "
                    "rate-limiting requests."
                )
            )

        if (
            response.status_code
            >=
            500
        ):
            raise (
                SafetyAlertSourceError(
                    "NAFDAC safety-alert pages "
                    "are temporarily unavailable."
                )
            )

        response.raise_for_status()

        return response

    # =====================================================
    # WORDPRESS SEARCH
    # =====================================================

    def _search_wordpress_api(
        self,
        query: str,
        *,
        max_links: int = 4,
    ) -> List[str]:

        self._require_budget()

        endpoint = urljoin(
            NAFDAC_BASE_URL,
            "wp-json/wp/v2/search",
        )

        response = self._get(
            endpoint,
            params={
                "search": query,
                "per_page": max_links,
                "subtype": "post",
            },
        )

        try:
            payload = (
                response.json()
            )

        except Exception:
            return []

        if not isinstance(
            payload,
            list,
        ):
            return []

        found = []

        for item in payload:

            if not isinstance(
                item,
                dict,
            ):
                continue

            href = (
                item.get(
                    "url"
                )
                or
                item.get(
                    "link"
                )
                or
                ""
            )

            title = str(
                item.get(
                    "title"
                )
                or
                ""
            )

            if not href:
                continue

            href = urljoin(
                NAFDAC_BASE_URL,
                href,
            )

            if not href.startswith(
                NAFDAC_BASE_URL
            ):
                continue

            if not (
                _looks_like_alert_url(
                    href,
                    title,
                )
            ):
                continue

            if (
                _is_generic_alert_index_url(
                    href,
                    title,
                )
            ):
                continue

            if (
                href
                not in
                found
            ):
                found.append(
                    href
                )

            if (
                len(
                    found
                )
                >=
                max_links
            ):
                break

        return found

    # =====================================================
    # NORMAL SITE SEARCH FALLBACK
    # =====================================================

    def _search_site(
        self,
        query: str,
        *,
        max_links: int = 4,
    ) -> List[str]:

        self._require_budget()

        response = (
            self._get(
                NAFDAC_BASE_URL,
                params={
                    "s": query,
                },
            )
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        found = []

        for anchor in soup.find_all(
            "a",
            href=True,
        ):

            href = (
                urljoin(
                    NAFDAC_BASE_URL,
                    anchor.get(
                        "href",
                        "",
                    ),
                )
            )

            text = (
                anchor.get_text(
                    " ",
                    strip=True,
                )
            )

            if not (
                _looks_like_alert_url(
                    href,
                    text,
                )
            ):
                continue

            if not (
                href.startswith(
                    NAFDAC_BASE_URL
                )
            ):
                continue

            if (
                _is_generic_alert_index_url(
                    href,
                    text,
                )
            ):
                continue

            if (
                href
                not in
                found
            ):
                found.append(
                    href
                )

            if (
                len(
                    found
                )
                >=
                max_links
            ):
                break

        return found

    # =====================================================
    # QUERY PRIORITY
    # =====================================================

    def _query_variants(
        self,
        *,
        product_name=None,
        registration_number=None,
        batch_number=None,
        manufacturer=None,
    ) -> List[str]:

        values: List[str] = []

        # Exact identifiers first.
        for value in (
            batch_number,
            registration_number,
        ):

            if (
                value
                and
                str(
                    value
                ).strip()
            ):
                values.append(
                    str(
                        value
                    ).strip()
                )

        product_tokens = (
            _distinctive_tokens(
                product_name,
                generic_words=(
                    GENERIC_PRODUCT_WORDS
                ),
                min_length=3,
            )
        )

        if product_tokens:

            values.append(
                " ".join(
                    product_tokens
                )
            )

        manufacturer_tokens = (
            _distinctive_tokens(
                manufacturer,
                generic_words=(
                    GENERIC_COMPANY_WORDS
                ),
                min_length=4,
            )
        )

        if manufacturer_tokens:

            values.append(
                " ".join(
                    manufacturer_tokens
                )
            )

        deduped = []

        for value in values:

            clean = (
                value.strip()
            )

            if (
                clean
                and
                clean
                not in
                deduped
            ):
                deduped.append(
                    clean
                )

        # Keep the live search small.
        return (
            deduped[
                :4
            ]
        )

    # =====================================================
    # EVALUATE ONE ALERT PAGE
    # =====================================================

    def _evaluate_url(
        self,
        url: str,
        *,
        product_name=None,
        registration_number=None,
        batch_number=None,
        manufacturer=None,
    ):

        self._require_budget()

        if (
            _is_generic_alert_index_url(
                url
            )
        ):
            return None

        if (
            url
            not in
            self.checked_urls
        ):
            self.checked_urls.append(
                url
            )

        try:

            response = (
                self._get(
                    url
                )
            )

        except (
            SafetyAlertBudgetExceeded
        ):
            raise

        except Exception:
            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        title = ""

        if soup.title:

            title = (
                soup.title.get_text(
                    " ",
                    strip=True,
                )
            )

        if (
            _is_generic_alert_index_url(
                url,
                title,
            )
        ):
            return None

        page_text = (
            _extract_visible_text(
                response.text
            )
        )

        if not page_text:
            return None

        identifier_text = (
            _normalize_identifier(
                page_text
            )
        )

        target_reg = (
            _normalize_identifier(
                registration_number
            )
        )

        target_batch = (
            _normalize_identifier(
                batch_number
            )
        )

        registration_match = bool(
            target_reg
            and
            target_reg
            in
            identifier_text
        )

        batch_match = bool(
            target_batch
            and
            target_batch
            in
            identifier_text
        )

        (
            product_match,
            product_score,
        ) = (
            _product_match(
                product_name,
                page_text,
            )
        )

        (
            manufacturer_match,
            manufacturer_score,
        ) = (
            _manufacturer_match(
                manufacturer,
                page_text,
            )
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

        if product_match:
            reasons.append(
                "product_name_match"
            )

        if manufacturer_match:
            reasons.append(
                "manufacturer_match"
            )

        if not reasons:
            return None

        # Exact identifiers remain highest confidence.
        if (
            batch_match
            or
            registration_match
        ):
            significance = (
                "high"
            )

        elif (
            product_match
            and
            manufacturer_match
            and
            manufacturer_score
            >=
            0.80
        ):
            significance = (
                "medium"
            )

        else:
            significance = (
                "possible"
            )

        return {
            "title": (
                title
                or
                "NAFDAC safety alert"
            ),

            "source_name": (
                "NAFDAC"
            ),

            "source_url": (
                url
            ),

            "url": (
                url
            ),

            "significance": (
                significance
            ),

            "match_reasons": (
                reasons
            ),

            "product_match": (
                product_match
            ),

            "registration_match": (
                registration_match
            ),

            "batch_match": (
                batch_match
            ),

            "manufacturer_match": (
                manufacturer_match
            ),

            "product_similarity": (
                round(
                    product_score,
                    3,
                )
            ),

            "manufacturer_similarity": (
                round(
                    manufacturer_score,
                    3,
                )
            ),

            "excerpt": (
                page_text[
                    :1200
                ]
            ),
        }

    # =====================================================
    # FINALISE MATCHES
    # =====================================================

    def _finalise_matches(
        self,
        matches: List[Dict],
    ) -> List[Dict]:

        deduped: Dict[
            str,
            Dict,
        ] = {}

        priority_value = {
            "high": 3,
            "medium": 2,
            "possible": 1,
        }

        for record in matches:

            url = (
                record.get(
                    "source_url"
                )
            )

            if not url:
                continue

            previous = (
                deduped.get(
                    url
                )
            )

            if previous is None:

                deduped[
                    url
                ] = (
                    record
                )

                continue

            if (
                priority_value.get(
                    record.get(
                        "significance"
                    ),
                    0,
                )
                >
                priority_value.get(
                    previous.get(
                        "significance"
                    ),
                    0,
                )
            ):

                deduped[
                    url
                ] = (
                    record
                )

        filtered = (
            _filter_matches_for_display(
                list(
                    deduped.values()
                )
            )
        )

        sort_priority = {
            "high": 0,
            "medium": 1,
            "possible": 2,
        }

        filtered.sort(
            key=lambda item: (
                sort_priority.get(
                    item.get(
                        "significance"
                    ),
                    9,
                ),
                item.get(
                    "title"
                )
                or
                "",
            )
        )

        return (
            filtered[
                :MAX_RESULTS
            ]
        )

    # =====================================================
    # MAIN SEARCH
    # =====================================================

    def search(
        self,
        *,
        product_name=None,
        registration_number=None,
        batch_number=None,
        manufacturer=None,
    ):

        queries = (
            self._query_variants(
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
        )

        matches: List[
            Dict
        ] = []

        candidate_urls: List[
            str
        ] = []

        try:

            for query in queries:

                self._require_budget()

                # WordPress API is tried first because
                # it is lighter than a full search page.
                try:

                    found = (
                        self._search_wordpress_api(
                            query,
                            max_links=4,
                        )
                    )

                    if (
                        "nafdac_wordpress_search"
                        not in
                        self.discovery_methods
                    ):

                        self.discovery_methods.append(
                            "nafdac_wordpress_search"
                        )

                except (
                    SafetyAlertBudgetExceeded
                ):
                    raise

                except Exception:

                    found = []

                # Only use the heavier site search when
                # WordPress returns nothing and enough
                # time remains.
                if (
                    not found
                    and
                    self._remaining()
                    >
                    1.25
                ):

                    try:

                        found = (
                            self._search_site(
                                query,
                                max_links=4,
                            )
                        )

                        if (
                            "nafdac_site_search"
                            not in
                            self.discovery_methods
                        ):

                            self.discovery_methods.append(
                                "nafdac_site_search"
                            )

                    except (
                        SafetyAlertBudgetExceeded
                    ):
                        raise

                    except Exception:

                        found = []

                for url in found:

                    if (
                        _is_generic_alert_index_url(
                            url
                        )
                    ):
                        continue

                    if (
                        url
                        not in
                        candidate_urls
                    ):

                        candidate_urls.append(
                            url
                        )

                    if (
                        len(
                            candidate_urls
                        )
                        >=
                        MAX_CANDIDATE_URLS
                    ):
                        break

                # Evaluate immediately so an exact
                # identifier can return early.
                for url in list(
                    candidate_urls
                ):

                    if (
                        url
                        in
                        self.checked_urls
                    ):
                        continue

                    self._require_budget()

                    result = (
                        self._evaluate_url(
                            url,
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
                    )

                    if result:

                        matches.append(
                            result
                        )

                        # Exact batch/registration alert:
                        # stop immediately.
                        if (
                            _has_exact_identifier_match(
                                result
                            )
                        ):

                            final = (
                                self._finalise_matches(
                                    matches
                                )
                            )

                            return {
                                "source_ok": True,

                                "source_name": (
                                    "NAFDAC recalls and "
                                    "safety alerts"
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
                                    final
                                ),

                                "checked_url_count": (
                                    len(
                                        set(
                                            self.checked_urls
                                        )
                                    )
                                ),

                                "discovery_methods": (
                                    list(
                                        self.discovery_methods
                                    )
                                ),

                                "coverage_note": (
                                    "A matching exact identifier "
                                    "was found during the bounded "
                                    "live NAFDAC alert check."
                                ),

                                "timed_out": False,

                                "elapsed_seconds": (
                                    round(
                                        time.monotonic()
                                        -
                                        self.started_at,
                                        3,
                                    )
                                ),

                                "error": None,
                            }

                if (
                    len(
                        candidate_urls
                    )
                    >=
                    MAX_CANDIDATE_URLS
                ):
                    break

            final = (
                self._finalise_matches(
                    matches
                )
            )

            return {
                "source_ok": True,

                "source_name": (
                    "NAFDAC recalls and "
                    "safety alerts"
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
                    final
                ),

                "checked_url_count": (
                    len(
                        set(
                            self.checked_urls
                        )
                    )
                ),

                "discovery_methods": (
                    list(
                        self.discovery_methods
                    )
                ),

                "coverage_note": (
                    "Best-effort bounded search of "
                    "official NAFDAC alert pages. "
                    "A zero-match result is not proof "
                    "that no alert exists."
                ),

                "timed_out": False,

                "elapsed_seconds": (
                    round(
                        time.monotonic()
                        -
                        self.started_at,
                        3,
                    )
                ),

                "error": None,
            }

        except (
            SafetyAlertBudgetExceeded
        ) as error:

            # If an exact match had already been found,
            # the function would have returned above.
            # Otherwise timeout = incomplete source.
            return {
                "source_ok": False,

                "source_name": (
                    "NAFDAC recalls and "
                    "safety alerts"
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

                "checked_url_count": (
                    len(
                        set(
                            self.checked_urls
                        )
                    )
                ),

                "discovery_methods": (
                    list(
                        self.discovery_methods
                    )
                ),

                "coverage_note": (
                    "The bounded live NAFDAC alert "
                    "check reached its time budget. "
                    "An incomplete check does not mean "
                    "that no alert exists."
                ),

                "timed_out": True,

                "elapsed_seconds": (
                    round(
                        time.monotonic()
                        -
                        self.started_at,
                        3,
                    )
                ),

                "error": (
                    str(
                        error
                    )
                ),
            }


# =========================================================
# PUBLIC FUNCTION
# =========================================================

def check_nafdac_safety_alerts(
    *,
    product_name=None,
    registration_number=None,
    batch_number=None,
    manufacturer=None,
):

    client = (
        NafdacSafetyAlertClient()
    )

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

    except (
        SafetyAlertBudgetExceeded
    ) as error:

        return {
            "source_ok": False,

            "source_name": (
                "NAFDAC recalls and "
                "safety alerts"
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

            "checked_url_count": 0,

            "discovery_methods": [],

            "coverage_note": (
                "The bounded live NAFDAC alert "
                "check reached its time budget. "
                "An incomplete check does not mean "
                "that no alert exists."
            ),

            "timed_out": True,

            "error": (
                str(
                    error
                )
            ),
        }

    except (
        SafetyAlertSourceError
    ) as error:

        return {
            "source_ok": False,

            "source_name": (
                "NAFDAC recalls and "
                "safety alerts"
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

            "checked_url_count": 0,

            "discovery_methods": [],

            "coverage_note": (
                "The source could not be checked. "
                "Source unavailable does not mean "
                "no alert exists."
            ),

            "timed_out": False,

            "error": (
                str(
                    error
                )
            ),
        }

    except Exception as error:

        return {
            "source_ok": False,

            "source_name": (
                "NAFDAC recalls and "
                "safety alerts"
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

            "checked_url_count": 0,

            "discovery_methods": [],

            "coverage_note": (
                "The source could not be completed. "
                "An incomplete source check does not "
                "mean no alert exists."
            ),

            "timed_out": False,

            "error": (
                str(
                    error
                )
            ),
        }