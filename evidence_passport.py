import hashlib
from typing import Any, Dict

import streamlit as st

from mas_guidance import (
    MAS_GUIDELINE_URL,
    classify_user_reported_mas_response,
)

from report_concern import (
    NAFDAC_SF_REPORT_URL,
    build_concern_summary,
)


def _safe(
    value,
    fallback="Not provided",
):
    if value is None:
        return fallback

    value = str(value).strip()

    if not value:
        return fallback

    return value


def _first_value(
    mapping,
    *keys,
    fallback=None,
):
    if not mapping:
        return fallback

    for key in keys:
        value = mapping.get(
            key
        )

        if value is not None:
            value = str(
                value
            ).strip()

            if value:
                return value

    return fallback


def _source_record_count(
    source,
):
    if not source:
        return 0

    return len(
        source.get(
            "records",
            [],
        )
    )


def _product_key(
    product: Dict[
        str,
        Any,
    ],
) -> str:
    raw = "|".join(
        str(
            product.get(
                key
            )
            or ""
        )
        .strip()
        .lower()
        for key in [
            "product_name",
            "nafdac_number",
            "manufacturer",
            "batch_number",
            "expiry_date",
        ]
    )

    return (
        hashlib
        .sha256(
            raw.encode(
                "utf-8"
            )
        )
        .hexdigest()[
            :12
        ]
    )


def _render_current_greenbook(
    greenbook,
    product=None,
):
    st.markdown(
        "### Current NAFDAC Greenbook"
    )

    records = (
        greenbook.get(
            "records",
            [],
        )
        if greenbook
        else []
    )

    if not records:
        registration_number = (
            (product or {}).get(
                "nafdac_number"
            )
        )

        if not registration_number:
            st.info(
                "Greenbook registration lookup was not run "
                "because no NAFDAC registration number "
                "was provided."
            )
        else:
            st.info(
                "No current exact Greenbook record "
                "was found for the confirmed "
                "registration number."
            )

        return

    official = records[0]

    st.success(
        "Current Greenbook record found."
    )

    official_product = _first_value(
        official,
        "product_name",
        "name",
    )

    official_nafdac = _first_value(
        official,
        "registration_number",
        "NAFDAC",
        "nafdac_number",
        "nafdac",
    )

    official_applicant = _first_value(
        official,
        "applicant",
        "applicant_name",
        "manufacturer",
        "manufacturer_name",
    )

    official_status = _first_value(
        official,
        "status",
    )

    official_approval_date = _first_value(
        official,
        "approval_date",
    )

    official_expiry = _first_value(
        official,
        "registration_expiry_date",
        "expiry_date",
    )

    ingredients = _first_value(
        official,
        "active_ingredients",
        "ingredient_name",
        "composition",
    )

    strength = _first_value(
        official,
        "strength",
    )

    dosage_form = _first_value(
        official,
        "form",
        "form_name",
    )

    route = _first_value(
        official,
        "route",
        "route_name",
    )

    category = _first_value(
        official,
        "category",
        "category_name",
    )

    col1, col2 = st.columns(
        2
    )

    with col1:
        st.caption(
            "Official product"
        )

        st.write(
            _safe(
                official_product
            )
        )

        st.caption(
            "Official NAFDAC number"
        )

        st.write(
            _safe(
                official_nafdac
            )
        )

    with col2:
        st.caption(
            "Official applicant"
        )

        st.write(
            _safe(
                official_applicant
            )
        )

        st.caption(
            "Registration status"
        )

        st.write(
            _safe(
                official_status
            )
        )

    detail_values = [
        (
            "Approval date",
            official_approval_date,
        ),
        (
            "Registration expiry",
            official_expiry,
        ),
        (
            "Ingredients",
            ingredients,
        ),
        (
            "Strength",
            strength,
        ),
        (
            "Form",
            dosage_form,
        ),
        (
            "Route",
            route,
        ),
        (
            "Category",
            category,
        ),
    ]

    if any(
        value
        for _, value
        in detail_values
    ):
        with st.expander(
            "More Greenbook details"
        ):
            for (
                label,
                value,
            ) in detail_values:
                if value:
                    st.markdown(
                        f"**{label}:** "
                        f"{_safe(value)}"
                    )


