import re
import shutil

import time

from typing import Any, Dict, Optional



from playwright.sync_api import sync_playwright





NAPAMS_URL = "https://registration.nafdac.gov.ng/Home/"



PAGE_TIMEOUT_MS = 45000



# NAPAMS itself has been observed taking 9–12+ seconds

# after form submission before showing the product result.

RESULT_WAIT_SECONDS = 22



RESULT_POLL_SECONDS = 0.25





# =========================================================

# NORMALISATION

# =========================================================



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

    value: Optional[str],

) -> Optional[str]:

    if value is None:

        return None



    value = re.sub(

        r"\s+",

        " ",

        str(value),

    ).strip()



    return value or None





def _compact_text(

    value: str,

) -> str:

    return re.sub(

        r"\s+",

        " ",

        value or "",

    ).strip()





# =========================================================

# BOILERPLATE FILTER

# =========================================================



def _is_napams_boilerplate(

    value: Optional[str],

) -> bool:

    if not value:

        return False



    normalized = (

        _compact_text(

            str(value)

        )

        .strip()

        .lower()

        .rstrip(":")

    )



    exact_boilerplate = {

        "product",

        "products",

        "details",

        "product details",

        "view details",

        "more details",

        "record details",

        "registration details",

        "verify",

        "verify product",

        "verify products",

        "verify your product",

        "use nafdac number to verify product",

        "enter the nafdac number of the product to verify",

        "success",

        "product found",

        "success, product found",

        "are you a registered client?",

        "are you a registered client",

    }



    if normalized in exact_boilerplate:

        return True



    boilerplate_fragments = [

        "use nafdac number to verify",

        "enter the nafdac number",

        "sign up or register",

        "sign in or login",

        "complete application",

        "make payment",

        "application processing",

        "do you have an account",

        "access the portal",

        "how can i register",

        "how do i respond",

        "how do i pay",

        "how do i process",

    ]



    return any(

        fragment in normalized

        for fragment in boilerplate_fragments

    )





# =========================================================

# RESULT REGION

# =========================================================



def _extract_result_region(

    page_text: str,

    registration_number: str,

) -> str:

    """

    Isolate the actual NAPAMS product-result area and

    avoid FAQ/site text where possible.

    """



    compact = _compact_text(

        page_text

    )



    if not compact:

        return ""



    lower = compact.lower()



    start_markers = [

        "success, product found",

        "product found",

    ]



    end_markers = [

        "sign up or register",

        "sign in or login",

        "complete application",

        "faq ",

    ]



    start_index = -1



    for marker in start_markers:

        position = lower.find(

            marker

        )



        if (

            position >= 0

            and

            (

                start_index < 0

                or position < start_index

            )

        ):

            start_index = position



    if start_index >= 0:

        end_index = len(

            compact

        )



        for marker in end_markers:

            position = lower.find(

                marker,

                start_index + 1,

            )



            if (

                position >= 0

                and

                position < end_index

            ):

                end_index = position



        result = (

            compact[

                start_index:end_index

            ]

            .strip()

        )



        if result:

            return result



    # Conservative fallback:

    # return a bounded area around the registration number.

    target = normalize_registration_number(

        registration_number

    )



    lines = [

        line.strip()

        for line in (

            page_text

            or ""

        ).splitlines()

        if line.strip()

    ]



    matching_indexes = []



    for index, line in enumerate(

        lines

    ):

        normalized_line = (

            normalize_registration_number(

                line

            )

        )



        if (

            target

            and

            target in normalized_line

        ):

            matching_indexes.append(

                index

            )



    if not matching_indexes:

        return compact



    anchor = matching_indexes[-1]



    start = max(

        0,

        anchor - 15,

    )



    end = min(

        len(lines),

        anchor + 25,

    )



    return "\n".join(

        lines[start:end]

    )





# =========================================================

# FIELD EXTRACTION

# =========================================================



