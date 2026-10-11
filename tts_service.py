"""Before Use server-generated TTS (English through Gemini, Yorùbá through Modal)."""
import base64
import io
import os
import time
import wave
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_YORUBA_REFERENCE = BASE_DIR / 'voice_assets' / 'yoruba_reference.wav'


def _required_environment(name: str) -> str:
    value = os.environ.get(name, '').strip()
    if not value:
        raise RuntimeError(f'{name} is not configured.')
    return value


def _base_url() -> str:
    return _required_environment('YORUBA_TTS_BASE_URL').rstrip('/')


def _api_key() -> str:
    return _required_environment('NATLAS_ASR_API_KEY')


def _reference_text() -> str:
    return _required_environment('YORUBA_REFERENCE_TEXT')


def _reference_audio_path() -> Path:
    configured = os.environ.get('YORUBA_REFERENCE_AUDIO', '').strip()
    path = Path(configured).expanduser() if configured else DEFAULT_YORUBA_REFERENCE
    if not path.is_absolute():
        path = BASE_DIR / path
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f'Yorùbá reference audio was not found at: {path}')
    return path


def check_yoruba_tts_health() -> dict:
    try:
        response = requests.get(f'{_base_url()}/health', timeout=15)
        response.raise_for_status()
        return {'ok': True, 'data': response.json()}
    except Exception as exc:
        return {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}


def generate_yoruba_speech(text: str) -> bytes:
    text = str(text or '').strip()
    if not text:
        raise ValueError('Text is required for Yorùbá TTS.')
    reference_bytes = _reference_audio_path().read_bytes()
    if not reference_bytes:
        raise RuntimeError('The Yorùbá reference recording is empty.')
    payload = {
        'text': text,
        'reference_audio_base64': base64.b64encode(reference_bytes).decode('utf-8'),
        'reference_text': _reference_text(),
        'speed': 0.95,
        'nfe_step': 24,
    }
    headers = {'Authorization': f'Bearer {_api_key()}', 'Content-Type': 'application/json'}
    last_error = None
    for attempt in range(2):
        try:
            response = requests.post(
                f'{_base_url()}/v1/audio/speech',
                headers=headers, json=payload, timeout=300,
            )
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(
                    f'Yorùbá TTS returned {response.status_code}: {response.text[:500]}',
                    response=response,
                )
            response.raise_for_status()
            data = response.json()
            encoded = data.get('audio_base64')
            if not encoded:
                raise RuntimeError('Yorùbá TTS returned no audio.')
            audio_bytes = base64.b64decode(encoded, validate=True)
            if not audio_bytes:
                raise RuntimeError('Yorùbá TTS returned empty audio.')
            return audio_bytes
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(2)
    raise RuntimeError('Yorùbá voice service is unavailable.') from last_error


def _pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    if not pcm:
        raise RuntimeError('Gemini TTS returned empty PCM audio.')
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)
    return buffer.getvalue()


def generate_english_speech(text: str) -> bytes:
    """Return playable WAV bytes. Requires a Gemini API key with TTS access."""
    text = str(text or '').strip()
    if not text:
        raise ValueError('Text is required for English TTS.')

    key = os.environ.get('GEMINI_API_KEY', '').strip() or os.environ.get('GOOGLE_API_KEY', '').strip()
    if not key:
        raise RuntimeError('GEMINI_API_KEY (or GOOGLE_API_KEY) is not configured.')

    from google import genai
    from google.genai import types

    model = os.environ.get('ENGLISH_TTS_MODEL', 'gemini-3.1-flash-tts-preview').strip()
    voice = os.environ.get('GEMINI_TTS_VOICE', 'Kore').strip()
    client = genai.Client(api_key=key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=f'Read the following exactly, in a calm, friendly Nigerian English style: {text}',
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                ),
            ),
        )
        candidates = response.candidates or []
        parts = candidates[0].content.parts if candidates and candidates[0].content else []
        for part in parts:
            inline = getattr(part, 'inline_data', None)
            if inline and inline.data:
                raw = inline.data
                if isinstance(raw, str):
                    raw = base64.b64decode(raw)
                raw = bytes(raw)
                if raw.startswith(b'RIFF') and raw[8:12] == b'WAVE':
                    return raw
                return _pcm_to_wav(raw)
        raise RuntimeError('Gemini returned no English audio. Check TTS model availability and quota.')
    finally:
        client.close()


def generate_speech(text: str, language: str) -> bytes:
    language = str(language or '').strip().lower()
    if language == 'yo':
        return generate_yoruba_speech(text)
    if language == 'en':
        return generate_english_speech(text)
    raise RuntimeError(f'Audio replies are not configured for: {language}')