def _render_napams_record(
    result,
):
    """
    Show the structured NAPAMS record used by the result engine.

    The section is kept separate from Greenbook so the user can see
    exactly what NAPAMS returned and compare it with the details they
    confirmed. Missing NAPAMS fields are never inferred.
    """

    result = (
        result
        or {}
    )

    registry_used = (
        str(
            result.get(
                "registry_used",
                ""
            )
            or ""
        )
        .strip()
    )

    code = (
        result.get(
            "code"
        )
    )

    napams_was_used = (
        "NAPAMS"
        in registry_used.upper()
        or
        code
        in {
            "napams_record_match",
            "registration_not_found_in_connected_sources",
            "broader_registry_check_inconclusive",
        }
    )

    if (
        code
        ==
        "details_mismatch"
        and
        "NAPAMS"
        in registry_used.upper()
    ):
        napams_was_used = True

    if not napams_was_used:
        return

    st.markdown(
        "### NAFDAC NAPAMS"
    )

    official = (
        result.get(
            "official_record"
        )
        or {}
    )

    if not official:
        if (
            code
            ==
            "registration_not_found_in_connected_sources"
        ):
            st.warning(
                "NAPAMS did not return a matching product "
                "for the confirmed NAFDAC registration number "
                "during this check."
            )

        elif (
            code
            ==
            "broader_registry_check_inconclusive"
        ):
            st.warning(
                "Before Use attempted the NAPAMS verification, "
                "but the automated browser result could not be "
                "classified safely."
            )

            if result.get(
                "napams_error"
            ):
                st.caption(
                    _safe(
                        result.get(
                            "napams_error"
                        )
                    )
                )

        else:
            st.info(
                "No structured NAPAMS record is available "
                "for this result."
            )

        return

    st.success(
        "NAPAMS returned a record for the confirmed "
        "NAFDAC registration number."
    )

    official_product = _first_value(
        official,
        "product_name",
        "name",
    )

    official_nafdac = _first_value(
        official,
        "registration_number",
        "NAFDAC",
        "nafdac_number",
        "nafdac",
    )

    official_applicant = _first_value(
        official,
        "applicant",
        "applicant_name",
        "manufacturer",
        "manufacturer_name",
    )

    official_status = _first_value(
        official,
        "status",
    )

    official_expiry = _first_value(
        official,
        "registration_expiry_date",
        "expiry_date",
    )

    category = _first_value(
        official,
        "category",
        "category_name",
    )

    left, right = st.columns(
        2
    )

    with left:
        st.caption(
            "NAPAMS product"
        )

        st.write(
            _safe(
                official_product,
                fallback="Not returned by NAPAMS",
            )
        )

        st.caption(
            "NAPAMS NAFDAC number"
        )

        st.write(
            _safe(
                official_nafdac,
                fallback="Not returned by NAPAMS",
            )
        )

    with right:
        st.caption(
            "NAPAMS manufacturer / applicant"
        )

        st.write(
            _safe(
                official_applicant,
                fallback="Not returned by NAPAMS",
            )
        )

        if official_status:
            st.caption(
                "NAPAMS status"
            )

            st.write(
                _safe(
                    official_status
                )
            )

    extra_values = [
        (
            "Registration expiry",
            official_expiry,
        ),
        (
            "Category",
            category,
        ),
    ]

    available_extra = [
        (
            label,
            value,
        )
        for (
            label,
            value,
        )
        in extra_values
        if value
    ]

    if available_extra:
        with st.expander(
            "More NAPAMS record details"
        ):
            for (
                label,
                value,
            ) in available_extra:
                st.markdown(
                    f"**{label}:** "
                    f"{_safe(value)}"
                )

    source_url = _first_value(
        official,
        "source_url",
    )

    if source_url:
        st.link_button(
            "Open official NAPAMS verification page",
            source_url,
            use_container_width=True,
        )

    field_checks = (
        result.get(
            "field_checks"
        )
        or []
    )

    if field_checks:
        st.markdown(
            "#### Comparison with your product"
        )

        st.caption(
            "These comparisons use the details you confirmed "
            "and the structured values returned by NAPAMS."
        )

        for check in field_checks:
            field = (
                check.get(
                    "field",
                    "Field",
                )
            )

            state = (
                check.get(
                    "state"
                )
            )

            user_value = (
                check.get(
                    "user_value"
                )
            )

            official_value = (
                check.get(
                    "official_value"
                )
            )

            if (
                state
                ==
                "match"
            ):
                symbol = "✓"
                state_label = "Match"

            elif state == "needs_verification":
                symbol = "◷"
                state_label = "Needs verification"

            elif (
                state
                ==
                "mismatch"
            ):
                symbol = "⚠"
                state_label = "Mismatch"

            elif (
                state
                ==
                "not_provided"
            ):
                symbol = "–"
                state_label = "Not provided"

            else:
                symbol = "–"
                state_label = "Not available to compare"

            with st.container(
                border=True
            ):
                st.markdown(
                    f"**{symbol} {field} — {state_label}**"
                )

                if check.get("note"):
                    st.caption(check["note"])

                compare_left, compare_right = (
                    st.columns(
                        2
                    )
                )

                with compare_left:
                    st.caption(
                        "You confirmed"
                    )

                    st.write(
                        _safe(
                            user_value
                        )
                    )

                with compare_right:
                    st.caption(
                        "NAPAMS record"
                    )

                    st.write(
                        _safe(
                            official_value,
                            fallback="Not returned by NAPAMS",
                        )
                    )

    st.caption(
        "NAPAMS is being used here as regulatory evidence. "
        "A NAPAMS registration result does not prove that "
        "the individual physical product is genuine, "
        "untampered, properly stored, or safe to use."
    )