_FIELD_BOUNDARY_LABELS = [

    "Product Name",

    "Brand Name",

    "Product Category",

    "Category",

    "Product Source",

    "Manufacturer Name",

    "Manufacturer",

    "Applicant Name",

    "Applicant",

    "Company",

    "Date Approved",

    "Approval Date",

    "Registration Expiry Date",

    "Certificate Expiry Date",

    "Expiry Date",

    "NAFDAC No",

    "NAFDAC Number",

    "Registration Number",

    "Certificate Number",

    "Registration Status",

    "Product Status",

    "Active Ingredient",

    "Ingredients",

]





def _boundary_pattern() -> str:

    ordered = sorted(

        _FIELD_BOUNDARY_LABELS,

        key=len,

        reverse=True,

    )



    return "|".join(

        re.escape(label)

        for label in ordered

    )





_FIELD_BOUNDARY_PATTERN = (

    _boundary_pattern()

)





def _extract_labeled_value(

    text: str,

    labels: list[str],

    *,

    require_colon: bool = False,

) -> Optional[str]:

    source = text or ""



    for label in labels:



        if require_colon:

            separator = (

                r"\s*:\s*"

            )

        else:

            separator = (

                r"\s*:?[ **\t**]*"

            )



        pattern = re.compile(

            rf"(?is)(?:^|\s)"

            rf"{re.escape(label)}"

            rf"{separator}"

            rf"(.+?)"

            rf"(?=\s+(?:{_FIELD_BOUNDARY_PATTERN})\s*:|$)"

        )



        match = pattern.search(

            source

        )



        if not match:

            continue



        candidate = _clean_text(

            match.group(1)

        )



        if (

            candidate

            and

            not _is_napams_boilerplate(

                candidate

            )

        ):

            return candidate



    return None





def _extract_generic_product_value(

    text: str,

) -> Optional[str]:

    """

    Only accept Product: when a literal colon exists.

    This prevents PRODUCT headings becoming product names.

    """



    return _extract_labeled_value(

        text,

        [

            "Product",

        ],

        require_colon=True,

    )





# =========================================================

# STRUCTURED RECORD

# =========================================================



def _extract_record(

    result_text: str,

    registration_number: str,

) -> Dict[str, Any]:



    region = _extract_result_region(

        result_text,

        registration_number,

    )



    product_name = (

        _extract_labeled_value(

            region,

            [

                "Product Name",

                "Brand Name",

            ],

        )

    )



    if not product_name:

        product_name = (

            _extract_generic_product_value(

                region

            )

        )



    if (

        product_name

        and

        _is_napams_boilerplate(

            product_name

        )

    ):

        product_name = None



    manufacturer = (

        _extract_labeled_value(

            region,

            [

                "Manufacturer Name",

                "Manufacturer",

                "Applicant Name",

                "Applicant",

                "Company",

            ],

        )

    )



    # IMPORTANT:

    # do not use generic "Status".

    # The NAPAMS FAQ contains that ordinary word.

    status = (

        _extract_labeled_value(

            region,

            [

                "Registration Status",

                "Product Status",

            ],

        )

    )



    expiry_date = (

        _extract_labeled_value(

            region,

            [

                "Registration Expiry Date",

                "Certificate Expiry Date",

                "Expiry Date",

            ],

        )

    )



    category = (

        _extract_labeled_value(

            region,

            [

                "Product Category",

                "Category",

            ],

        )

    )



    return {

        "product_name": (

            _clean_text(

                product_name

            )

        ),

        "registration_number": (

            registration_number

        ),

        "applicant": (

            _clean_text(

                manufacturer

            )

        ),

        "status": (

            _clean_text(

                status

            )

        ),

        "registration_expiry_date": (

            _clean_text(

                expiry_date

            )

        ),

        "category": (

            _clean_text(

                category

            )

        ),

        "source_name": (

            "NAFDAC NAPAMS"

        ),

        "source_url": (

            NAPAMS_URL

        ),

    }





# =========================================================

# RESULT CLASSIFICATION

# =========================================================



_NEGATIVE_PHRASES = [

    "no product found",

    "product not found",

    "no record found",

    "record not found",

    "invalid nafdac number",

    "no result found",

    "no matching product",

]





