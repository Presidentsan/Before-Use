# Before Use — Evidence Engine Phase 1

This phase connects Before Use to the **official NAFDAC Greenbook**.

It does **not** yet check safety alerts or recall batches. That will be
Phase 2.

## Files

Put these beside `app.py`:

```text
Before Use/
├── app.py
├── natlas_asr.py
├── transcript_interpreter.py
├── product_extractor.py
├── conversation.py
├── evidence_checker.py
├── result_engine.py
└── test_evidence.py
```

## Install dependency

```bash
pip install requests
```

## Compile

```bash
python -m py_compile evidence_checker.py
python -m py_compile result_engine.py
python -m py_compile test_evidence.py
```

No output means the Python syntax is valid.

## Test the evidence engine WITHOUT changing app.py yet

Run:

```bash
python test_evidence.py
```

The test performs two checks:

### Test 1

```text
Panadol Extra
04-0005
GlaxoSmithKline Consumer Nigeria PLC
```

The current official NAFDAC Greenbook lists Panadol Extra Caplet under
`04-0005` and Active.

We expect an official record to be found.

### Test 2

```text
Panadol Extra
A4-1409
Emzor
```

This deliberately uses the number that appeared in our earlier ASR
development test.

Before Use should **not** silently assume that number belongs to
Panadol Extra.

## Why we test outside Streamlit first

We want to establish:

```text
NAFDAC website
    ↓
evidence_checker.py
    ↓
official record
    ↓
result_engine.py
    ↓
careful conclusion
```

before changing the UI.

If the direct Greenbook JSON request has changed its schema, the test
will give us the exact error and we can repair only the adapter.

## Result meanings

### records_match

Means:

> The confirmed details match an active registration record.

It does NOT mean:

> This individual pack is genuine.

### details_mismatch

Means:

> The registration exists, but one or more comparable pack details do
> not agree with the official record.

### registration_inactive

Means:

> The registration exists but is not currently listed Active.

### record_not_found

Means:

> No exact match was found for the confirmed registration number.

This does not automatically mean counterfeit.

### source_unavailable

Means:

> NAFDAC could not be reached or returned an unusable response.

This is kept separate from "not found".

## After this test passes

We connect the two modules into the existing `checking` and `result`
states in `app.py`.

Then Phase 2 adds:

```text
NAFDAC safety alerts
        +
product name
        +
registration number
        +
batch number
        +
expiry date
```

A matching safety alert will override an ordinary positive
registration-record result.