def _render_historical(
    historical,
):
    st.markdown(
        "### Historical NAFDAC evidence"
    )

    records = (
        historical.get(
            "records",
            [],
        )
        if historical
        else []
    )

    if not records:
        st.info(
            "No additional historical record "
            "was found in the currently connected "
            "historical NAFDAC evidence index."
        )

        return

    st.warning(
        "Historical regulatory evidence found."
    )

    for record in records:
        st.caption(
            "Historical product"
        )

        st.write(
            _safe(
                record.get(
                    "product_name"
                )
            )
        )

        st.caption(
            "Registration number"
        )

        st.write(
            _safe(
                record.get(
                    "registration_number"
                )
            )
        )

        st.caption(
            "Manufacturer"
        )

        st.write(
            _safe(
                record.get(
                    "manufacturer"
                )
            )
        )

        if record.get(
            "product_class"
        ):
            st.caption(
                "Product class"
            )

            st.write(
                record.get(
                    "product_class"
                )
            )

        if record.get(
            "evidence_year"
        ):
            st.caption(
                "Evidence year"
            )

            st.write(
                record.get(
                    "evidence_year"
                )
            )

        if record.get(
            "source_name"
        ):
            st.caption(
                "Source: "
                f"{record.get('source_name')}"
            )

        if record.get(
            "source_url"
        ):
            st.link_button(
                "Open historical source",
                record.get(
                    "source_url"
                ),
            )

        if record.get(
            "note"
        ):
            st.caption(
                record.get(
                    "note"
                )
            )


