import io

import torch
import scipy.io.wavfile
from transformers import (
    AutoTokenizer,
    VitsModel,
)


MODEL_ID = "Shinzmann/soro-tts-yor"


_model = None
_tokenizer = None


def _load_model():
    global _model
    global _tokenizer

    if (
        _model is not None
        and _tokenizer is not None
    ):
        return _model, _tokenizer


    print(
        "Loading Soro-TTS Yorùbá model..."
    )


    _tokenizer = (
        AutoTokenizer.from_pretrained(
            MODEL_ID
        )
    )


    _model = (
        VitsModel.from_pretrained(
            MODEL_ID
        )
    )


    _model.eval()


    print(
        "Soro-TTS Yorùbá loaded."
    )


    return (
        _model,
        _tokenizer,
    )


def generate_yoruba_speech(
    text: str,
) -> bytes:
    """
    Convert Yorùbá text into WAV audio.

    Returns:
        WAV bytes suitable for st.audio().
    """

    text = (
        str(
            text
            or ""
        )
        .strip()
    )


    if not text:
        raise ValueError(
            "Yorùbá TTS text is empty."
        )


    model, tokenizer = (
        _load_model()
    )


    inputs = (
        tokenizer(
            text,
            return_tensors="pt",
        )
    )


    with torch.no_grad():

        output = (
            model(
                **inputs
            )
        )


    waveform = (
        output.waveform[
            0
        ]
        .cpu()
        .numpy()
    )


    buffer = io.BytesIO()


    scipy.io.wavfile.write(
        buffer,
        rate=model.config.sampling_rate,
        data=waveform,
    )


    buffer.seek(0)


    return buffer.read()