_POSITIVE_PHRASES = [

    "success, product found",

    "product found",

    "product name:",

    "nafdac no:",

    "manufacturer:",

]





def _contains_explicit_negative(

    text: str,

) -> bool:

    lower = (

        _compact_text(

            text

        )

        .lower()

    )



    return any(

        phrase in lower

        for phrase in _NEGATIVE_PHRASES

    )





def _looks_like_positive_result(

    text: str,

    registration_number: str,

) -> bool:



    compact = (

        _compact_text(

            text

        )

    )



    lower = compact.lower()



    target = (

        normalize_registration_number(

            registration_number

        )

    )



    normalized_text = (

        normalize_registration_number(

            compact

        )

    )



    if (

        not target

        or

        target not in normalized_text

    ):

        return False



    return any(

        phrase in lower

        for phrase in _POSITIVE_PHRASES

    )





# =========================================================

# WAIT FOR RESULT

# =========================================================



def _wait_for_napams_result(

    page,

    registration_number: str,

) -> Dict[str, Any]:



    started = time.monotonic()



    deadline = (

        started

        +

        RESULT_WAIT_SECONDS

    )



    last_text = ""



    while (

        time.monotonic()

        <

        deadline

    ):



        try:

            page.wait_for_timeout(

                int(

                    RESULT_POLL_SECONDS

                    *

                    1000

                )

            )



        except Exception:

            # NAPAMS submits a document POST.

            # During navigation Playwright may briefly lose

            # the old execution context. Keep waiting.

            time.sleep(

                RESULT_POLL_SECONDS

            )



        try:

            current_text = (

                page

                .locator(

                    "body"

                )

                .inner_text(

                    timeout=3000

                )

            )



        except Exception:

            continue



        if not current_text:

            continue



        last_text = current_text



        if _contains_explicit_negative(

            current_text

        ):

            return {

                "classification": (

                    "negative"

                ),

                "text": current_text,

                "wait_seconds": round(

                    time.monotonic()

                    -

                    started,

                    2,

                ),

            }



        if _looks_like_positive_result(

            current_text,

            registration_number,

        ):

            return {

                "classification": (

                    "positive"

                ),

                "text": current_text,

                "wait_seconds": round(

                    time.monotonic()

                    -

                    started,

                    2,

                ),

            }



    return {

        "classification": (

            "timeout"

        ),

        "text": last_text,

        "wait_seconds": round(

            time.monotonic()

            -

            started,

            2,

        ),

    }





# =========================================================

# MAIN NAPAMS CHECK

# =========================================================



