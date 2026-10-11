import os
import time
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


DEFAULT_TIMEOUT_SECONDS = 180
MAX_ATTEMPTS = 3


# =========================================================
# HTTP SESSION
# =========================================================
#
# Reuse TCP/TLS connections rather than creating a brand
# new connection for every transcription request.
# =========================================================

_HTTP_SESSION = (
    requests.Session()
)


def _base_url() -> str:

    value = (
        os.environ.get(
            "NATLAS_ASR_BASE_URL",
            "",
        )
        .strip()
        .rstrip("/")
    )

    if not value:

        raise RuntimeError(
            "NATLAS_ASR_BASE_URL is not configured."
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
            "NATLAS_ASR_API_KEY is not configured."
        )

    return value


def _normalize_language(
    language: str,
) -> str:

    value = (
        str(
            language
            or "en"
        )
        .strip()
        .lower()
        .replace(
            "_",
            "-",
        )
    )

    aliases = {
        "en": "en",
        "english": "en",
        "nigerian english": "en",
        "en-ng": "en",

        "yo": "yo",
        "yoruba": "yo",
        "yorùbá": "yo",
        "yo-ng": "yo",

        "ha": "ha",
        "hausa": "ha",
        "ha-ng": "ha",

        "ig": "ig",
        "igbo": "ig",
        "ig-ng": "ig",
    }

    code = (
        aliases.get(
            value
        )
    )

    if not code:

        raise ValueError(
            "Unsupported N-ATLAS "
            f"language: {language}"
        )

    return code


def _audio_bytes(
    audio: Any,
) -> bytes:

    if isinstance(
        audio,
        bytes,
    ):

        return audio


    if hasattr(
        audio,
        "getvalue",
    ):

        return (
            audio.getvalue()
        )


    if hasattr(
        audio,
        "read",
    ):

        try:

            audio.seek(
                0
            )

        except Exception:

            pass

        return (
            audio.read()
        )


    raise TypeError(
        "Unsupported audio input type."
    )


def load_asr_model(
    language: str = "en",
):

    """
    Compatibility helper for the existing Streamlit app.

    N-ATLAS is hosted remotely, so this does not load
    a local ASR model.
    """

    code = (
        _normalize_language(
            language
        )
    )

    return {
        "backend": "remote_modal",
        "language": code,
    }


def check_asr_health() -> dict:

    url = (
        f"{_base_url()}/health"
    )

    response = (
        _HTTP_SESSION.get(
            url,
            timeout=30,
        )
    )

    response.raise_for_status()

    return (
        response.json()
    )


def transcribe_audio(
    audio: Any,
    language: str = "en",
) -> str:

    total_start = (
        time.perf_counter()
    )


    code = (
        _normalize_language(
            language
        )
    )


    audio_data = (
        _audio_bytes(
            audio
        )
    )


    if not audio_data:

        return ""


    filename = (
        getattr(
            audio,
            "name",
            None,
        )
        or
        "recording.wav"
    )


    content_type = (
        getattr(
            audio,
            "type",
            None,
        )
        or
        "application/octet-stream"
    )


    url = (
        f"{_base_url()}"
        "/v1/audio/transcriptions"
    )


    headers = {
        "Authorization": (
            f"Bearer {_api_key()}"
        )
    }


    data = {
        "language": code,
    }


    last_error = None


    for attempt in range(
        1,
        MAX_ATTEMPTS + 1,
    ):

        attempt_start = (
            time.perf_counter()
        )

        try:

            files = {
                "file": (
                    filename,
                    audio_data,
                    content_type,
                )
            }


            response = (
                _HTTP_SESSION.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=(
                        DEFAULT_TIMEOUT_SECONDS
                    ),
                )
            )


            request_seconds = (
                time.perf_counter()
                -
                attempt_start
            )


            if (
                response.status_code
                ==
                429

                or

                response.status_code
                >=
                500
            ):

                raise requests.HTTPError(
                    (
                        "Temporary ASR error "
                        f"{response.status_code}: "
                        f"{response.text}"
                    ),

                    response=response,
                )


            response.raise_for_status()


            payload = (
                response.json()
            )


            transcript = (
                str(
                    payload.get(
                        "text"
                    )
                    or
                    ""
                )
                .strip()
            )


            total_seconds = (
                time.perf_counter()
                -
                total_start
            )


            print(
                "N-ATLAS CLIENT TIMING:",
                {
                    "language": code,

                    "attempt": attempt,

                    "request_seconds": (
                        round(
                            request_seconds,
                            3,
                        )
                    ),

                    "total_seconds": (
                        round(
                            total_seconds,
                            3,
                        )
                    ),

                    "server_timing": (
                        payload.get(
                            "timing"
                        )
                    ),
                },
            )


            return transcript


        except (
            requests.ConnectionError,
            requests.Timeout,
            requests.HTTPError,
        ) as error:

            last_error = (
                error
            )


            print(
                "N-ATLAS REQUEST FAILED:",
                {
                    "attempt": attempt,

                    "error": str(
                        error
                    ),
                },
            )


            if (
                attempt
                >=
                MAX_ATTEMPTS
            ):

                break


            time.sleep(
                2 ** (
                    attempt
                    -
                    1
                )
            )


    raise RuntimeError(
        "N-ATLAS transcription service "
        "is temporarily unavailable. "
        f"{last_error}"
    )