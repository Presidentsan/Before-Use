import base64
import os
import tempfile
from pathlib import Path

import modal


# =========================================================
# CONFIG
# =========================================================

MODEL_REPO = "naijaml/f5-tts-yoruba"

MODEL_FILENAME = "model_150000.pt"

VOCAB_FILENAME = "vocab.txt"


app = modal.App(
    "before-use-yoruba-tts"
)


# =========================================================
# IMAGE
# =========================================================

image = (
    modal.Image.debian_slim(
        python_version="3.10"
    )
    .apt_install(
        "ffmpeg",
        "libsndfile1",
    )
    .pip_install(
        "torch",
        "torchaudio",
        "f5-tts",
        "huggingface_hub",
        "fastapi",
        "uvicorn",
        "soundfile",
        "numpy",
    )
)


# =========================================================
# MODEL CACHE
# =========================================================

model_volume = modal.Volume.from_name(
    "before-use-yoruba-tts-cache",
    create_if_missing=True,
)


MODEL_CACHE_DIR = "/models"


# =========================================================
# GPU WORKER
# =========================================================

@app.cls(
    image=image,
    gpu="L4",
    memory=16384,
    timeout=600,
    scaledown_window=300,
    max_containers=1,
    volumes={
        MODEL_CACHE_DIR: model_volume,
    },
    secrets=[
        modal.Secret.from_name(
            "before-use-hf"
        ),
    ],
)
class YorubaTTSWorker:

    @modal.enter()
    def load_model(self):
        """
        Load the Yorùbá F5-TTS model once when the
        GPU container starts.
        """

        print(
            "Starting Yorùbá F5-TTS model..."
        )

        from huggingface_hub import (
            hf_hub_download,
        )


        # -------------------------------------------------
        # Download model files into persistent Modal volume
        # -------------------------------------------------

        checkpoint_path = (
            hf_hub_download(
                repo_id=MODEL_REPO,
                filename=MODEL_FILENAME,
                cache_dir=MODEL_CACHE_DIR,
            )
        )


        vocab_path = (
            hf_hub_download(
                repo_id=MODEL_REPO,
                filename=VOCAB_FILENAME,
                cache_dir=MODEL_CACHE_DIR,
            )
        )


        model_volume.commit()


        print(
            "Yorùbá checkpoint:",
            checkpoint_path,
        )

        print(
            "Yorùbá vocab:",
            vocab_path,
        )


        # -------------------------------------------------
        # IMPORTANT:
        #
        # NaijaML explicitly requires F5's default pinyin
        # conversion to be bypassed for Yorùbá.
        #
        # This must happen before importing F5TTS.
        # -------------------------------------------------

        import f5_tts.model.utils as f5_utils

        f5_utils.convert_char_to_pinyin = (
            lambda texts, polyphone=True: texts
        )


        from f5_tts.api import F5TTS


        self.tts = F5TTS(
            model="F5TTS_v1_Base",
            ckpt_file=checkpoint_path,
            vocab_file=vocab_path,
            device="cuda",
        )


        print(
            "Yorùbá F5-TTS ready."
        )


    @modal.method()
    def generate(
        self,
        text: str,
        reference_audio: bytes,
        reference_text: str,
        speed: float = 1.0,
        nfe_step: int = 16,
    ) -> bytes:
        """
        Generate Yorùbá speech.

        Input:
            text
            reference WAV bytes
            exact transcript of reference WAV

        Output:
            WAV bytes
        """

        text = (
            str(
                text
                or ""
            )
            .strip()
        )


        reference_text = (
            str(
                reference_text
                or ""
            )
            .strip()
        )


        if not text:
            raise ValueError(
                "Generation text is empty."
            )


        if not reference_text:
            raise ValueError(
                "Reference transcript is empty."
            )


        if not reference_audio:
            raise ValueError(
                "Reference audio is empty."
            )


        # Keep inference settings inside safe range.

        try:
            speed = float(speed)
        except Exception:
            speed = 1.0


        if speed < 0.75:
            speed = 0.75

        if speed > 1.25:
            speed = 1.25


        try:
            nfe_step = int(nfe_step)
        except Exception:
            nfe_step = 16


        if nfe_step not in {
            8,
            16,
            24,
            32,
        }:
            nfe_step = 16


        reference_path = None
        output_path = None


        try:

            # ---------------------------------------------
            # Write uploaded reference voice temporarily
            # ---------------------------------------------

            reference_file = (
                tempfile.NamedTemporaryFile(
                    suffix=".wav",
                    delete=False,
                )
            )

            reference_path = (
                reference_file.name
            )

            reference_file.write(
                reference_audio
            )

            reference_file.close()


            # ---------------------------------------------
            # Temporary output file
            # ---------------------------------------------

            output_file = (
                tempfile.NamedTemporaryFile(
                    suffix=".wav",
                    delete=False,
                )
            )

            output_path = (
                output_file.name
            )

            output_file.close()


            # ---------------------------------------------
            # INFERENCE
            # ---------------------------------------------

            print(
                "Generating Yorùbá speech:",
                text[:160],
            )


            wav, sample_rate, _ = (
                self.tts.infer(
                    ref_file=reference_path,
                    ref_text=reference_text,
                    gen_text=text,
                    speed=speed,
                    nfe_step=nfe_step,
                    file_wave=output_path,
                )
            )


            # F5-TTS normally writes file_wave.
            # Read that file rather than serialising the
            # numpy result ourselves.

            if (
                output_path
                and
                os.path.exists(
                    output_path
                )
                and
                os.path.getsize(
                    output_path
                ) > 0
            ):

                with open(
                    output_path,
                    "rb",
                ) as audio_file:

                    audio_bytes = (
                        audio_file.read()
                    )


            else:

                # Defensive fallback if the package
                # version does not write file_wave.

                import io
                import soundfile as sf


                audio_buffer = (
                    io.BytesIO()
                )


                sf.write(
                    audio_buffer,
                    wav,
                    sample_rate,
                    format="WAV",
                )


                audio_buffer.seek(0)


                audio_bytes = (
                    audio_buffer.read()
                )


            if not audio_bytes:
                raise RuntimeError(
                    "F5-TTS produced empty audio."
                )


            print(
                "Yorùbá generation complete."
            )


            return audio_bytes


        finally:

            for path in [
                reference_path,
                output_path,
            ]:

                if (
                    path
                    and
                    os.path.exists(
                        path
                    )
                ):

                    try:
                        os.remove(
                            path
                        )
                    except Exception:
                        pass


