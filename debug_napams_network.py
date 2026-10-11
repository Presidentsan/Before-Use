import re
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


NAPAMS_URL = "https://registration.nafdac.gov.ng/Home/"
TEST_NUMBER = "02-7346"

WAIT_SECONDS = 20
POLL_MS = 250


def is_napams_url(
    url: str,
) -> bool:
    try:
        hostname = (
            urlparse(url).hostname
            or ""
        ).lower()

        return (
            hostname
            ==
            "registration.nafdac.gov.ng"
        )

    except Exception:
        return False


def safe_post_data(
    request,
):
    """
    Avoid crashing on binary request bodies.
    """

    try:
        content_type = (
            request.headers.get(
                "content-type",
                ""
            )
            or ""
        ).lower()

    except Exception:
        content_type = ""

    textual_types = (
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/",
    )

    if not any(
        item in content_type
        for item in textual_types
    ):
        return (
            "[not displayed: "
            f"{content_type or 'unknown content type'}]"
        )

    try:
        return (
            request.post_data
            or None
        )

    except Exception as exc:
        return (
            "[could not decode: "
            f"{type(exc).__name__}]"
        )


def main():
    with sync_playwright() as playwright:

        browser = (
            playwright.chromium.launch(
                headless=True,
            )
        )

        context = (
            browser.new_context(
                locale="en-NG",
                viewport={
                    "width": 1280,
                    "height": 900,
                },
            )
        )

        page = (
            context.new_page()
        )

        page.set_default_timeout(
            35000
        )

        captured = []

        # =================================================
        # REQUEST LOGGER
        # =================================================

        def on_request(
            request,
        ):
            try:
                if not is_napams_url(
                    request.url
                ):
                    return

                captured.append(
                    {
                        "direction": "REQUEST",
                        "method": (
                            request.method
                        ),
                        "resource_type": (
                            request.resource_type
                        ),
                        "url": (
                            request.url
                        ),
                        "content_type": (
                            request.headers.get(
                                "content-type"
                            )
                        ),
                        "post_data": (
                            safe_post_data(
                                request
                            )
                        ),
                    }
                )

            except Exception as exc:
                captured.append(
                    {
                        "direction": (
                            "REQUEST_LOGGER_ERROR"
                        ),
                        "error": (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                    }
                )

        # =================================================
        # RESPONSE LOGGER
        # =================================================

        def on_response(
            response,
        ):
            try:
                if not is_napams_url(
                    response.url
                ):
                    return

                request = (
                    response.request
                )

                captured.append(
                    {
                        "direction": "RESPONSE",
                        "method": (
                            request.method
                        ),
                        "resource_type": (
                            request.resource_type
                        ),
                        "status": (
                            response.status
                        ),
                        "url": (
                            response.url
                        ),
                        "content_type": (
                            response.headers.get(
                                "content-type"
                            )
                        ),
                    }
                )

            except Exception as exc:
                captured.append(
                    {
                        "direction": (
                            "RESPONSE_LOGGER_ERROR"
                        ),
                        "error": (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                    }
                )

        page.on(
            "request",
            on_request,
        )

        page.on(
            "response",
            on_response,
        )

        # =================================================
        # LOAD HOMEPAGE
        # =================================================

        print(
            "Opening NAPAMS..."
        )

        homepage_start = (
            time.perf_counter()
        )

        page.goto(
            NAPAMS_URL,
            wait_until=(
                "domcontentloaded"
            ),
            timeout=35000,
        )

        print(
            "Homepage seconds:",
            round(
                time.perf_counter()
                -
                homepage_start,
                2,
            ),
        )

        print(
            "Page URL before Verify:",
            page.url,
        )

        # Remove initial page-load traffic.
        captured.clear()

        # =================================================
        # FIND INPUT
        # =================================================

        input_locator = (
            page.get_by_placeholder(
                re.compile(
                    r"(certificate|nafdac)",
                    re.IGNORECASE,
                )
            )
        )

        if (
            input_locator.count()
            ==
            0
        ):
            input_locator = (
                page.locator(
                    'input[type="text"]'
                )
            )

        if (
            input_locator.count()
            ==
            0
        ):
            raise RuntimeError(
                "NAPAMS verification input "
                "could not be located."
            )

        input_locator.first.fill(
            TEST_NUMBER
        )

        # =================================================
        # VERIFY BUTTON
        # =================================================

        verify_button = (
            page.get_by_role(
                "button",
                name=re.compile(
                    r"^\s*verify\s*$",
                    re.IGNORECASE,
                ),
            )
        )

        if (
            verify_button.count()
            ==
            0
        ):
            raise RuntimeError(
                "Verify button could not "
                "be located."
            )

        print()
        print(
            "Clicking Verify..."
        )

        verify_start = (
            time.perf_counter()
        )

        verify_button.first.click()

        deadline = (
            time.monotonic()
            +
            WAIT_SECONDS
        )

        result_found = False

        while (
            time.monotonic()
            <
            deadline
        ):
            page.wait_for_timeout(
                POLL_MS
            )

            try:
                body_text = (
                    page
                    .locator(
                        "body"
                    )
                    .inner_text()
                )

            except Exception:
                continue

            if (
                "Product Name:"
                in body_text
                and
                TEST_NUMBER
                in body_text
            ):
                result_found = True
                break

            lower = (
                body_text.lower()
            )

            negative_phrases = [
                "no product found",
                "product not found",
                "no record found",
                "invalid nafdac number",
                "no matching product",
            ]

            if any(
                phrase in lower
                for phrase
                in negative_phrases
            ):
                break

        print(
            "Visible result seconds:",
            round(
                time.perf_counter()
                -
                verify_start,
                2,
            ),
        )

        print(
            "Result detected:",
            result_found,
        )

        print(
            "Page URL after Verify:",
            page.url,
        )

        page.wait_for_timeout(
            500
        )

        # =================================================
        # FILTER IMPORTANT REQUESTS
        # =================================================

        print()
        print(
            "=" * 70
        )

        print(
            "REQUESTS AFTER CLICKING VERIFY"
        )

        print(
            "=" * 70
        )

        important = []

        for item in captured:

            resource_type = (
                item.get(
                    "resource_type"
                )
            )

            method = (
                item.get(
                    "method"
                )
            )

            url = (
                item.get(
                    "url",
                    ""
                )
            )

            if (
                resource_type
                in {
                    "document",
                    "xhr",
                    "fetch",
                }
                or
                method
                in {
                    "POST",
                    "PUT",
                    "PATCH",
                }
                or
                TEST_NUMBER
                in url
            ):
                important.append(
                    item
                )

        if not important:
            print(
                "No obvious verification "
                "request was identified."
            )

            print()
            print(
                "Showing all same-domain "
                "traffic instead:"
            )

            important = (
                captured
            )

        for index, item in enumerate(
            important,
            start=1,
        ):

            print()
            print(
                f"--- {index} ---"
            )

            for key, value in (
                item.items()
            ):
                print(
                    f"{key}: {value}"
                )

        browser.close()


if __name__ == "__main__":
    main()