def _render_nafdac_alerts(
    source,
):
    st.markdown(
        "### NAFDAC safety alerts"
    )

    records = (
        source.get(
            "records",
            [],
        )
        if source
        else []
    )

    source_ok = (
        source.get(
            "source_ok",
            False,
        )
        if source
        else False
    )

    if not source_ok:
        st.warning(
            "The NAFDAC safety-alert source "
            "could not be fully checked."
        )

        if (
            source
            and source.get(
                "error"
            )
        ):
            st.caption(
                source.get(
                    "error"
                )
            )

        return

    high_records = [
        record
        for record in records
        if record.get(
            "significance"
        ) == "high"
    ]

    medium_records = [
        record
        for record in records
        if record.get(
            "significance"
        ) == "medium"
    ]

    possible_records = [
        record
        for record in records
        if record.get(
            "significance",
            "possible",
        ) == "possible"
    ]

    if high_records:
        for record in high_records:
            title = (
                record.get(
                    "title"
                )
                or
                "NAFDAC safety alert"
            )

            st.error(
                title
            )

            reasons = (
                record.get(
                    "match_reasons"
                )
                or []
            )

            reason_labels = {
                "exact_batch_match": (
                    "Exact batch match"
                ),
                "exact_registration_match": (
                    "Exact registration-number match"
                ),
                "product_name_match": (
                    "Product-name match"
                ),
                "manufacturer_match": (
                    "Manufacturer match"
                ),
            }

            visible_reasons = [
                reason_labels.get(
                    reason,
                    reason.replace(
                        "_",
                        " ",
                    ).title(),
                )
                for reason
                in reasons
            ]

            if visible_reasons:
                st.caption(
                    "Why this alert matched: "
                    + ", ".join(
                        visible_reasons
                    )
                    + "."
                )

            alert_url = (
                record.get(
                    "url"
                )
                or record.get(
                    "source_url"
                )
            )

            if alert_url:
                st.link_button(
                    "Open NAFDAC alert",
                    alert_url,
                )

        return

    if medium_records:
        st.warning(
            "Relevant NAFDAC safety communication found."
        )

        st.caption(
            "The product and manufacturer matched the alert context, "
            "but Before Use did not confirm an exact batch or "
            "registration-number match."
        )

        for record in medium_records:
            title = (
                record.get(
                    "title"
                )
                or
                "NAFDAC safety alert"
            )

            st.write(
                title
            )

            alert_url = (
                record.get(
                    "url"
                )
                or record.get(
                    "source_url"
                )
            )

            if alert_url:
                st.link_button(
                    "Open NAFDAC alert",
                    alert_url,
                )

        return

    st.success(
        "No matching high-confidence NAFDAC safety alert "
        "was found for the confirmed identifiers."
    )

    if possible_records:
        st.caption(
            "A broader related safety communication was found, "
            "but it did not match the confirmed registration number, "
            "batch, or manufacturer. It is not being treated as a "
            "match for this product."
        )

    else:
        st.caption(
            "This means no matching alert was found during this check. "
            "It is not a guarantee that no alert exists."
        )


def _render_who_alerts(
    source,
):
    st.markdown(
        "### WHO Medical Product Alerts"
    )

    records = (
        source.get(
            "records",
            [],
        )
        if source
        else []
    )

    source_ok = (
        source.get(
            "source_ok",
            False,
        )
        if source
        else False
    )

    if not source_ok:
        st.warning(
            "The WHO Medical Product Alert source "
            "could not be fully checked."
        )

        if (
            source
            and
            source.get(
                "error"
            )
        ):
            st.caption(
                source.get(
                    "error"
                )
            )

        return

    if not records:
        st.success(
            "No matching WHO Medical Product Alert "
            "was found in the sources checked."
        )

        st.caption(
            "This means no matching WHO alert was found "
            "during this check. It does not guarantee "
            "that the product has never been mentioned "
            "in another safety communication."
        )

        return

    for record in records:
        significance = (
            record.get(
                "significance"
            )
            or
            "possible"
        )

        title = (
            record.get(
                "title"
            )
            or
            "WHO Medical Product Alert"
        )

        if (
            significance
            ==
            "high"
        ):
            st.error(
                title
            )

        else:
            st.warning(
                title
            )

        if record.get(
            "url"
        ):
            st.link_button(
                "Open WHO alert",
                record.get(
                    "url"
                ),
            )


