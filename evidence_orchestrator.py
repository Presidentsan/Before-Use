from registry_comparison import compare_field
import re

import time



from concurrent.futures import (

    ThreadPoolExecutor,

    TimeoutError as FutureTimeoutError,

)



from difflib import SequenceMatcher

from typing import Any, Dict, Optional



from evidence_checker import (

    check_greenbook_registration,

)



from historical_evidence import (

    find_historical_evidence,

)



from napams_browser import (

    check_napams_registration,

)



from safety_alerts import (

    check_nafdac_safety_alerts,

)



from who_alerts import (

    check_who_safety_alerts,

)



from result_engine import (

    build_registration_result,

)





# =========================================================

# PERFORMANCE SETTINGS

# =========================================================



NAFDAC_ALERT_EXTRA_WAIT_SECONDS = 8

WHO_ALERT_EXTRA_WAIT_SECONDS = 6





# =========================================================

# ROUTING CONSTANTS

# =========================================================



NAPAMS_FIRST_CATEGORIES = {

    "cosmetic",

    "cosmetics",

    "personal care",

    "oral care",

    "household chemical",

    "household chemicals",

    "chemical",

    "chemicals",

    "food",

    "foods",

    "beverage",

    "beverages",

    "packaged water",

    "water",

}



MEDICAL_CATEGORIES = {

    "drug",

    "drugs",

    "medicine",

    "medicines",

    "pharmaceutical",

    "pharmaceuticals",

    "medicinal product",

    "medical product",

}



NAPAMS_FIRST_PRODUCT_TERMS = {

    "toothpaste",

    "mouthwash",

    "shampoo",

    "conditioner",

    "hair conditioner",

    "hair cream",

    "hair relaxer",

    "hair dye",

    "body lotion",

    "body cream",

    "body wash",

    "face wash",

    "facial cleanser",

    "cleanser",

    "moisturizer",

    "moisturiser",

    "deodorant",

    "antiperspirant",

    "perfume",

    "fragrance",

    "lipstick",

    "mascara",

    "foundation",

    "nail polish",

    "cosmetic",

    "cosmetics",

    "soft drink",

    "fruit juice",

    "bottled water",

    "packaged water",

    "seasoning",

    "noodles",

    "biscuit",

    "biscuits",

    "cereal",

}



NAPAMS_FIRST_BRAND_HINTS = {

    "closeup",

    "close-up",

}





# =========================================================

# PERFORMANCE HELPERS

# =========================================================



def _print_timing(

    label: str,

    seconds: float,

):

    print(

        f"BEFORE USE TIMING | "

        f"{label}: {seconds:.2f}s",

        flush=True,

    )





def _timed_call(

    label,

    function,

    *args,

    **kwargs,

):

    started = time.perf_counter()



    try:

        return function(

            *args,

            **kwargs,

        )



    finally:

        elapsed = (

            time.perf_counter()

            -

            started

        )



        _print_timing(

            label,

            elapsed,

        )





def _timed_out_source(

    source_name: str,

    seconds: int,

):

    return {

        "source_ok": False,

        "source_name": source_name,

        "records": [],

        "error": (

            f"{source_name} did not complete within "

            f"the {seconds}-second evidence-check time budget."

        ),

        "timed_out": True,

    }





