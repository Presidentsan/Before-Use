import base64
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


REFERENCE_FILE = (
    BASE_DIR
    / "voice_assets"
    / "yoruba_reference.wav"
)


TEST_TEXT = (
    "Ẹ kú àárọ̀. "
    "Kí ni orúkọ ọja yìí?"
)


BASE_URL = (
    os.environ.get(
        "YORUBA_TTS_BASE_URL",
        "",
    )
    .strip()
    .rstrip("/")
)


API_KEY = (
    os.environ.get(
        "NATLAS_ASR_API_KEY",
        "",
    )
    .strip()
)


REFERENCE_TEXT = (
    os.environ.get(
        "YORUBA_REFERENCE_TEXT",
        "",
    )
    .strip()
)


if not BASE_URL:
    raise RuntimeError(
        "YORUBA_TTS_BASE_URL is missing."
    )


if not API_KEY:
    raise RuntimeError(
        "NATLAS_ASR_API_KEY is missing."
    )


if not REFERENCE_TEXT:
    raise RuntimeError(
        "YORUBA_REFERENCE_TEXT is missing."
    )


if not REFERENCE_FILE.exists():
    raise RuntimeError(
        f"Reference audio not found: {REFERENCE_FILE}"
    )


reference_audio = (
    REFERENCE_FILE.read_bytes()
)


reference_base64 = (
    base64.b64encode(
        reference_audio
    )
    .decode("utf-8")
)


headers = {
    "Authorization": (
        f"Bearer {API_KEY}"
    ),
    "Content-Type": (
        "application/json"
    ),
}


tests = [
    {
        "name": "quality_16",
        "nfe_step": 16,
        "speed": 1.0,
    },
    {
        "name": "quality_24",
        "nfe_step": 24,
        "speed": 0.95,
    },
    {
        "name": "quality_32",
        "nfe_step": 32,
        "speed": 0.95,
    },
]


for test in tests:

    print()
    print(
        "Generating:",
        test["name"],
    )


    payload = {
        "text": TEST_TEXT,

        "reference_audio_base64": (
            reference_base64
        ),

        "reference_text": (
            REFERENCE_TEXT
        ),

        "speed": (
            test["speed"]
        ),

        "nfe_step": (
            test["nfe_step"]
        ),
    }


    response = requests.post(
        (
            f"{BASE_URL}"
            "/v1/audio/speech"
        ),
        headers=headers,
        json=payload,
        timeout=300,
    )


    if not response.ok:

        print(
            "FAILED:",
            response.status_code,
            response.text[:500],
        )

        continue


    data = response.json()


    audio_base64 = (
        data.get(
            "audio_base64"
        )
    )


    if not audio_base64:

        print(
            "No audio returned."
        )

        continue


    audio_bytes = (
        base64.b64decode(
            audio_base64
        )
    )


    output_file = (
        BASE_DIR
        / f"yoruba_{test['name']}.wav"
    )


    output_file.write_bytes(
        audio_bytes
    )


    print(
        "Saved:",
        output_file.name,
    )


print()
print(
    "Finished. Listen to all three files."
)