def _render_overall_finding(
    result,
):
    st.markdown(
        "### Overall finding"
    )

    code = (
        result.get(
            "code"
        )
    )

    headline = (
        result.get(
            "headline",
            "Evidence check complete",
        )
    )

    summary = (
        result.get(
            "summary",
            "",
        )
    )

    next_action = (
        result.get(
            "next_action",
            "",
        )
    )

    if (
        code
        ==
        "safety_alert_match"
    ):
        st.error(
            headline
        )

    elif (
        code
        ==
        "international_alert_relevant"
    ):
        st.warning(
            headline
        )

    elif (
        code
        ==
        "current_record_match"
    ):
        st.success(
            headline
        )

    elif (
        code
        ==
        "historical_record_found"
    ):
        st.warning(
            headline
        )

    elif (
        code
        in {
            "details_mismatch",
            "details_need_verification",
            "registration_inactive",
            "record_not_found",
            "source_incomplete",
            "source_unavailable",
        }
    ):
        st.warning(
            headline
        )

    else:
        st.info(
            headline
        )

    if summary:
        st.write(
            summary
        )

    if next_action:
        st.markdown(
            "**Recommended next step**"
        )

        st.write(
            next_action
        )


def _render_why(
    result,
):
    sources = (
        result.get(
            "sources"
        )
        or {}
    )

    greenbook = (
        sources.get(
            "greenbook"
        )
        or {}
    )

    historical = (
        sources.get(
            "historical_nafdac"
        )
        or {}
    )

    nafdac_alerts = (
        sources.get(
            "nafdac_alerts"
        )
        or {}
    )

    who_alerts = (
        sources.get(
            "who_alerts"
        )
        or {}
    )

    with st.expander(
        "Why am I seeing this result?"
    ):
        st.write(
            "Before Use reached this conclusion "
            "from the evidence trail below:"
        )

        st.markdown(
            "- Current NAFDAC records found: "
            f"**{_source_record_count(greenbook)}**"
        )

        st.markdown(
            "- Historical NAFDAC records found: "
            f"**{_source_record_count(historical)}**"
        )

        meaningful_nafdac_alerts = [
            record
            for record
            in nafdac_alerts.get(
                "records",
                [],
            )
            if record.get(
                "significance"
            )
            in {
                "high",
                "medium",
            }
        ]

        st.markdown(
            "- Matching NAFDAC alert records found: "
            f"**{len(meaningful_nafdac_alerts)}**"
        )

        st.markdown(
            "- Matching WHO alert records found: "
            f"**{_source_record_count(who_alerts)}**"
        )

        code = (
            result.get(
                "code"
            )
        )

        if (
            code
            ==
            "current_record_match"
        ):
            st.caption(
                "A current Greenbook registration match "
                "supports the registration record, "
                "but does not authenticate "
                "the individual pack."
            )

        elif (
            code
            ==
            "historical_record_found"
        ):
            st.caption(
                "Historical evidence is shown separately "
                "because it does not establish current "
                "registration status."
            )

        elif (
            code
            ==
            "safety_alert_match"
        ):
            st.caption(
                "A high-priority safety alert can override "
                "an otherwise positive registration finding "
                "for the affected product or batch."
            )

        elif (
            code
            ==
            "international_alert_relevant"
        ):
            st.caption(
                "The WHO alert is relevant to the product "
                "name, but Before Use has not automatically "
                "assumed that the exact pack or batch "
                "is affected."
            )