def _collect_future_with_budget(

    future,

    *,

    label: str,

    source_name: str,

    extra_wait_seconds: int,

):

    """

    Allow an already-running background source a small amount

    of extra time before returning control to the user.



    Important:

    A timeout is represented as source_ok=False.

    It is NEVER represented as zero alerts.

    """



    if future is None:

        return _skipped_source(

            source_name,

            "This source was not required for this product route.",

        )



    if future.done():

        try:

            return future.result()



        except Exception as error:

            print(

                f"BEFORE USE SOURCE ERROR | "

                f"{label}: {error}",

                flush=True,

            )



            return {

                "source_ok": False,

                "source_name": source_name,

                "records": [],

                "error": str(error),

            }



    wait_started = (

        time.perf_counter()

    )



    try:

        result = future.result(

            timeout=extra_wait_seconds

        )



        wait_elapsed = (

            time.perf_counter()

            -

            wait_started

        )



        _print_timing(

            f"{label} EXTRA WAIT",

            wait_elapsed,

        )



        return result



    except FutureTimeoutError:

        _print_timing(

            f"{label} EXTRA WAIT TIMEOUT",

            extra_wait_seconds,

        )



        return _timed_out_source(

            source_name,

            extra_wait_seconds,

        )



    except Exception as error:

        print(

            f"BEFORE USE SOURCE ERROR | "

            f"{label}: {error}",

            flush=True,

        )



        return {

            "source_ok": False,

            "source_name": source_name,

            "records": [],

            "error": str(error),

        }





# =========================================================

# GENERIC HELPERS

# =========================================================



def _clean(

    value: Any,

) -> str:

    return re.sub(

        r"\s+",

        " ",

        str(

            value

            or ""

        ),

    ).strip().lower()





def _normalise_compare(

    value: Any,

) -> str:

    return re.sub(

        r"[^a-z0-9]+",

        " ",

        _clean(

            value

        ),

    ).strip()





def _similarity(

    left: Any,

    right: Any,

) -> Optional[float]:



    left_norm = (

        _normalise_compare(

            left

        )

    )



    right_norm = (

        _normalise_compare(

            right

        )

    )



    if (

        not left_norm

        or

        not right_norm

    ):

        return None



    if (

        left_norm

        ==

        right_norm

    ):

        return 1.0



    return SequenceMatcher(

        None,

        left_norm,

        right_norm,

    ).ratio()





def _field_check(*, field, user_value, official_value, threshold):
    return compare_field(field=field, user_value=user_value,
                         official_value=official_value, threshold=threshold)


def _alerts_by_significance(

    evidence: Dict[

        str,

        Any,

    ],

    significance: str,

):

    return [

        record

        for record

        in (

            evidence.get(

                "records"

            )

            or []

        )

        if (

            record.get(

                "significance"

            )

            ==

            significance

        )

    ]





def _skipped_source(

    source_name: str,

    reason: str,

) -> Dict[str, Any]:



    return {

        "source_ok": True,

        "source_name": source_name,

        "records": [],

        "error": None,

        "skipped": True,

        "skip_reason": reason,

    }





def _empty_source(

    source_name: str,

) -> Dict[str, Any]:



    return {

        "source_ok": True,

        "source_name": source_name,

        "records": [],

        "error": None,

    }





def _safety_source_incomplete(

    nafdac_alerts: Dict[str, Any],

    who_alerts: Dict[str, Any],

) -> bool:

    return bool(

        not nafdac_alerts.get(

            "source_ok",

            True,

        )

        or

        not who_alerts.get(

            "source_ok",

            True,

        )

    )





def _registration_source_incomplete(

    greenbook: Dict[str, Any],

) -> bool:

    return bool(

        not greenbook.get(

            "source_ok",

            True,

        )

    )





def _with_safety_limitation(

    summary: str,

    next_action: str,

    *,

    nafdac_alerts: Dict[str, Any],

    who_alerts: Dict[str, Any],

):

    limitations = []



    if not nafdac_alerts.get(

        "source_ok",

        True,

    ):

        limitations.append(

            "the live NAFDAC safety-alert check did not complete"

        )



    if not who_alerts.get(

        "source_ok",

        True,

    ):

        limitations.append(

            "the WHO Medical Product Alert check did not complete"

        )



    if not limitations:

        return (

            summary,

            next_action,

        )



    if len(limitations) == 1:

        limitation_text = (

            limitations[0]

        )

    else:

        limitation_text = (

            " and ".join(

                limitations

            )

        )



    updated_summary = (

        f"{summary} Safety evidence limitation: "

        f"{limitation_text}. Before Use therefore cannot "

        "say that all relevant safety-alert sources were fully checked."

    )



    updated_next_action = (

        f"{next_action} You may also retry the incomplete safety check "

        "or verify directly with the relevant regulator."

    )



    return (

        updated_summary,

        updated_next_action,

    )





