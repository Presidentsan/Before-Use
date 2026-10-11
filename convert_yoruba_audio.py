from pathlib import Path
import subprocess
import imageio_ffmpeg


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

INPUT_FILE = (
    BASE_DIR
    / "voice_assets"
    / "yoruba_reference.wav.m4a"
)

OUTPUT_FILE = (
    BASE_DIR
    / "voice_assets"
    / "yoruba_reference.wav"
)


if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"Input file not found: {INPUT_FILE}"
    )


ffmpeg = (
    imageio_ffmpeg.get_ffmpeg_exe()
)


print(
    "Using bundled FFmpeg:"
)

print(
    ffmpeg
)


command = [
    ffmpeg,

    "-y",

    "-i",
    str(INPUT_FILE),

    "-ac",
    "1",

    "-ar",
    "24000",

    "-c:a",
    "pcm_s16le",

    str(OUTPUT_FILE),
]


result = subprocess.run(
    command,
    capture_output=True,
    text=True,
)


if result.returncode != 0:

    print(
        result.stderr
    )

    raise RuntimeError(
        "Audio conversion failed."
    )


if not OUTPUT_FILE.exists():

    raise RuntimeError(
        "Conversion completed but the WAV "
        "file was not created."
    )


print()

print(
    "Created:"
)

print(
    OUTPUT_FILE
)

print()

print(
    "File size:",
    OUTPUT_FILE.stat().st_size,
    "bytes",
)

print()

print(
    "Conversion successful."
)