def check_napams_registration(

    registration_number: str,

) -> Dict[str, Any]:



    registration_number = (

        str(

            registration_number

            or ""

        )

        .strip()

    )



    target = (

        normalize_registration_number(

            registration_number

        )

    )



    if not target:

        return {

            "source_ok": True,

            "source_name": (

                "NAFDAC NAPAMS"

            ),

            "source_url": (

                NAPAMS_URL

            ),

            "query": (

                registration_number

            ),

            "status": (

                "inconclusive"

            ),

            "found": False,

            "record": None,

            "result_text": None,

            "wait_seconds": None,

            "error": None,

        }



    browser = None



    try:

        with sync_playwright() as playwright:



            # On Streamlit Cloud, packages.txt installs system Chromium.
            # Locally, Playwright's installed Chromium remains supported.
            system_chromium = (
                shutil.which("chromium")
                or shutil.which("chromium-browser")
            )

            launch_options = {"headless": True}
            if system_chromium:
                launch_options["executable_path"] = system_chromium

            print(
                "NAPAMS BROWSER:",
                "system chromium" if system_chromium else "playwright bundled chromium",
                flush=True,
            )
            browser = playwright.chromium.launch(**launch_options)

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

                PAGE_TIMEOUT_MS

            )



            # =================================================

            # OPEN NAPAMS

            # =================================================



            page.goto(

                NAPAMS_URL,

                wait_until=(

                    "domcontentloaded"

                ),

                timeout=(

                    PAGE_TIMEOUT_MS

                ),

            )



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

                registration_number

            )



            # =================================================

            # FIND VERIFY CONTROL

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

                    "NAPAMS Verify button "

                    "could not be located."

                )



            # =================================================

            # SUBMIT

            # =================================================



            verify_button.first.click(

                no_wait_after=True

            )



            result = (

                _wait_for_napams_result(

                    page,

                    registration_number,

                )

            )



            after_text = (

                result.get(

                    "text"

                )

                or ""

            )



            wait_seconds = (

                result.get(

                    "wait_seconds"

                )

            )



            classification = (

                result.get(

                    "classification"

                )

            )



            # =================================================

            # EXPLICIT NEGATIVE

            # =================================================



            if (

                classification

                ==

                "negative"

            ):



                return {

                    "source_ok": True,

                    "source_name": (

                        "NAFDAC NAPAMS"

                    ),

                    "source_url": (

                        NAPAMS_URL

                    ),

                    "query": (

                        registration_number

                    ),

                    "status": (

                        "not_found"

                    ),

                    "found": False,

                    "record": None,

                    "result_text": (

                        _compact_text(

                            after_text

                        )[

                            :1800

                        ]

                    ),

                    "wait_seconds": (

                        wait_seconds

                    ),

                    "error": None,

                }



            # =================================================

            # POSITIVE RESULT

            # =================================================



            if (

                classification

                ==

                "positive"

            ):



                region = (

                    _extract_result_region(

                        after_text,

                        registration_number,

                    )

                )



                record = (

                    _extract_record(

                        after_text,

                        registration_number,

                    )

                )



                official_number = (

                    normalize_registration_number(

                        record.get(

                            "registration_number"

                        )

                    )

                )



                product_context = (

                    bool(

                        record.get(

                            "product_name"

                        )

                    )

                    or

                    bool(

                        record.get(

                            "applicant"

                        )

                    )

                    or

                    "product name:"

                    in region.lower()

                )



                if (

                    official_number

                    ==

                    target

                    and

                    product_context

                ):

                    return {

                        "source_ok": True,

                        "source_name": (

                            "NAFDAC NAPAMS"

                        ),

                        "source_url": (

                            NAPAMS_URL

                        ),

                        "query": (

                            registration_number

                        ),

                        "status": (

                            "match_found"

                        ),

                        "found": True,

                        "record": (

                            record

                        ),

                        "result_text": (

                            _compact_text(

                                region

                            )[

                                :1800

                            ]

                        ),

                        "wait_seconds": (

                            wait_seconds

                        ),

                        "error": None,

                    }



            # =================================================

            # COULD NOT SAFELY CLASSIFY

            # =================================================



            return {

                "source_ok": True,

                "source_name": (

                    "NAFDAC NAPAMS"

                ),

                "source_url": (

                    NAPAMS_URL

                ),

                "query": (

                    registration_number

                ),

                "status": (

                    "inconclusive"

                ),

                "found": False,

                "record": None,

                "result_text": (

                    _compact_text(

                        after_text

                    )[

                        :1800

                    ]

                    if after_text

                    else None

                ),

                "wait_seconds": (

                    wait_seconds

                ),

                "error": (

                    "NAPAMS did not return a result "

                    "that could be classified safely "

                    f"within {RESULT_WAIT_SECONDS} seconds."

                ),

            }



    except Exception as exc:

        # Report the browser failure without logging tokens or session data.
        print("NAPAMS BROWSER ERROR:", type(exc).__name__, str(exc)[:1000], flush=True)
        return {

            "source_ok": False,

            "source_name": (

                "NAFDAC NAPAMS"

            ),

            "source_url": (

                NAPAMS_URL

            ),

            "query": (

                registration_number

            ),

            "status": (

                "source_unavailable"

            ),

            "found": False,

            "record": None,

            "result_text": None,

            "wait_seconds": None,

            "error": (

                f"{type(exc).__name__}: "

                f"{exc}"

            ),

        }



    finally:

        if browser is not None:

            try:

                browser.close()

            except Exception:

                pass