# =========================================================

# PRODUCT ROUTING

# =========================================================



def classify_evidence_route(

    product_state: Dict[

        str,

        Any,

    ],

) -> Dict[str, str]:



    product_state = (

        product_state

        or {}

    )



    category = (

        _clean(

            product_state.get(

                "category"

            )

            or

            product_state.get(

                "product_category"

            )

            or

            product_state.get(

                "product_type"

            )

        )

    )



    product_name = (

        _clean(

            product_state.get(

                "product_name"

            )

        )

    )



    if (

        category

        in

        MEDICAL_CATEGORIES

    ):

        return {

            "route": (

                "greenbook_first"

            ),

            "reason": (

                "The confirmed product category is "

                "medical/pharmaceutical, so current "

                "Greenbook evidence is checked first."

            ),

        }



    if (

        category

        in

        NAPAMS_FIRST_CATEGORIES

    ):

        return {

            "route": (

                "napams_first"

            ),

            "reason": (

                "The confirmed product category is outside "

                "the medicine-first Greenbook route, so "

                "NAPAMS is checked first."

            ),

        }



    for term in (

        NAPAMS_FIRST_PRODUCT_TERMS

    ):

        if re.search(

            rf"\b{re.escape(term)}\b",

            product_name,

            flags=re.IGNORECASE,

        ):

            return {

                "route": (

                    "napams_first"

                ),

                "reason": (

                    f"The confirmed product name contains "

                    f"'{term}', which is a strong non-medicine "

                    "product signal, so NAPAMS is checked first."

                ),

            }



    if any(

        hint

        in

        product_name

        for hint

        in

        NAPAMS_FIRST_BRAND_HINTS

    ):

        return {

            "route": (

                "napams_first"

            ),

            "reason": (

                "The confirmed product name is a known "

                "non-medicine retail product, so "

                "NAPAMS is checked first."

            ),

        }



    return {

        "route": (

            "greenbook_first"

        ),

        "reason": (

            "The product type is not clear enough to safely "

            "skip Greenbook, so Before Use keeps the "

            "conservative Greenbook-first route."

        ),

    }





# =========================================================

# NAPAMS RESULT BUILDER

# =========================================================



