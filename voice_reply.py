import re
import unicodedata
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from natlas_language import (
    natlas_chat,
)

from tts_service import (
    generate_speech,
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

YORUBA_PROMPTS_DIR = (
    BASE_DIR
    / "voice_assets"
    / "yoruba_prompts"
)


# =========================================================
# LANGUAGE CONFIG
# =========================================================

LANGUAGE_CONFIG = {

    "en": {
        "name": "Nigerian English",
    },

    "yo": {
        "name": "Yorùbá",
    },

    "ha": {
        "name": "Hausa",
    },

    "ig": {
        "name": "Igbo",
    },
}


# =========================================================
# CURATED YORÙBÁ DISPLAY COPY
# =========================================================

YORUBA_DISPLAY_MESSAGES = {

    "capture_prompt": (
        "Sọ ohun tí o rí lórí ọjà náà fún mi. "
        "O lè sọ orúkọ ọjà, nọ́mbà NAFDAC, "
        "ilé-iṣẹ́ tó ṣe é, nọ́mbà batch àti "
        "ọjọ́ tí yóò parí. "
        "Má ṣe yọ ara rẹ lẹ́nu bí o kò bá rí gbogbo wọn. "
        "A ó jẹ́ kí o ṣàyẹ̀wò àwọn àlàyé pàtàkì "
        "kí Before Use tó ṣàyẹ̀wò ẹ̀rí."
    ),

    "confirmation_prompt": (
        "Mo ti ṣètò àwọn àlàyé tí mo gbọ́. "
        "Jọ̀wọ́ fi wọ́n wé ohun tó wà lórí "
        "ọjà tó wà lọ́wọ́ rẹ. "
        "Ṣàtúnṣe ohunkóhun tí kò bá tọ́."
    ),

    "ready_to_check": (
        "Àwọn àlàyé pàtàkì ti ṣetán. "
        "O lè tẹ bọ́tìnì náà láti jẹ́ kí "
        "Before Use ṣàyẹ̀wò ẹ̀rí tó wà."
    ),

    "checking_prompt": (
        "Before Use ń ṣàyẹ̀wò àwọn àlàyé "
        "tí o jẹ́rìí sí pẹ̀lú àwọn orísun ẹ̀rí tó wà. "
        "Èyí kò túmọ̀ sí pé ọjà náà jẹ́ ojúlówó."
    ),

    "development_result": (
        "Àbájáde yìí dá lórí ẹ̀rí tí Before Use lè rí. "
        "Ìbámu pẹ̀lú àkọsílẹ̀ ìforúkọsílẹ̀ "
        "kì í ṣe ẹ̀rí pé àpò ọjà tó wà lọ́wọ́ rẹ "
        "jẹ́ ojúlówó."
    ),

    "evidence_passport_result": (
        "Àbájáde ìṣàyẹ̀wò ti ṣetán. "
        "Jọ̀wọ́ wo àbájáde àti ẹ̀rí tó hàn "
        "lójú ìbòjú. "
        "Rántí pé ìbámu pẹ̀lú àkọsílẹ̀ "
        "ìforúkọsílẹ̀ kì í ṣe ẹ̀rí pé "
        "àpò ọjà tó wà lọ́wọ́ rẹ jẹ́ ojúlówó."
    ),

    "pharmacy_search_prompt": (
        "Sọ àgbègbè tí o fẹ́ kí n wá "
        "ilé elegbogi sí fún mi. "
        "O tún lè sọ bí o ṣe fẹ́ kí ìjìnnà náà tó. "
        "Fún àpẹẹrẹ, o lè sọ pé kí n wá "
        "ilé elegbogi ní agbègbè Ìkẹ́jà."
    ),

    "pharmacy_result_summary": (
        "Àwọn àbájáde ìwádìí ilé elegbogi ti ṣetán. "
        "Jọ̀wọ́ wo àwọn ibi tí a rí lójú ìbòjú. "
        "Ṣàyẹ̀wò àlàyé ilé elegbogi náà dáadáa "
        "kí o tó pinnu ibi tí o máa lọ."
    ),
}


# =========================================================
# CURATED YORÙBÁ SPEECH COPY
# =========================================================

YORUBA_SPEECH_MESSAGES = {

    "capture_prompt": (
        "Sọ ohun tí o rí lórí ọjà náà fún mi. "
        "O lè sọ orúkọ ọjà, nọ́mbà ìforúkọsílẹ̀, "
        "ilé-iṣẹ́ tó ṣe é, nọ́mbà ìṣelọpọ àti "
        "ọjọ́ tí yóò parí. "
        "Má ṣe yọ ara rẹ lẹ́nu bí o kò bá rí gbogbo wọn. "
        "A ó jẹ́ kí o ṣàyẹ̀wò àwọn àlàyé pàtàkì "
        "kí ètò yìí tó ṣàyẹ̀wò ẹ̀rí."
    ),

    "confirmation_prompt": (
        "Mo ti ṣètò àwọn àlàyé tí mo gbọ́. "
        "Jọ̀wọ́ fi wọ́n wé ohun tó wà lórí "
        "ọjà tó wà lọ́wọ́ rẹ. "
        "Ṣàtúnṣe ohunkóhun tí kò bá tọ́."
    ),

    "ready_to_check": (
        "Àwọn àlàyé pàtàkì ti ṣetán. "
        "O lè tẹ bọ́tìnì náà kí ètò yìí "
        "bẹ̀rẹ̀ sí í ṣàyẹ̀wò ẹ̀rí."
    ),

    "checking_prompt": (
        "Ètò yìí ń ṣàyẹ̀wò àwọn àlàyé "
        "tí o jẹ́rìí sí pẹ̀lú àwọn orísun ẹ̀rí tó wà. "
        "Èyí kò túmọ̀ sí pé ọjà náà jẹ́ ojúlówó."
    ),

    "development_result": (
        "Àbájáde yìí dá lórí ẹ̀rí tí ètò yìí lè rí. "
        "Ìbámu pẹ̀lú àkọsílẹ̀ ìforúkọsílẹ̀ "
        "kì í ṣe ẹ̀rí pé àpò ọjà tó wà lọ́wọ́ rẹ "
        "jẹ́ ojúlówó."
    ),

    "evidence_passport_result": (
        "Àbájáde ìṣàyẹ̀wò ti ṣetán. "
        "Jọ̀wọ́ wo àbájáde àti ẹ̀rí tó hàn lójú ìbòjú. "
        "Rántí pé ìbámu pẹ̀lú àkọsílẹ̀ ìforúkọsílẹ̀ "
        "kì í ṣe ẹ̀rí pé àpò ọjà tó wà lọ́wọ́ rẹ "
        "jẹ́ ojúlówó."
    ),

    "pharmacy_search_prompt": (
        "Sọ àgbègbè tí o fẹ́ kí n wá "
        "ilé elegbogi sí fún mi. "
        "O tún lè sọ bí o ṣe fẹ́ kí ìjìnnà náà tó. "
        "Fún àpẹẹrẹ, o lè sọ pé kí n wá "
        "ilé elegbogi ní agbègbè Ìkẹ́jà."
    ),

    "pharmacy_result_summary": (
        "Àwọn àbájáde ìwádìí ilé elegbogi ti ṣetán. "
        "Jọ̀wọ́ wo àwọn ibi tí a rí lójú ìbòjú. "
        "Ṣàyẹ̀wò àlàyé ilé elegbogi náà dáadáa "
        "kí o tó pinnu ibi tí o máa lọ."
    ),
}


# =========================================================
# MISSING FIELD MESSAGES
# =========================================================

YORUBA_MISSING_FIELD_DISPLAY = {

    "product_name": (
        "Kí ni orúkọ ọjà náà?"
    ),

    "nafdac_number": (
        "Kí ni nọ́mbà NAFDAC tó wà lórí ọjà náà?"
    ),

    "manufacturer": (
        "Ilé-iṣẹ́ wo ni wọ́n sọ pé ó ṣe ọjà náà?"
    ),

    "batch_number": (
        "Kí ni nọ́mbà batch tó wà lórí ọjà náà?"
    ),

    "expiry_date": (
        "Ọjọ́ wo ni wọ́n sọ pé ọjà náà yóò parí?"
    ),
}


YORUBA_MISSING_FIELD_SPEECH = {

    "product_name": (
        "Kí ni orúkọ ọjà náà?"
    ),

    "nafdac_number": (
        "Kí ni nọ́mbà ìforúkọsílẹ̀ "
        "tó wà lórí ọjà náà?"
    ),

    "manufacturer": (
        "Ilé-iṣẹ́ wo ni wọ́n sọ pé "
        "ó ṣe ọjà náà?"
    ),

    "batch_number": (
        "Kí ni nọ́mbà ìṣelọpọ "
        "tó wà lórí ọjà náà?"
    ),

    "expiry_date": (
        "Ọjọ́ wo ni wọ́n sọ pé "
        "ọjà náà yóò parí?"
    ),
}


# =========================================================
# LANGUAGE
# =========================================================

def _selected_language():

    language = (
        st.session_state.get(
            "selected_language",
            "en",
        )
    )

    if language not in LANGUAGE_CONFIG:
        return "en"

    return language


# =========================================================
# YORÙBÁ QUALITY HELPERS
# =========================================================

def _contains_yoruba_marks(
    text: str,
) -> bool:

    if not text:
        return False

    lowered = (
        unicodedata.normalize(
            "NFC",
            text,
        )
        .lower()
    )

    if any(
        letter in lowered
        for letter in (
            "ẹ",
            "ọ",
            "ṣ",
        )
    ):
        return True

    decomposed = (
        unicodedata.normalize(
            "NFD",
            lowered,
        )
    )

    return any(
        mark in decomposed
        for mark in {
            "\u0300",
            "\u0301",
            "\u0304",
        }
    )


def _looks_like_bad_yoruba(
    text: str,
) -> bool:

    if not text:
        return True

    words = re.findall(
        r"[A-Za-zÀ-ž]+",
        text,
    )

    if len(words) < 3:
        return False

    return not _contains_yoruba_marks(
        text
    )


# =========================================================
# FIXED MESSAGE LOOKUPS
# =========================================================

def _fixed_yoruba_display_message(
    message_id,
):

    message_id = (
        str(
            message_id
            or ""
        )
        .strip()
    )

    if message_id in YORUBA_DISPLAY_MESSAGES:

        return (
            YORUBA_DISPLAY_MESSAGES[
                message_id
            ]
        )

    if message_id.startswith(
        "missing_"
    ):

        field = (
            message_id[
                len("missing_"):
            ]
        )

        return (
            YORUBA_MISSING_FIELD_DISPLAY
            .get(
                field
            )
        )

    return None


def _fixed_yoruba_speech_message(
    message_id,
):

    message_id = (
        str(
            message_id
            or ""
        )
        .strip()
    )

    if message_id in YORUBA_SPEECH_MESSAGES:

        return (
            YORUBA_SPEECH_MESSAGES[
                message_id
            ]
        )

    if message_id.startswith(
        "missing_"
    ):

        field = (
            message_id[
                len("missing_"):
            ]
        )

        return (
            YORUBA_MISSING_FIELD_SPEECH
            .get(
                field
            )
        )

    return None


# =========================================================
# LOCAL YORÙBÁ AUDIO
# =========================================================

def _local_yoruba_audio_path(
    message_id,
):

    message_id = (
        str(
            message_id
            or ""
        )
        .strip()
    )

    if not message_id:
        return None

    path = (
        YORUBA_PROMPTS_DIR
        / f"{message_id}.wav"
    )

    if (
        path.exists()
        and
        path.is_file()
    ):

        return path

    return None


@st.cache_data(
    show_spinner=False,
)
def _read_local_audio(
    path_string,
):

    path = Path(
        path_string
    )

    return (
        path.read_bytes()
    )


# =========================================================
# DYNAMIC LANGUAGE FALLBACK
# =========================================================

def _yoruba_dynamic_system_prompt():

    return """
You are the Yorùbá language layer for Before Use.

Translate the supplied message into concise,
natural Standard Yorùbá.

Rules:

- Preserve the original meaning.
- Do not invent product details.
- Do not invent registration numbers.
- Do not invent batch numbers.
- Do not invent manufacturers.
- Do not add authenticity claims.
- Do not strengthen the conclusion.
- Preserve uncertainty.
- A registration match does not prove that an
  individual physical pack is genuine.
- Use natural Nigerian Yorùbá.
- Use ẹ, ọ and ṣ correctly.
- Use appropriate tone marks.
- Keep it concise.

Return only the Yorùbá message.
""".strip()


def _general_system_prompt(
    language,
):

    language_name = (
        LANGUAGE_CONFIG[
            language
        ][
            "name"
        ]
    )

    return f"""
You are the language layer for Before Use.

Render the supplied message naturally in
{language_name}.

Rules:

- Preserve product-safety meaning.
- Preserve registration numbers.
- Preserve batch numbers.
- Preserve dates.
- Do not invent information.
- Do not remove uncertainty.
- Do not strengthen conclusions.
- Keep the response concise.
- Return only the final message.
""".strip()


def _render_dynamic_text(
    text,
    language,
):

    if language == "yo":

        system_prompt = (
            _yoruba_dynamic_system_prompt()
        )

    else:

        system_prompt = (
            _general_system_prompt(
                language
            )
        )

    return (
        natlas_chat(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            language=language,
            max_tokens=400,
            temperature=0.0,
        )
    )


# =========================================================
# DISPLAY TEXT
# =========================================================

@st.cache_data(
    show_spinner=False,
    ttl=3600,
)
def _render_reply_text(
    text,
    language,
    message_id=None,
):

    text = (
        str(
            text
            or ""
        )
        .strip()
    )

    if not text:
        return ""

    if language == "en":
        return text


    if language == "yo":

        fixed = (
            _fixed_yoruba_display_message(
                message_id
            )
        )

        if fixed:

            print(
                "YORUBA DISPLAY SOURCE:",
                "curated"
            )

            print(
                "YORUBA DISPLAY TEXT:",
                fixed,
            )

            return fixed


    try:

        result = (
            _render_dynamic_text(
                text,
                language,
            )
        )

        result = (
            str(
                result
                or ""
            )
            .strip()
        )

        if result:

            if (
                language == "yo"
                and
                _looks_like_bad_yoruba(
                    result
                )
            ):

                raise RuntimeError(
                    "N-ATLAS returned "
                    "low-quality Yorùbá."
                )

            return result

    except Exception as exc:

        print(
            "LANGUAGE RENDER ERROR:",
            type(exc).__name__,
            str(exc),
        )

    return text


# =========================================================
# LIVE YORÙBÁ AUDIO FALLBACK
# =========================================================

@st.cache_data(
    show_spinner=False,
    ttl=3600,
)
def _generate_audio(
    text,
    language,
):

    return (
        generate_speech(
            text=text,
            language=language,
        )
    )


# =========================================================
# ENGLISH BROWSER SPEECH
# =========================================================

def _escape_js_text(
    text,
):

    return (
        str(
            text
            or ""
        )
        .replace(
            "\\",
            "\\\\",
        )
        .replace(
            "`",
            "\\`",
        )
        .replace(
            "${",
            "\\${",
        )
        .replace(
            "</script>",
            "<\\/script>",
        )
    )


def _render_english_browser_speech(
    text,
    message_id,
    autoplay=True,
):

    clean_text = (
        str(
            text
            or ""
        )
        .strip()
    )

    if not clean_text:
        return

    safe_text = (
        _escape_js_text(
            clean_text
        )
    )

    safe_id = (
        re.sub(
            r"[^a-zA-Z0-9_-]",
            "_",
            str(
                message_id
                or
                "english_reply"
            ),
        )
    )

    autoplay_js = (
        "speakText();"
        if autoplay
        else ""
    )

    html = f"""
    <!DOCTYPE html>

    <html>
    <body style="
        margin: 0;
        padding: 0;
        background: transparent;
        font-family: sans-serif;
    ">

        <button
            id="speak_{safe_id}"
            onclick="speakText()"
            style="
                width: 100%;
                border: 1px solid rgba(0,0,0,0.12);
                border-radius: 10px;
                padding: 10px 14px;
                background: white;
                cursor: pointer;
                font-size: 14px;
            "
        >
            🔊 Hear reply
        </button>

        <script>

            const textToSpeak = `{safe_text}`;

            function chooseEnglishVoice() {{

                const voices =
                    window.speechSynthesis.getVoices();

                const preferredCodes = [
                    "en-NG",
                    "en-GB",
                    "en-US",
                    "en"
                ];

                for (
                    const code
                    of preferredCodes
                ) {{

                    const found =
                        voices.find(
                            voice =>
                                voice.lang
                                &&
                                voice.lang
                                .toLowerCase()
                                .startsWith(
                                    code.toLowerCase()
                                )
                        );

                    if (found) {{
                        return found;
                    }}
                }}

                return null;
            }}


            function speakText() {{

                if (
                    !("speechSynthesis" in window)
                ) {{
                    return;
                }}

                window.speechSynthesis.cancel();

                const utterance =
                    new SpeechSynthesisUtterance(
                        textToSpeak
                    );

                utterance.lang = "en-NG";

                utterance.rate = 0.95;

                utterance.pitch = 1.0;

                const voice =
                    chooseEnglishVoice();

                if (voice) {{
                    utterance.voice = voice;
                }}

                window.speechSynthesis.speak(
                    utterance
                );
            }}


            if (
                window.speechSynthesis
                &&
                window.speechSynthesis
                .getVoices()
                .length
                ===
                0
            ) {{

                window.speechSynthesis
                .onvoiceschanged = () => {{

                    {autoplay_js}

                }};

            }} else {{

                {autoplay_js}

            }}

        </script>

    </body>
    </html>
    """

    components.html(
        html,
        height=52,
        scrolling=False,
    )


# =========================================================
# UI
# =========================================================

def render_voice_toggle():

    if (
        "voice_replies_enabled"
        not in st.session_state
    ):

        st.session_state[
            "voice_replies_enabled"
        ] = True

    return st.toggle(
        "🔊 Voice replies",
        key="voice_replies_enabled",
        help=(
            "When enabled, Before Use speaks "
            "short replies in your selected language."
        ),
    )


def render_voice_reply(
    text,
    message_id,
    *,
    enabled=True,
    autoplay=True,
    label="Hear reply",
):

    if not enabled:
        return

    text = (
        str(
            text
            or ""
        )
        .strip()
    )

    if not text:
        return

    language = (
        _selected_language()
    )

    language_name = (
        LANGUAGE_CONFIG[
            language
        ][
            "name"
        ]
    )


    # =====================================================
    # ENGLISH
    # =====================================================

    if language == "en":

        print(
            "ENGLISH VOICE SOURCE:",
            "browser speech"
        )

        _render_english_browser_speech(
            text=text,
            message_id=message_id,
            autoplay=autoplay,
        )

        with st.expander(
            "Read the reply"
        ):

            st.write(
                text
            )

        return


    # =====================================================
    # YORÙBÁ
    # =====================================================

    if language == "yo":

        displayed_text = (
            _render_reply_text(
                text,
                language,
                message_id,
            )
        )


        local_audio_path = (
            _local_yoruba_audio_path(
                message_id
            )
        )


        # -------------------------------------------------
        # LOCAL PRERECORDED AUDIO
        # -------------------------------------------------

        if local_audio_path:

            try:

                audio_bytes = (
                    _read_local_audio(
                        str(
                            local_audio_path
                        )
                    )
                )


                print(
                    "YORUBA AUDIO SOURCE:",
                    "local"
                )


                print(
                    "YORUBA AUDIO FILE:",
                    local_audio_path,
                )


                st.audio(
                    audio_bytes,
                    format="audio/wav",
                    autoplay=autoplay,
                )


                with st.expander(
                    "Read the Yorùbá reply"
                ):

                    st.write(
                        displayed_text
                    )


                return


            except Exception as exc:

                print(
                    "LOCAL YORUBA AUDIO ERROR:",
                    type(exc).__name__,
                    str(exc),
                )


        # -------------------------------------------------
        # LIVE F5 FALLBACK
        # -------------------------------------------------

        speech_text = (
            _fixed_yoruba_speech_message(
                message_id
            )
            or
            displayed_text
        )


        print(
            "YORUBA AUDIO SOURCE:",
            "live TTS"
        )


        print(
            "YORUBA AUDIO FILE NOT FOUND FOR:",
            message_id,
        )


        try:

            with st.spinner(
                "Generating Yorùbá voice..."
            ):

                audio_bytes = (
                    _generate_audio(
                        speech_text,
                        language,
                    )
                )


            st.audio(
                audio_bytes,
                format="audio/wav",
                autoplay=autoplay,
            )


            with st.expander(
                "Read the Yorùbá reply"
            ):

                st.write(
                    displayed_text
                )


        except Exception as exc:

            print(
                "YORUBA TTS ERROR:",
                type(exc).__name__,
                str(exc),
            )


            st.warning(
                "Yorùbá voice playback is "
                "temporarily unavailable."
            )


            st.write(
                displayed_text
            )


        return


    # =====================================================
    # HAUSA / IGBO
    # =====================================================

    displayed_text = (
        _render_reply_text(
            text,
            language,
            message_id,
        )
    )


    if language in {
        "ha",
        "ig",
    }:

        st.info(
            f"{language_name} voice is being "
            "improved. The translated reply is "
            "shown below."
        )


        st.write(
            displayed_text
        )


        return


    st.write(
        displayed_text
    )