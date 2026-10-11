"""Before Use server-generated TTS (English and Yorùbá)."""
import asyncio
import base64
import os
import time
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


async def _english_audio_async(text: str) -> bytes:
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError('English voice requires edge-tts in requirements.txt.') from exc
    voice = os.environ.get('ENGLISH_TTS_VOICE', 'en-NG-EzinneNeural').strip()
    communicate = edge_tts.Communicate(text=text, voice=voice, rate='-5%')
    chunks = []
    async for chunk in communicate.stream():
        if chunk.get('type') == 'audio':
            chunks.append(chunk['data'])
    result = b''.join(chunks)
    if not result:
        raise RuntimeError('English TTS returned no audio.')
    return result


def generate_english_speech(text: str) -> bytes:
    text = str(text or '').strip()
    if not text:
        raise ValueError('Text is required for English TTS.')
    # Streamlit executes script runs in a normal synchronous thread.
    return asyncio.run(_english_audio_async(text))


def generate_speech(text: str, language: str) -> bytes:
    language = str(language or '').strip().lower()
    if language == 'yo':
        return generate_yoruba_speech(text)
    if language == 'en':
        return generate_english_speech(text)
    raise RuntimeError(f'Audio replies are not configured for: {language}')