def _build_napams_only_registration_result(

    product_state: Dict[

        str,

        Any,

    ],

    napams: Dict[

        str,

        Any,

    ],

) -> Dict[str, Any]:



    registration_number = (

        product_state.get(

            "nafdac_number"

        )

    )



    status = (

        napams.get(

            "status"

        )

    )



    if (

        napams.get(

            "source_ok"

        )

        and

        napams.get(

            "found"

        )

        and

        status

        ==

        "match_found"

    ):

        record = (

            napams.get(

                "record"

            )

            or {}

        )



        field_checks = [

            {

                "field": (

                    "NAFDAC registration number"

                ),

                "user_value": (

                    registration_number

                ),

                "official_value": (

                    record.get(

                        "registration_number"

                    )

                    or

                    registration_number

                ),

                "state": (

                    "match"

                ),

                "similarity": (

                    1.0

                ),

            }

        ]



        if record.get(

            "product_name"

        ):

            field_checks.append(

                _field_check(

                    field=(

                        "Product name"

                    ),

                    user_value=(

                        product_state.get(

                            "product_name"

                        )

                    ),

                    official_value=(

                        record.get(

                            "product_name"

                        )

                    ),

                    threshold=0.72,

                )

            )



        if record.get(

            "applicant"

        ):

            field_checks.append(

                _field_check(

                    field=(

                        "Manufacturer / applicant"

                    ),

                    user_value=(

                        product_state.get(

                            "manufacturer"

                        )

                    ),

                    official_value=(

                        record.get(

                            "applicant"

                        )

                    ),

                    threshold=0.65,

                )

            )



        mismatches = [

            item

            for item

            in field_checks

            if (

                item.get(

                    "state"

                )

                ==

                "mismatch"

            )

        ]



        if mismatches:

            names = ", ".join(

                item[

                    "field"

                ]

                for item

                in mismatches

            )



            return {

                "code": (

                    "details_mismatch"

                ),

                "level": (

                    "warning"

                ),

                "headline": (

                    "Some details do not match "

                    "the NAPAMS record"

                ),

                "summary": (

                    "NAPAMS returned the confirmed "

                    "NAFDAC registration number, but "

                    "Before Use found a mismatch in: "

                    f"{names}."

                ),

                "claim_limit": (

                    "A valid registration number can appear "

                    "on another physical product. This does "

                    "not prove that the item in your hand "

                    "is genuine."

                ),

                "next_action": (

                    "Compare the product label carefully "

                    "with the NAPAMS result before use."

                ),

                "field_checks": (

                    field_checks

                ),

                "official_record": (

                    record

                ),

                "candidate_count": (

                    1

                ),

                "registry_used": (

                    "NAFDAC NAPAMS"

                ),

                "napams_result_text": (

                    napams.get(

                        "result_text"

                    )

                ),

                "napams_error": (

                    napams.get(

                        "error"

                    )

                ),

            }



        partials = [c for c in field_checks if c.get("state") == "needs_verification"]
        if partials:
            return {
                "code": "details_need_verification",
                "level": "limited",
                "headline": "Registration found; verify the exact product details",
                "summary": "NAPAMS returned the registration number, but the available descriptions do not establish an exact variant match.",
                "claim_limit": "A registration match does not authenticate the physical product.",
                "next_action": "Compare the exact product variant on the pack with the NAPAMS record before use.",
                "field_checks": field_checks,
                "official_record": record,
                "candidate_count": 1,
                "registry_used": "NAFDAC NAPAMS",
                "napams_result_text": napams.get("result_text"),
                "napams_error": napams.get("error"),
            }

        return {

            "code": (

                "napams_record_match"

            ),

            "level": (

                "positive"

            ),

            "headline": (

                "NAFDAC registration found in NAPAMS"

            ),

            "summary": (

                "The confirmed NAFDAC number was returned "

                "by the official NAPAMS product-verification "

                "service, and the comparable details did not "

                "conflict with the record returned."

            ),

            "claim_limit": (

                "This confirms an official registration-record "

                "result. It does not prove that the individual "

                "product is genuine, untampered, correctly "

                "stored, or safe to use."

            ),

            "next_action": (

                "Continue checking the physical product "

                "and any relevant safety alerts."

            ),

            "field_checks": (

                field_checks

            ),

            "official_record": (

                record

            ),

            "candidate_count": (

                1

            ),

            "registry_used": (

                "NAFDAC NAPAMS"

            ),

            "napams_result_text": (

                napams.get(

                    "result_text"

                )

            ),

            "napams_error": (

                napams.get(

                    "error"

                )

            ),

        }



    if (

        napams.get(

            "source_ok"

        )

        and

        status

        ==

        "not_found"

    ):

        return {

            "code": (

                "registration_not_found_in_connected_sources"

            ),

            "level": (

                "warning"

            ),

            "headline": (

                "Registration not returned by NAPAMS"

            ),

            "summary": (

                "NAPAMS did not return a matching product "

                "for the confirmed NAFDAC registration number "

                "during this check."

            ),

            "claim_limit": (

                "A NAPAMS miss does not prove that the "

                "individual product is counterfeit, "

                "unregistered, or unsafe. Public records "

                "can be incomplete or temporarily unavailable."

            ),

            "next_action": (

                "Recheck the number on the product and verify "

                "directly with NAFDAC if needed."

            ),

            "field_checks": [],

            "official_record": None,

            "candidate_count": 0,

            "registry_used": (

                "NAFDAC NAPAMS"

            ),

            "napams_result_text": (

                napams.get(

                    "result_text"

                )

            ),

            "napams_error": (

                napams.get(

                    "error"

                )

            ),

        }



    if not napams.get(

        "source_ok"

    ):

        return {

            "code": (

                "source_unavailable"

            ),

            "level": (

                "unknown"

            ),

            "headline": (

                "NAPAMS could not be reached"

            ),

            "summary": (

                "Before Use could not complete the broader "

                "NAFDAC registration check."

            ),

            "claim_limit": (

                "A source outage is not evidence that the "

                "product is unregistered or unsafe."

            ),

            "next_action": (

                "Retry the check or verify the same NAFDAC "

                "number directly on NAPAMS."

            ),

            "field_checks": [],

            "official_record": None,

            "candidate_count": 0,

            "registry_used": (

                "NAFDAC NAPAMS"

            ),

            "napams_result_text": (

                napams.get(

                    "result_text"

                )

            ),

            "napams_error": (

                napams.get(

                    "error"

                )

            ),

        }



    return {

        "code": (

            "broader_registry_check_inconclusive"

        ),

        "level": (

            "limited"

        ),

        "headline": (

            "Broader NAFDAC verification incomplete"

        ),

        "summary": (

            "Before Use attempted the NAPAMS verification, "

            "but the automated browser result could not "

            "be classified safely."

        ),

        "claim_limit": (

            "An inconclusive automated lookup is not "

            "evidence that the product is unregistered, "

            "fake, or unsafe."

        ),

        "next_action": (

            "Open the official NAPAMS verification page "

            "and check the same NAFDAC number manually."

        ),

        "field_checks": [],

        "official_record": None,

        "candidate_count": 0,

        "registry_used": (

            "NAFDAC NAPAMS"

        ),

        "napams_result_text": (

            napams.get(

                "result_text"

            )

        ),

        "napams_error": (

            napams.get(

                "error"

            )

        ),

    }





