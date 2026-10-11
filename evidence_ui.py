import html

import streamlit as st


def _esc(value):
    if value is None:
        return ""
    return html.escape(str(value))


def render_evidence_result(result):
    """
    Render Phase 1 registration evidence clearly and cautiously.

    This UI deliberately distinguishes:
    - record match
    - mismatch
    - inactive record
    - record not found
    - source unavailable

    It never labels an individual pack "authentic".
    """
    if not result:
        st.error("No evidence result is available.")
        return

    code = result.get("code")
    headline = result.get("headline", "Evidence result")
    summary = result.get("summary", "")
    claim_limit = result.get("claim_limit", "")
    next_action = result.get("next_action", "")

    if code == "records_match":
        st.success(headline)

    elif code in {
        "details_mismatch",
        "registration_inactive",
        "record_not_found",
    }:
        st.warning(headline)

    else:
        st.info(headline)

    if summary:
        st.write(summary)

    official_record = result.get("official_record")

    if official_record:
        st.markdown("### Official record")

        col1, col2 = st.columns(2)

        with col1:
            st.caption("Product")
            st.write(
                official_record.get("product_name")
                or "Not available"
            )

            st.caption("NAFDAC registration number")
            st.write(
                official_record.get("registration_number")
                or "Not available"
            )

            st.caption("Applicant")
            st.write(
                official_record.get("applicant")
                or "Not available"
            )

        with col2:
            st.caption("Status")
            st.write(
                official_record.get("status")
                or "Not available"
            )

            st.caption("Approval date")
            st.write(
                official_record.get("approval_date")
                or "Not available"
            )

            st.caption("Registration expiry")
            st.write(
                official_record.get(
                    "registration_expiry_date"
                )
                or "Not available"
            )

        extra_fields = [
            (
                "Ingredients",
                official_record.get("active_ingredients"),
            ),
            (
                "Strength",
                official_record.get("strength"),
            ),
            (
                "Form",
                official_record.get("form"),
            ),
            (
                "Route",
                official_record.get("route"),
            ),
            (
                "Category",
                official_record.get("category"),
            ),
        ]

        available_extra = [
            (label, value)
            for label, value in extra_fields
            if value
        ]

        if available_extra:
            with st.expander("More official record details"):
                for label, value in available_extra:
                    st.markdown(
                        f"**{_esc(label)}:** {_esc(value)}"
                    )

        source_url = official_record.get("source_url")

        if source_url:
            st.link_button(
                "Open official NAFDAC record",
                source_url,
                use_container_width=True,
            )

    field_checks = result.get("field_checks") or []

    if field_checks:
        st.markdown("### What matched")

        for check in field_checks:
            state = check.get("state")
            field = check.get("field", "Field")
            user_value = check.get("user_value")
            official_value = check.get("official_value")

            if state == "match":
                symbol = "✓"
                label = "Match"
            elif state == "mismatch":
                symbol = "!"
                label = "Mismatch"
            elif state == "not_provided":
                symbol = "–"
                label = "Not provided"
            else:
                symbol = "–"
                label = "Not available to compare"

            with st.container(border=True):
                st.markdown(
                    f"**{symbol} {field} — {label}**"
                )

                if user_value is not None:
                    st.caption("You confirmed")
                    st.write(user_value)

                if official_value is not None:
                    st.caption("Official record")
                    st.write(official_value)

    duplicate_note = result.get("duplicate_note")

    if duplicate_note:
        st.info(duplicate_note)

    if claim_limit:
        st.markdown("### What this does not prove")
        st.write(claim_limit)

    if next_action:
        st.markdown("### Next step")
        st.write(next_action)

    if code == "records_match":
        st.caption(
            "Phase 1 complete: registration-record check. "
            "Batch and safety-alert checking is not connected yet."
        )

    elif code == "source_unavailable":
        source_error = result.get("source_error")

        if source_error:
            with st.expander("Technical source detail"):
                st.code(source_error)