# =========================================================
# FASTAPI
# =========================================================

@app.function(
    image=image,
    timeout=300,
    secrets=[
        modal.Secret.from_name(
            "before-use-asr-api"
        ),
    ],
)
@modal.asgi_app()
def fastapi_app():

    from fastapi import (
        FastAPI,
        Header,
        HTTPException,
    )

    from pydantic import (
        BaseModel,
    )


    api = FastAPI(
        title="Before Use Yorùbá TTS",
        version="1.0",
    )


    worker = (
        YorubaTTSWorker()
    )


    # -----------------------------------------------------
    # REQUEST MODEL
    # -----------------------------------------------------

    class TTSRequest(
        BaseModel
    ):

        text: str

        reference_audio_base64: str

        reference_text: str

        speed: float = 1.0

        nfe_step: int = 16


    # -----------------------------------------------------
    # AUTH
    # -----------------------------------------------------

    def verify_api_key(
        authorization: str | None,
    ):

        expected_key = (
            os.environ.get(
                "BEFORE_USE_ASR_API_KEY",
                "",
            )
            .strip()
        )


        if not expected_key:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Server API key "
                    "is not configured."
                ),
            )


        if not authorization:

            raise HTTPException(
                status_code=401,
                detail=(
                    "Authorization header missing."
                ),
            )


        expected_header = (
            f"Bearer {expected_key}"
        )


        if authorization != expected_header:

            raise HTTPException(
                status_code=401,
                detail="Invalid API key.",
            )


    # -----------------------------------------------------
    # HEALTH
    # -----------------------------------------------------

    @api.get(
        "/health"
    )
    def health():

        return {
            "ok": True,
            "service": (
                "Before Use Yorùbá TTS"
            ),
            "model": MODEL_REPO,
        }


    # -----------------------------------------------------
    # TTS
    # -----------------------------------------------------

    @api.post(
        "/v1/audio/speech"
    )
    def speech(
        request: TTSRequest,
        authorization: str | None = (
            Header(
                default=None
            )
        ),
    ):

        verify_api_key(
            authorization
        )


        try:

            reference_audio = (
                base64.b64decode(
                    request.reference_audio_base64
                )
            )


        except Exception as exc:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid reference audio."
                ),
            ) from exc


        try:

            audio_bytes = (
                worker.generate.remote(
                    text=request.text,
                    reference_audio=reference_audio,
                    reference_text=(
                        request.reference_text
                    ),
                    speed=(
                        request.speed
                    ),
                    nfe_step=(
                        request.nfe_step
                    ),
                )
            )


        except Exception as exc:

            print(
                "YORUBA TTS ERROR:",
                type(exc).__name__,
                str(exc),
            )


            raise HTTPException(
                status_code=500,
                detail=(
                    "Yorùbá speech generation failed."
                ),
            ) from exc


        return {
            "audio_base64": (
                base64.b64encode(
                    audio_bytes
                )
                .decode(
                    "utf-8"
                )
            ),

            "format": (
                "wav"
            ),

            "language": (
                "yo"
            ),

            "model": (
                MODEL_REPO
            ),
        }


    return api