def _render_mas_section(
    result,
):
    product = (
        result.get(
            "product_state"
        )
        or {}
    )

    key = (
        _product_key(
            product
        )
    )

    st.divider()

    st.markdown(
        "## Check your pack directly"
    )

    st.write(
        "Some medicines use NAFDAC's Mobile "
        "Authentication Service (MAS). Where a pack "
        "has an authentication scratch panel or PIN, "
        "the code printed on the pack can be used to "
        "request an SMS response from the MAS provider."
    )

    st.caption(
        "Before Use does not send the PIN or receive "
        "the SMS itself. Any MAS result entered here "
        "is recorded as user-reported evidence."
    )

    has_panel = (
        st.radio(
            "Does this pack have an authentication "
            "scratch panel or PIN?",
            [
                "Select an option",
                "Yes",
                "No / I can't find one",
            ],
            key=f"mas_panel_{key}",
        )
    )

    if (
        has_panel
        ==
        "Yes"
    ):
        st.info(
            "1. Scratch the authentication panel carefully.\n\n"
            "2. Find the one-time PIN/code.\n\n"
            "3. Follow the SMS instructions and short code "
            "printed on the pack.\n\n"
            "4. Wait for the response, then enter the response "
            "below exactly as you received it."
        )

        st.link_button(
            "Read NAFDAC MAS guidance",
            MAS_GUIDELINE_URL,
        )

        response_text = (
            st.text_area(
                "Enter the MAS SMS response",
                placeholder=(
                    "Paste or type the SMS response here. "
                    "Do not enter the scratch PIN itself."
                ),
                key=f"mas_response_text_{key}",
            )
        )

        if st.button(
            "Record this MAS response",
            key=f"mas_record_{key}",
            use_container_width=True,
        ):
            mas_result = (
                classify_user_reported_mas_response(
                    response_text
                )
            )

            st.session_state[
                f"mas_result_{key}"
            ] = (
                mas_result
            )

            st.rerun()

        mas_result = (
            st.session_state.get(
                f"mas_result_{key}"
            )
        )

        if mas_result:
            status = (
                mas_result.get(
                    "status"
                )
            )

            if (
                status
                ==
                "user_reported_concern"
            ):
                st.error(
                    mas_result.get(
                        "label"
                    )
                )

                st.write(
                    "Do not rely on this pack until "
                    "the concern is resolved. "
                    "You can prepare a report "
                    "for NAFDAC below."
                )

            elif (
                status
                ==
                "user_reported_positive"
            ):
                st.success(
                    mas_result.get(
                        "label"
                    )
                )

            else:
                st.info(
                    mas_result.get(
                        "label"
                    )
                )

            if (
                mas_result.get(
                    "response_text"
                )
            ):
                st.caption(
                    "Recorded response"
                )

                st.write(
                    mas_result.get(
                        "response_text"
                    )
                )

            st.caption(
                mas_result.get(
                    "claim_limit"
                )
            )

    elif (
        has_panel
        ==
        "No / I can't find one"
    ):
        st.info(
            "Not every medicine pack uses MAS. "
            "Do not invent or reuse a code from "
            "another pack. Continue with the "
            "regulatory evidence already shown above."
        )


