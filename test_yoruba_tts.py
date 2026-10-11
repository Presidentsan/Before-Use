from pathlib import Path

from tts_service import (
    generate_yoruba_speech,
)


TEST_TEXT = (
    "Ẹ kú àárọ̀. "
    "Kí ni orúkọ ọja yìí?"
)


audio = (
    generate_yoruba_speech(
        TEST_TEXT
    )
)


output = (
    Path(
        "yoruba_f5_test.wav"
    )
)


output.write_bytes(
    audio
)


print(
    "Saved:",
    output.resolve(),
)

print(
    "Audio bytes:",
    len(audio),
)