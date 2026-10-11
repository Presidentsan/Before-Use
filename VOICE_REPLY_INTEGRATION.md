# Before Use — Voice Reply Integration

These changes add **turn-based spoken replies** without changing the
working N-ATLAS → Gemini → user-confirmation pipeline.

The browser performs the speech locally through its built-in
SpeechSynthesis capability. No TTS API key or paid TTS service is
required for this challenge version.

## 1. Put these two files beside `app.py`

- `voice_reply.py`
- `response_builder.py`

Your folder should look like:

```text
Before Use/
├── app.py
├── natlas_asr.py
├── transcript_interpreter.py
├── product_extractor.py
├── conversation.py
├── voice_reply.py
├── response_builder.py
└── assets/
```

## 2. Add these imports near the top of `app.py`

Immediately after your existing Before Use imports:

```python
from voice_reply import (
    render_voice_reply,
    render_voice_toggle,
)
from response_builder import (
    capture_prompt,
    confirmation_prompt,
    missing_detail_prompt,
    ready_to_check_prompt,
    checking_prompt,
    development_result_prompt,
)
```

Do **not** add `voice_replies_enabled` to `reset_check()`.
The user's voice preference should survive a new product check.

---

## 3. CAPTURE screen

In the `capture` stage, after the heading/copy and before the
`st.audio_input(...)` widget, add:

```python
voice_enabled = render_voice_toggle()

render_voice_reply(
    capture_prompt(),
    "capture_prompt",
    enabled=voice_enabled,
)
```

This lets Before Use say:

> Tell me what you can see on the product...

The reply tries to autoplay once. A replay button remains visible if
the browser blocks automatic speech.

---

## 4. CONFIRM screen

After the heading/copy and before the editable fields, add:

```python
voice_enabled = render_voice_toggle()

render_voice_reply(
    confirmation_prompt(
        st.session_state.extracted_details
    ),
    "confirmation_prompt",
    enabled=voice_enabled,
)
```

This does **not** call Gemini again. It simply turns the already
interpreted candidate information into a short spoken prompt.

---

## 5. COMPLETE MISSING DETAILS screen

After:

```python
field = next_question["field"]
question = next_question["question"]
```

add:

```python
voice_enabled = render_voice_toggle()

render_voice_reply(
    missing_detail_prompt(question),
    f"missing_{field}",
    enabled=voice_enabled,
)
```

Each missing field gets a different `message_id`, so Before Use speaks
a new question once rather than repeating the previous one.

### When all available details are collected

Immediately before the `Check the evidence` button, add:

```python
voice_enabled = render_voice_toggle()

render_voice_reply(
    ready_to_check_prompt(),
    "ready_to_check",
    enabled=voice_enabled,
)
```

---

## 6. CHECKING screen

After the heading/copy, add:

```python
voice_enabled = render_voice_toggle()

render_voice_reply(
    checking_prompt(),
    "checking_prompt",
    enabled=voice_enabled,
)
```

This wording is deliberately cautious. It does not say that a check
has already succeeded.

---

## 7. RESULT placeholder

After the result heading/copy, add:

```python
voice_enabled = render_voice_toggle()

render_voice_reply(
    development_result_prompt(),
    "development_result",
    enabled=voice_enabled,
)
```

Again, the spoken message explicitly avoids claiming the product has
been verified while the evidence engine is still pending.

---

## 8. Test

Run:

```bash
python -m py_compile voice_reply.py
python -m py_compile response_builder.py
python -m py_compile app.py
```

If all three commands return no output:

```bash
streamlit run app.py
```

### What to test

1. Turn **Voice replies** on.
2. Enter the capture screen.
3. Before Use should try to speak the capture prompt.
4. If it does not autoplay, click **Hear reply**.
5. Record a product.
6. On the confirmation screen, it should speak a concise confirmation
   prompt.
7. Correct/confirm the fields.
8. If a detail is missing, Before Use should speak that follow-up
   question.
9. Turn **Voice replies** off and make sure the voice control disappears.

## Important architecture note

This is intentionally split into two responsibilities:

```text
response_builder.py
    ↓
decides WHAT Before Use says

voice_reply.py
    ↓
decides HOW the Streamlit/browser version speaks it
```

Later:

```text
FastAPI / WhatsApp
    ↓
same response_builder.py
    ↓
production tts_service.py
    ↓
actual audio file / voice note
```

So this work is not thrown away when the Streamlit frontend is
replaced.
