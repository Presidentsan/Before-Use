import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv


load_dotenv()


MODEL_ID = "NCAIR1/N-ATLaS"


LANGUAGE_NAMES = {
    "en": "Nigerian English",
    "yo": "Yorùbá",
    "ha": "Hausa",
    "ig": "Igbo",
}


def _base_url() -> str:
    """
    Return the deployed N-ATLAS LLM gateway URL.
    """

    value = (
        os.environ.get(
            "NATLAS_LLM_BASE_URL",
            "",
        )
        .strip()
        .rstrip("/")
    )

    if not value:
        raise RuntimeError(
            "NATLAS_LLM_BASE_URL is not configured."
        )

    return value


def _api_key() -> str:
    """
    Reuse the private API key already used by
    the N-ATLAS ASR service.
    """

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


def language_name(
    language: Optional[str],
) -> str:
    """
    Convert language code to readable name.
    """

    return LANGUAGE_NAMES.get(
        language or "",
        "the language used by the speaker",
    )


def check_natlas_llm_health() -> dict:
    """
    Check whether the remote N-ATLAS LLM
    gateway is reachable.
    """

    url = (
        f"{_base_url()}/health"
    )

    try:

        response = requests.get(
            url,
            timeout=10,
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
                f"{type(exc).__name__}: {exc}"
            ),
        }


def natlas_chat(
    messages: list,
    language: Optional[str] = None,
    max_tokens: int = 400,
    temperature: float = 0.0,
) -> str:
    """
    Send a chat request to the remote N-ATLAS
    language-model service running on Modal.
    """

    url = (
        f"{_base_url()}"
        "/v1/chat/completions"
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
        "model": MODEL_ID,
        "messages": messages,
        "language": language,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_error = None

    for attempt in range(3):

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=180,
            )

            if (
                response.status_code == 429
                or
                response.status_code >= 500
            ):

                raise requests.HTTPError(
                    (
                        f"N-ATLAS returned "
                        f"{response.status_code}: "
                        f"{response.text[:500]}"
                    ),
                    response=response,
                )

            response.raise_for_status()

            data = response.json()

            choices = (
                data.get(
                    "choices"
                )
                or []
            )

            if not choices:

                raise RuntimeError(
                    "N-ATLAS returned no completion choices."
                )

            content = (
                choices[0]
                .get(
                    "message",
                    {}
                )
                .get(
                    "content",
                    ""
                )
                .strip()
            )

            if not content:

                raise RuntimeError(
                    "N-ATLAS returned an empty response."
                )

            return content

        except (
            requests.ConnectionError,
            requests.Timeout,
            requests.HTTPError,
        ) as exc:

            last_error = exc

            if attempt < 2:

                time.sleep(
                    2 ** attempt
                )

    raise RuntimeError(
        "N-ATLAS language service is unavailable."
    ) from last_error