import base64
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


DEFAULT_YORUBA_REFERENCE = (
    BASE_DIR
    / "voice_assets"
    / "yoruba_reference.wav"
)


# =========================================================
# ENVIRONMENT
# =========================================================

def _base_url() -> str:

    value = (
        os.environ.get(
            "YORUBA_TTS_BASE_URL",
            "",
        )
        .strip()
        .rstrip("/")
    )

    if not value:

        raise RuntimeError(
            "YORUBA_TTS_BASE_URL "
            "is not configured."
        )

    return value


def _api_key() -> str:

    value = (
        os.environ.get(
            "NATLAS_ASR_API_KEY",
            "",
        )
        .strip()
    )

    if not value:

        raise RuntimeError(
            "NATLAS_ASR_API_KEY "
            "is not configured."
        )

    return value


def _reference_text() -> str:

    value = (
        os.environ.get(
            "YORUBA_REFERENCE_TEXT",
            "",
        )
        .strip()
    )

    if not value:

        raise RuntimeError(
            "YORUBA_REFERENCE_TEXT "
            "is not configured."
        )

    return value


def _reference_audio_path() -> Path:

    configured = (
        os.environ.get(
            "YORUBA_REFERENCE_AUDIO",
            "",
        )
        .strip()
    )

    if configured:

        configured_path = (
            Path(configured)
            .expanduser()
        )

        if configured_path.is_absolute():

            path = (
                configured_path.resolve()
            )

        else:

            path = (
                BASE_DIR
                / configured_path
            ).resolve()

    else:

        path = (
            DEFAULT_YORUBA_REFERENCE
            .resolve()
        )

    if not path.exists():

        raise RuntimeError(
            "Yorùbá reference audio "
            f"was not found at: {path}"
        )

    if not path.is_file():

        raise RuntimeError(
            "Yorùbá reference audio path "
            "is not a file."
        )

    return path


# =========================================================
# HEALTH
# =========================================================

def check_yoruba_tts_health() -> dict:

    try:

        response = requests.get(
            f"{_base_url()}/health",
            timeout=15,
        )

        response.raise_for_status()

        return {
            "ok": True,
            "data": response.json(),
        }

    except Exception as exc:

        return {
            "ok": False,
            "error": (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        }


# =========================================================
# YORÙBÁ
# =========================================================

def generate_yoruba_speech(
    text: str,
) -> bytes:

    text = (
        str(
            text
            or ""
        )
        .strip()
    )

    if not text:

        raise ValueError(
            "Text is required for "
            "Yorùbá TTS."
        )

    reference_path = (
        _reference_audio_path()
    )

    print(
        "YORUBA REFERENCE AUDIO:",
        reference_path,
    )

    with open(
        reference_path,
        "rb",
    ) as reference_file:

        reference_bytes = (
            reference_file.read()
        )

    if not reference_bytes:

        raise RuntimeError(
            "The Yorùbá reference "
            "recording is empty."
        )

    reference_audio_base64 = (
        base64.b64encode(
            reference_bytes
        )
        .decode(
            "utf-8"
        )
    )

    headers = {
        "Authorization": (
            f"Bearer {_api_key()}"
        ),

        "Content-Type": (
            "application/json"
        ),
    }

    payload = {
        "text": text,

        "reference_audio_base64": (
            reference_audio_base64
        ),

        "reference_text": (
            _reference_text()
        ),

        # Preferred quality settings
        "speed": 0.95,
        "nfe_step": 24,
    }

    last_error = None

    for attempt in range(2):

        try:

            response = requests.post(
                (
                    f"{_base_url()}"
                    "/v1/audio/speech"
                ),
                headers=headers,
                json=payload,
                timeout=300,
            )

            if (
                response.status_code == 429
                or
                response.status_code >= 500
            ):

                raise requests.HTTPError(
                    (
                        "Yorùbá TTS returned "
                        f"{response.status_code}: "
                        f"{response.text[:500]}"
                    ),
                    response=response,
                )

            response.raise_for_status()

            data = (
                response.json()
            )

            audio_base64 = (
                data.get(
                    "audio_base64"
                )
            )

            if not audio_base64:

                raise RuntimeError(
                    "Yorùbá TTS returned "
                    "no audio."
                )

            audio_bytes = (
                base64.b64decode(
                    audio_base64
                )
            )

            if not audio_bytes:

                raise RuntimeError(
                    "Yorùbá TTS returned "
                    "empty audio."
                )

            return audio_bytes

        except (
            requests.ConnectionError,
            requests.Timeout,
            requests.HTTPError,
        ) as exc:

            last_error = exc

            if attempt == 0:

                time.sleep(
                    2
                )

    raise RuntimeError(
        "Yorùbá voice service "
        "is unavailable."
    ) from last_error


# =========================================================
# PUBLIC INTERFACE
# =========================================================

def generate_speech(
    text: str,
    language: str,
) -> bytes:

    language = (
        str(
            language
            or ""
        )
        .strip()
        .lower()
    )

    if language == "yo":

        return (
            generate_yoruba_speech(
                text
            )
        )

    raise RuntimeError(
        "Remote TTS is currently "
        f"configured only for Yorùbá. "
        f"Received: {language}"
    )