def _render_report_section(
    result,
):
    product = (
        result.get(
            "product_state"
        )
        or {}
    )

    key = (
        _product_key(
            product
        )
    )

    mas_result = (
        st.session_state.get(
            f"mas_result_{key}"
        )
        or {}
    )

    st.divider()

    st.markdown(
        "## Report a concern"
    )

    st.write(
        "If the pack, registration details, seller, "
        "authentication response, or product quality "
        "gives you reason for concern, Before Use can "
        "prepare the information for NAFDAC's official "
        "substandard or falsified product reporting form."
    )

    reason = (
        st.text_area(
            "What concerns you about this product?",
            placeholder=(
                "For example: the NAFDAC number does not "
                "match, the packaging looks altered, "
                "the MAS response said suspected fake, "
                "or the product quality seems unusual."
            ),
            key=f"concern_reason_{key}",
        )
    )

    report_summary = (
        build_concern_summary(
            product=product,
            evidence_result=result,
            mas_result=mas_result,
            reason=reason,
        )
    )

    with st.expander(
        "Preview report information"
    ):
        st.code(
            report_summary,
            language=None,
        )

    st.download_button(
        "Download concern summary",
        data=report_summary,
        file_name=(
            f"before-use-concern-{key}.txt"
        ),
        mime="text/plain",
        use_container_width=True,
        key=f"download_concern_{key}",
    )

    st.link_button(
        "Open official NAFDAC reporting form",
        NAFDAC_SF_REPORT_URL,
        use_container_width=True,
    )

    st.caption(
        "The NAFDAC form asks for reporter information, "
        "product information, the suspected issue, "
        "where the product was obtained, and supporting "
        "evidence such as photos or packaging. "
        "Before Use does not submit the report on your behalf."
    )


def render_evidence_passport(
    result,
):
    result = (
        result
        or {}
    )

    product = (
        result.get(
            "product_state"
        )
        or {}
    )

    sources = (
        result.get(
            "sources"
        )
        or {}
    )

    st.caption(
        "A transparent record of what Before Use "
        "checked and what each connected source "
        "actually showed."
    )

    st.markdown(
        '<div class="bu-passport-banner"><strong>Your Evidence Passport</strong>'
        '<span>Regulatory evidence and safety signals, clearly separated.</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### Product checked"
    )

    col1, col2 = (
        st.columns(
            2
        )
    )

    with col1:
        st.caption(
            "Product"
        )

        st.write(
            _safe(
                product.get(
                    "product_name"
                )
            )
        )

        st.caption(
            "NAFDAC number"
        )

        st.write(
            _safe(
                product.get(
                    "nafdac_number"
                )
            )
        )

        st.caption(
            "Expiry"
        )

        st.write(
            _safe(
                product.get(
                    "expiry_date"
                )
            )
        )

    with col2:
        st.caption(
            "Manufacturer"
        )

        st.write(
            _safe(
                product.get(
                    "manufacturer"
                )
            )
        )

        st.caption(
            "Batch / lot"
        )

        st.write(
            _safe(
                product.get(
                    "batch_number"
                )
            )
        )

    # Each source is presented in a separate card; evidence computation is unchanged.
    with st.container(border=True):
        _render_overall_finding(result)

    with st.container(border=True):
        _render_current_greenbook(sources.get("greenbook") or {}, product)

    with st.container(border=True):
        _render_napams_record(result)

    with st.container(border=True):
        _render_historical(sources.get("historical_nafdac") or {})

    with st.container(border=True):
        _render_nafdac_alerts(sources.get("nafdac_alerts") or {})

    with st.container(border=True):
        _render_who_alerts(sources.get("who_alerts") or {})

    _render_why(
        result
    )

    st.caption(
        "Before Use reports regulatory evidence found "
        "in the sources checked. A registration match "
        "does not prove that an individual pack is genuine, "
        "untampered, properly stored or safe to use."
    )

    # MAS scratch-code guidance is specific to eligible medicine packs.
    # An explicit non-medicine classification should not display it.
    official_record = result.get("official_record") or {}
    category = str(
        official_record.get("category")
        or official_record.get("category_name")
        or product.get("category")
        or product.get("product_category")
        or product.get("product_type")
        or ""
    ).strip().lower()
    non_medicine_categories = {
        "cosmetic", "cosmetics", "personal care", "oral care",
        "food", "foods", "beverage", "beverages", "packaged water",
        "household chemical", "household chemicals", "chemical", "chemicals",
    }
    if category not in non_medicine_categories:
        _render_mas_section(result)

    _render_report_section(
        result
    )