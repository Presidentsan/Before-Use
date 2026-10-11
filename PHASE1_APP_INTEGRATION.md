# Before Use — Connect Phase 1 Evidence to app.py

This assumes these files already exist beside `app.py`:

```text
evidence_checker.py
result_engine.py
evidence_ui.py
```

Your existing voice-reply files can stay exactly where they are.

---

## 1. Add these imports

Near your existing project imports at the top of `app.py`, add:

```python
from evidence_checker import check_greenbook_registration
from result_engine import build_registration_result
from evidence_ui import render_evidence_result
```

Do not remove any of your existing voice imports.

---

## 2. Add two session-state values

Inside `default_state()`, add:

```python
"greenbook_evidence": None,
"registration_result": None,
```

So that section includes:

```python
def default_state():
    return {
        "current_step": "start",
        "transcript": None,
        "extracted_details": None,
        "product_state": None,
        "followup_transcript": None,
        "followup_field": None,
        "skipped_fields": set(),
        "interpreter_used": None,
        "interpreter_error": None,
        "greenbook_evidence": None,
        "registration_result": None,
    }
```

---

## 3. Update reset_check()

Add these two names to `keys_to_clear`:

```python
"greenbook_evidence",
"registration_result",
```

Then, near the bottom of `reset_check()`, add:

```python
st.session_state.greenbook_evidence = None
st.session_state.registration_result = None
```

This prevents the previous product's evidence from appearing during a new check.

---

## 4. Replace your entire current CHECKING branch

Replace everything from:

```python
elif st.session_state.current_step == "checking":
```

down to just before the RESULT section with this:

```python
elif st.session_state.current_step == "checking":

    render_brand()
    render_progress("checking")

    _, center, _ = st.columns(
        [0.18, 0.64, 0.18]
    )

    with center:

        render_html(
            """
            <div class="screen-heading">
                Checking the evidence.
            </div>

            <div class="screen-copy">
                Before Use is comparing the NAFDAC number
                you confirmed with the official NAFDAC
                Greenbook.
            </div>
            """
        )

        render_product_summary(
            st.session_state.product_state
        )

        render_html(
            """
            <div class="source-chips">
                <div class="source-chip">
                    NAFDAC Greenbook · connected
                </div>
                <div class="source-chip">
                    Safety alerts · next phase
                </div>
            </div>
            """
        )

        product_state = (
            st.session_state.product_state
            or {}
        )

        nafdac_number = product_state.get(
            "nafdac_number"
        )

        if not nafdac_number:

            st.session_state.greenbook_evidence = {
                "source_ok": True,
                "source_name": "NAFDAC Greenbook",
                "query": None,
                "records": [],
                "error": None,
            }

            st.session_state.registration_result = (
                build_registration_result(
                    product_state,
                    st.session_state.greenbook_evidence,
                )
            )

            st.session_state.current_step = "result"
            st.rerun()

        if (
            st.session_state.registration_result
            is None
        ):

            with st.spinner(
                "Checking the official NAFDAC register..."
            ):

                evidence = (
                    check_greenbook_registration(
                        nafdac_number
                    )
                )

                result = (
                    build_registration_result(
                        product_state,
                        evidence,
                    )
                )

                st.session_state.greenbook_evidence = (
                    evidence
                )

                st.session_state.registration_result = (
                    result
                )

        st.success(
            "Registration-record check complete."
        )

        if st.button(
            "See evidence result",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.current_step = "result"
            st.rerun()
```

---

## 5. Replace the RESULT PLACEHOLDER branch

Replace your entire current:

```python
elif st.session_state.current_step == "result":
```

branch with:

```python
elif st.session_state.current_step == "result":

    render_brand()
    render_progress("result")

    _, center, _ = st.columns(
        [0.15, 0.70, 0.15]
    )

    with center:

        render_html(
            """
            <div class="eyebrow">
                Evidence Trail
            </div>

            <div class="screen-heading">
                Here’s what the official record shows.
            </div>

            <div class="screen-copy">
                Before Use checked your confirmed product
                details against the NAFDAC Greenbook.
            </div>
            """
        )

        render_product_summary(
            st.session_state.product_state
        )

        render_evidence_result(
            st.session_state.registration_result
        )

        st.divider()

        st.info(
            "Batch and safety-alert checking is not connected "
            "yet. A registration-record match alone does not "
            "prove that the individual pack is genuine or safe."
        )

        if st.button(
            "Check another product",
            type="primary",
            use_container_width=True,
        ):
            reset_check()
            st.rerun()
```

---

## 6. Fix the missing space in result_engine.py

Find:

```python
"individual pack"
"is genuine, untampered, properly stored, "
```

Change it to:

```python
"individual pack "
"is genuine, untampered, properly stored, "
```

---

## 7. Compile

Run:

```bash
python -m py_compile evidence_checker.py
python -m py_compile result_engine.py
python -m py_compile evidence_ui.py
python -m py_compile app.py
```

No output means all four files compile.

Then:

```bash
streamlit run app.py
```

---

## 8. Test two products

### Known official record

Use:

```text
Product: Panadol Extra
NAFDAC: 04-0005
Manufacturer: GlaxoSmithKline Consumer Nigeria PLC
Batch: 116Y
Expiry: December 2027
```

Expected result:

```text
Registration record matches
```

The result should also show the official record and the field-by-field evidence trail.

### Deliberate non-match

Use:

```text
Product: Panadol Extra
NAFDAC: A4-1409
Manufacturer: Emzor
Batch: 258341B
Expiry: December 2027
```

Expected result:

```text
Registration record not found
```

It must NOT say counterfeit.

---

## What Phase 1 now proves

```text
Voice input
    ↓
N-ATLAS
    ↓
Gemini interpretation
    ↓
User confirmation
    ↓
Official NAFDAC Greenbook lookup
    ↓
Exact NRN match
    ↓
Product/applicant comparison
    ↓
Transparent evidence result
```

The next phase is **NAFDAC recalls / safety alerts**, where batch and expiry become materially useful.