# =========================================================

# MAIN ORCHESTRATOR

# =========================================================



def check_all_evidence(

    product_state: Dict[

        str,

        Any,

    ],

):



    overall_started = (

        time.perf_counter()

    )



    product_state = (

        product_state

        or {}

    )



    product_name = (

        product_state.get(

            "product_name"

        )

    )



    registration_number = (

        product_state.get(

            "nafdac_number"

        )

    )



    manufacturer = (

        product_state.get(

            "manufacturer"

        )

    )



    batch_number = (

        product_state.get(

            "batch_number"

        )

    )



    route_info = (

        classify_evidence_route(

            product_state

        )

    )



    route = (

        route_info[

            "route"

        ]

    )



    route_reason = (

        route_info[

            "reason"

        ]

    )



    print(

        "\n"

        "============================================\n"

        "BEFORE USE EVIDENCE CHECK START\n"

        f"Route: {route}\n"

        f"Product: {product_name}\n"

        f"NAFDAC: {registration_number}\n"

        "============================================",

        flush=True,

    )



    executor = (

        ThreadPoolExecutor(

            max_workers=3,

            thread_name_prefix=(

                "before_use_evidence"

            ),

        )

    )



    nafdac_alert_future = None

    who_alert_future = None



    try:



        nafdac_alert_future = (

            executor.submit(

                _timed_call,

                "NAFDAC ALERTS",

                check_nafdac_safety_alerts,

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



        if (

            route

            ==

            "napams_first"

        ):

            who_alerts = (

                _skipped_source(

                    "WHO Medical Product Alerts",

                    (

                        "Skipped because this product was "

                        "routed as a clearly non-medicine product."

                    ),

                )

            )



        else:

            who_alert_future = (

                executor.submit(

                    _timed_call,

                    "WHO ALERTS",

                    check_who_safety_alerts,

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



        if not registration_number:



            greenbook = (

                _empty_source(

                    "NAFDAC Greenbook"

                )

            )



            historical = (

                _empty_source(

                    "Historical NAFDAC evidence"

                )

            )



            registration_result = (

                build_registration_result(

                    product_state,

                    greenbook,

                )

            )



        elif (

            route

            ==

            "napams_first"

        ):



            napams = (

                _timed_call(

                    "NAPAMS",

                    check_napams_registration,

                    registration_number,

                )

            )



            greenbook = (

                _skipped_source(

                    "NAFDAC Greenbook",

                    (

                        "Skipped because this product was "

                        "conservatively routed to NAFDAC "

                        "NAPAMS first as a clearly "

                        "non-medicine product."

                    ),

                )

            )



            greenbook[

                "napams"

            ] = (

                napams

            )



            registration_result = (

                _build_napams_only_registration_result(

                    product_state,

                    napams,

                )

            )



            historical = (

                _skipped_source(

                    "Historical NAFDAC evidence",

                    (

                        "Skipped because NAPAMS is the "

                        "relevant current registration "

                        "route for this clearly "

                        "non-medicine product."

                    ),

                )

            )



        else:



            greenbook = (

                _timed_call(

                    "GREENBOOK",

                    check_greenbook_registration,

                    registration_number,

                )

            )



            greenbook_records = (

                greenbook.get(

                    "records"

                )

                or []

            )



            if greenbook_records:



                registration_result = (

                    build_registration_result(

                        product_state,

                        greenbook,

                    )

                )



                historical = (

                    _skipped_source(

                        "Historical NAFDAC evidence",

                        (

                            "Skipped because a current "

                            "exact Greenbook record was found; "

                            "historical evidence is unnecessary "

                            "for this result."

                        ),

                    )

                )



            else:



                napams = (

                    _timed_call(

                        "NAPAMS",

                        check_napams_registration,

                        registration_number,

                    )

                )



                greenbook = dict(

                    greenbook

                )



                greenbook[

                    "napams"

                ] = (

                    napams

                )



                registration_result = (

                    build_registration_result(

                        product_state,

                        greenbook,

                    )

                )



                if (

                    napams.get(

                        "source_ok"

                    )

                    and

                    napams.get(

                        "found"

                    )

                    and

                    napams.get(

                        "status"

                    )

                    ==

                    "match_found"

                ):



                    historical = (

                        _skipped_source(

                            "Historical NAFDAC evidence",

                            (

                                "Skipped because NAPAMS "

                                "returned current registration "

                                "evidence after the Greenbook miss."

                            ),

                        )

                    )



                else:



                    historical = (

                        _timed_call(

                            "HISTORICAL",

                            find_historical_evidence,

                            registration_number=(

                                registration_number

                            ),

                            product_name=(

                                product_name

                            ),

                            manufacturer=(

                                manufacturer

                            ),

                        )

                    )



        nafdac_alerts = (

            _collect_future_with_budget(

                nafdac_alert_future,

                label=(

                    "NAFDAC ALERTS"

                ),

                source_name=(

                    "NAFDAC recalls and safety alerts"

                ),

                extra_wait_seconds=(

                    NAFDAC_ALERT_EXTRA_WAIT_SECONDS

                ),

            )

        )



        if (

            who_alert_future

            is not None

        ):

            who_alerts = (

                _collect_future_with_budget(

                    who_alert_future,

                    label=(

                        "WHO ALERTS"

                    ),

                    source_name=(

                        "WHO Medical Product Alerts"

                    ),

                    extra_wait_seconds=(

                        WHO_ALERT_EXTRA_WAIT_SECONDS

                    ),

                )

            )



    finally:



        executor.shutdown(

            wait=False,

            cancel_futures=True,

        )



    # =====================================================

    # ALERT CLASSIFICATION

    # =====================================================



    nafdac_high = (

        _alerts_by_significance(

            nafdac_alerts,

            "high",

        )

    )



    who_high = (

        _alerts_by_significance(

            who_alerts,

            "high",

        )

    )



    who_relevant = (

        _alerts_by_significance(

            who_alerts,

            "relevant",

        )

    )



    exact_safety_alerts = (

        nafdac_high

        +

        who_high

    )



    safety_source_incomplete = (

        _safety_source_incomplete(

            nafdac_alerts,

            who_alerts,

        )

    )



    registration_source_incomplete = (

        _registration_source_incomplete(

            greenbook

        )

    )



    # =====================================================

    # FINAL EVIDENCE PRIORITY

    # =====================================================



    if exact_safety_alerts:



        code = (

            "safety_alert_match"

        )



        headline = (

            "Safety alert requires attention"

        )



        summary = (

            "Before Use found safety-alert evidence "

            "matching an identifier or batch you confirmed."

        )



        next_action = (

            "Review the cited regulatory alert before "

            "using the product. Safety-alert evidence "

            "takes priority over an otherwise positive "

            "registration result."

        )



    elif who_relevant:



        code = (

            "international_alert_relevant"

        )



        headline = (

            "Relevant WHO safety alert found"

        )



        summary = (

            "WHO has published a Medical Product Alert "

            "involving this product name. Before Use has "

            "not confirmed that your exact pack or batch "

            "is affected."

        )



        next_action = (

            "Open the WHO alert and compare the affected "

            "product, batch, presentation and location "

            "with the pack in your hand."

        )



    elif (

        registration_result.get(

            "code"

        )

        ==

        "records_match"

    ):



        code = (

            "current_record_match"

        )



        headline = (

            "Current registration record matches"

        )



        summary = (

            "The confirmed registration number matches "

            "a current NAFDAC Greenbook record, and the "

            "comparable product details are consistent."

        )



        next_action = (

            "Continue checking the physical pack. Registration "

            "does not prove that this individual pack is genuine."

        )



        if safety_source_incomplete:

            (

                summary,

                next_action,

            ) = _with_safety_limitation(

                summary,

                next_action,

                nafdac_alerts=nafdac_alerts,

                who_alerts=who_alerts,

            )

        else:

            next_action = (

                "No matching high-priority safety alert was found "

                "in the connected sources. Continue checking the "

                "physical pack. Registration does not prove that "

                "this individual pack is genuine."

            )



    elif (

        registration_result.get(

            "code"

        )

        ==

        "napams_record_match"

    ):



        code = (

            "napams_record_match"

        )



        headline = (

            "Current NAFDAC registration record found"

        )



        summary = (

            "NAPAMS returned the confirmed NAFDAC "

            "registration number and the comparable "

            "details did not conflict with the "

            "returned record."

        )



        next_action = (

            "Continue checking the physical product. A "

            "registration result does not prove that the "

            "individual item is genuine."

        )



        if safety_source_incomplete:

            (

                summary,

                next_action,

            ) = _with_safety_limitation(

                summary,

                next_action,

                nafdac_alerts=nafdac_alerts,

                who_alerts=who_alerts,

            )

        else:

            next_action = (

                "No matching high-priority NAFDAC safety alert "

                "was found in the connected sources. Continue "

                "checking the physical product. A registration "

                "result does not prove that the individual item "

                "is genuine."

            )



    elif (

        registration_result.get(

            "code"

        )

        in

        {"details_mismatch", "details_need_verification"}

    ):



        code = (

            registration_result.get(

                "code"

            )

        )



        headline = (

            registration_result.get(

                "headline"

            )

        )



        summary = (

            registration_result.get(

                "summary"

            )

        )



        next_action = (

            registration_result.get(

                "next_action"

            )

        )



        if safety_source_incomplete:

            (

                summary,

                next_action,

            ) = _with_safety_limitation(

                summary,

                next_action,

                nafdac_alerts=nafdac_alerts,

                who_alerts=who_alerts,

            )



    elif (

        historical.get(

            "records"

        )

        and

        not historical.get(

            "skipped"

        )

    ):



        code = (

            "historical_record_found"

        )



        headline = (

            "Historical NAFDAC evidence found"

        )



        summary = (

            "No current registration match was confirmed, "

            "but an official historical NAFDAC source "

            "associates this registration number with "

            "the product."

        )



        next_action = (

            "Treat this as historical evidence only. "

            "It does not confirm that the registration "

            "is currently active. Verify current status "

            "with NAFDAC before use."

        )



        if safety_source_incomplete:

            (

                summary,

                next_action,

            ) = _with_safety_limitation(

                summary,

                next_action,

                nafdac_alerts=nafdac_alerts,

                who_alerts=who_alerts,

            )



    elif registration_source_incomplete:



        code = (

            "source_incomplete"

        )



        headline = (

            "Some evidence sources could not be checked"

        )



        summary = (

            "Before Use could not complete the relevant "

            "registration-source check, so the evidence "

            "trail is incomplete."

        )



        next_action = (

            "Retry the check or verify directly with the "

            "relevant regulator before relying on the result."

        )



    elif safety_source_incomplete:



        code = (

            "source_incomplete"

        )



        headline = (

            "Some evidence sources could not be checked"

        )



        summary = (

            "Before Use completed the available regulatory "

            "checks, but one or more relevant safety sources "

            "did not complete during this check."

        )



        next_action = (

            "You can retry later or verify directly with the "

            "relevant regulator before relying on the incomplete "

            "evidence trail."

        )



    else:



        code = (

            registration_result.get(

                "code",

                "record_not_found",

            )

        )



        headline = (

            registration_result.get(

                "headline",

                "Registration record not found",

            )

        )



        summary = (

            registration_result.get(

                "summary",

                (

                    "No matching regulatory evidence "

                    "was found in the relevant sources checked."

                ),

            )

        )



        next_action = (

            registration_result.get(

                "next_action",

                (

                    "Recheck the product details and "

                    "verify directly with NAFDAC."

                ),

            )

        )



    # =====================================================

    # COMPLETE EVIDENCE PASSPORT

    # =====================================================



    result = {



        "code": (

            code

        ),



        "headline": (

            headline

        ),



        "summary": (

            summary

        ),



        "next_action": (

            next_action

        ),



        "product_state": (

            product_state

        ),



        "evidence_route": (

            route

        ),



        "evidence_route_reason": (

            route_reason

        ),



        "sources": {



            "greenbook": (

                greenbook

            ),



            "historical_nafdac": (

                historical

            ),



            "nafdac_alerts": (

                nafdac_alerts

            ),



            "who_alerts": (

                who_alerts

            ),

        },



        "registration_result": (

            registration_result

        ),



        "exact_safety_alerts": (

            exact_safety_alerts

        ),



        "relevant_who_alerts": (

            who_relevant

        ),



        "safety_source_incomplete": (

            safety_source_incomplete

        ),



        "registration_source_incomplete": (

            registration_source_incomplete

        ),

    }



    # =====================================================

    # PROMOTE REGISTRATION DETAILS

    # =====================================================



    for key in [

        "level",

        "claim_limit",

        "field_checks",

        "official_record",

        "candidate_count",

        "registry_used",

        "napams_result_text",

        "napams_error",

        "source_error",

        "duplicate_note",

    ]:



        if (

            key

            in

            registration_result

        ):

            result[

                key

            ] = (

                registration_result.get(

                    key

                )

            )



    # =====================================================

    # FINAL TIMING

    # =====================================================



    total_elapsed = (

        time.perf_counter()

        -

        overall_started

    )



    _print_timing(

        "TOTAL EVIDENCE",

        total_elapsed,

    )



    print(

        "============================================\n"

        "BEFORE USE EVIDENCE CHECK COMPLETE\n"

        "============================================\n",

        flush=True,

    )



    return result