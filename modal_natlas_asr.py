import os
import subprocess
import tempfile
import time
from typing import Optional

import modal


APP_NAME = "before-use-natlas-asr"


# =========================================================
# MODELS
# =========================================================

MODEL_MAP = {
    "en": "NCAIR1/NigerianAccentedEnglish",
    "yo": "NCAIR1/Yoruba-ASR",
    "ha": "NCAIR1/Hausa-ASR",
    "ig": "NCAIR1/Igbo-ASR",
}


LANGUAGE_ALIASES = {
    "en": "en",
    "eng": "en",
    "english": "en",
    "en-ng": "en",
    "en-us": "en",
    "en-gb": "en",
    "nigerian english": "en",
    "naija": "en",

    "yo": "yo",
    "yor": "yo",
    "yoruba": "yo",
    "yorùbá": "yo",
    "yo-ng": "yo",

    "ha": "ha",
    "hau": "ha",
    "hausa": "ha",
    "ha-ng": "ha",

    "ig": "ig",
    "ibo": "ig",
    "igbo": "ig",
    "ig-ng": "ig",
}


def normalize_language(
    value: str,
) -> str:

    normalized = (
        str(
            value
            or ""
        )
        .strip()
        .lower()
        .replace(
            "_",
            "-",
        )
    )

    code = (
        LANGUAGE_ALIASES.get(
            normalized
        )
    )

    if not code:

        raise ValueError(
            f"Unsupported language: {value}"
        )

    return code


# =========================================================
# MODAL IMAGES
# =========================================================

asr_image = (
    modal.Image
    .debian_slim(
        python_version="3.11"
    )
    .apt_install(
        "ffmpeg"
    )
    .uv_pip_install(
        "torch",
        "transformers",
        "accelerate",
        "numpy",
        "scipy",
        "soundfile",
        "huggingface-hub",
    )
)


web_image = (
    modal.Image
    .debian_slim(
        python_version="3.11"
    )
    .uv_pip_install(
        "fastapi[standard]",
        "python-multipart",
    )
)


# =========================================================
# APP + CACHE
# =========================================================

app = modal.App(
    APP_NAME
)


model_cache = (
    modal.Volume.from_name(
        "before-use-natlas-model-cache",
        create_if_missing=True,
    )
)


# =========================================================
# ASR WORKER
# =========================================================
#
# This class is parameterized by language.
#
# Because parameterized Modal classes cannot use
# min_containers directly, we use buffer_containers instead.
# =========================================================

@app.cls(
    image=asr_image,

    # -----------------------------------------------------
    # GPU
    # -----------------------------------------------------

    gpu="L4",

    cpu=2,

    memory=8192,

    timeout=300,

    startup_timeout=300,

    # -----------------------------------------------------
    # AUTOSCALING
    # -----------------------------------------------------
    #
    # min_containers is NOT allowed here because this
    # is a parameterized class.
    #
    # buffer_containers keeps spare capacity available.
    #

    buffer_containers=1,

    max_containers=1,

    # Keep an active worker around longer after use.
    scaledown_window=1200,

    # -----------------------------------------------------
    # SECRETS
    # -----------------------------------------------------

    secrets=[
        modal.Secret.from_name(
            "before-use-hf"
        )
    ],

    # -----------------------------------------------------
    # MODEL CACHE
    # -----------------------------------------------------

    volumes={
        "/cache": model_cache
    },

    env={
        "HF_HOME": "/cache/huggingface",
        "TRANSFORMERS_CACHE": "/cache/huggingface",
    },
)
@modal.concurrent(
    max_inputs=1
)
class ASRWorker:

    language: str = (
        modal.parameter()
    )


    # =====================================================
    # LOAD MODEL ONCE
    # =====================================================

    @modal.enter()
    def load_model(
        self,
    ):

        import torch

        from transformers import (
            AutoModelForSpeechSeq2Seq,
            AutoProcessor,
        )

        load_start = (
            time.perf_counter()
        )


        self.language = (
            normalize_language(
                self.language
            )
        )


        self.model_id = (
            MODEL_MAP[
                self.language
            ]
        )


        print(
            "Loading N-ATLAS ASR model:",
            self.model_id,
        )


        print(
            "CUDA available:",
            torch.cuda.is_available(),
        )


        # -------------------------------------------------
        # DEVICE
        # -------------------------------------------------

        if torch.cuda.is_available():

            self.device = (
                torch.device(
                    "cuda"
                )
            )

            self.dtype = (
                torch.float16
            )

        else:

            self.device = (
                torch.device(
                    "cpu"
                )
            )

            self.dtype = (
                torch.float32
            )

            torch.set_num_threads(
                2
            )


        # -------------------------------------------------
        # PROCESSOR
        # -------------------------------------------------

        self.processor = (
            AutoProcessor
            .from_pretrained(
                self.model_id
            )
        )


        # -------------------------------------------------
        # MODEL
        # -------------------------------------------------

        self.model = (
            AutoModelForSpeechSeq2Seq
            .from_pretrained(
                self.model_id,

                torch_dtype=(
                    self.dtype
                ),

                low_cpu_mem_usage=True,
            )
        )


        self.model.eval()


        self.model.to(
            self.device
        )


        load_seconds = (
            time.perf_counter()
            -
            load_start
        )


        print(
            "N-ATLAS model ready."
        )


        print(
            "Language:",
            self.language,
        )


        print(
            "Device:",
            self.device,
        )


        print(
            "Dtype:",
            self.dtype,
        )


        print(
            "Model load seconds:",
            round(
                load_seconds,
                2,
            ),
        )


    # =====================================================
    # TRANSCRIBE
    # =====================================================

    @modal.method()
    def transcribe(
        self,
        audio_bytes: bytes,
    ) -> dict:

        import numpy as np
        import soundfile as sf
        import torch


        request_start = (
            time.perf_counter()
        )


        if not audio_bytes:

            raise ValueError(
                "Empty audio file."
            )


        # -------------------------------------------------
        # AUDIO PREPARATION
        # -------------------------------------------------

        audio_start = (
            time.perf_counter()
        )


        with tempfile.TemporaryDirectory() as temp_dir:

            input_path = (
                os.path.join(
                    temp_dir,
                    "input_audio",
                )
            )

            output_path = (
                os.path.join(
                    temp_dir,
                    "audio.wav",
                )
            )


            with open(
                input_path,
                "wb",
            ) as file_handle:

                file_handle.write(
                    audio_bytes
                )


            command = [
                "ffmpeg",

                "-hide_banner",

                "-loglevel",
                "error",

                "-y",

                "-i",
                input_path,

                "-ac",
                "1",

                "-ar",
                "16000",

                "-t",
                "30",

                output_path,
            ]


            subprocess.run(
                command,
                check=True,
            )


            audio_array, sample_rate = (
                sf.read(
                    output_path,
                    dtype="float32",
                    always_2d=False,
                )
            )


        audio_array = (
            np.asarray(
                audio_array,
                dtype=np.float32,
            )
        )


        if (
            audio_array.ndim
            >
            1
        ):

            audio_array = (
                np.mean(
                    audio_array,
                    axis=1,
                )
            )


        audio_prepare_seconds = (
            time.perf_counter()
            -
            audio_start
        )


        # -------------------------------------------------
        # PROCESS AUDIO
        # -------------------------------------------------

        preprocess_start = (
            time.perf_counter()
        )


        inputs = (
            self.processor(
                audio_array,

                sampling_rate=(
                    int(
                        sample_rate
                    )
                ),

                return_tensors="pt",
            )
        )


        input_features = (
            inputs.input_features
            .to(
                device=self.device,
                dtype=self.dtype,
            )
        )


        preprocess_seconds = (
            time.perf_counter()
            -
            preprocess_start
        )


        # -------------------------------------------------
        # INFERENCE
        # -------------------------------------------------

        inference_start = (
            time.perf_counter()
        )


        with torch.inference_mode():

            generated_ids = (
                self.model.generate(
                    input_features,

                    do_sample=False,

                    num_beams=1,

                    max_new_tokens=128,
                )
            )


        if (
            self.device.type
            ==
            "cuda"
        ):

            torch.cuda.synchronize()


        inference_seconds = (
            time.perf_counter()
            -
            inference_start
        )


        # -------------------------------------------------
        # DECODE
        # -------------------------------------------------

        decode_start = (
            time.perf_counter()
        )


        transcript = (
            self.processor
            .batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )[0]
            .strip()
        )


        decode_seconds = (
            time.perf_counter()
            -
            decode_start
        )


        total_seconds = (
            time.perf_counter()
            -
            request_start
        )


        timing = {

            "audio_prepare_seconds": (
                round(
                    audio_prepare_seconds,
                    3,
                )
            ),

            "preprocess_seconds": (
                round(
                    preprocess_seconds,
                    3,
                )
            ),

            "inference_seconds": (
                round(
                    inference_seconds,
                    3,
                )
            ),

            "decode_seconds": (
                round(
                    decode_seconds,
                    3,
                )
            ),

            "total_seconds": (
                round(
                    total_seconds,
                    3,
                )
            ),
        }


        print(
            "ASR TIMING:",
            {
                "language": (
                    self.language
                ),

                **timing,
            },
        )


        return {

            "text": transcript,

            "language": (
                self.language
            ),

            "model": (
                self.model_id
            ),

            "timing": timing,
        }


# =========================================================
# FASTAPI SERVICE
# =========================================================

@app.function(
    image=web_image,

    secrets=[
        modal.Secret.from_name(
            "before-use-asr-api"
        )
    ],

    timeout=300,
)
@modal.asgi_app()
def fastapi_app():

    from fastapi import (
        FastAPI,
        File,
        Form,
        Header,
        HTTPException,
        UploadFile,
    )


    api = FastAPI(
        title=(
            "Before Use N-ATLAS ASR"
        ),

        version="1.1",
    )


    # =====================================================
    # AUTH
    # =====================================================

    def verify_authorization(
        authorization: Optional[str],
    ):

        expected = (
            os.environ.get(
                "BEFORE_USE_ASR_API_KEY",
                "",
            )
        )


        if not expected:

            raise HTTPException(
                status_code=500,

                detail=(
                    "ASR API key is not "
                    "configured."
                ),
            )


        expected_header = (
            f"Bearer {expected}"
        )


        if (
            authorization
            !=
            expected_header
        ):

            raise HTTPException(
                status_code=401,

                detail=(
                    "Missing or invalid "
                    "API key."
                ),
            )


    # =====================================================
    # HEALTH
    # =====================================================

    @api.get(
        "/health"
    )
    async def health():

        return {

            "status": "ok",

            "service": (
                "Before Use N-ATLAS ASR"
            ),

            "version": "1.1",

            "languages": [
                "en",
                "yo",
                "ha",
                "ig",
            ],

            "models": (
                MODEL_MAP
            ),

            "worker": {

                "accelerator": "L4",

                "max_audio_seconds": 30,

                "buffer_containers": 1,

                "scaledown_window_seconds": 1200,
            },
        }


    # =====================================================
    # TRANSCRIPTION
    # =====================================================

    @api.post(
        "/v1/audio/transcriptions"
    )
    async def transcriptions(

        file: UploadFile = File(...),

        language: str = Form(...),

        authorization: Optional[str] = (
            Header(
                default=None
            )
        ),
    ):

        verify_authorization(
            authorization
        )


        # -------------------------------------------------
        # LANGUAGE
        # -------------------------------------------------

        try:

            code = (
                normalize_language(
                    language
                )
            )

        except ValueError as error:

            raise HTTPException(
                status_code=400,

                detail=str(
                    error
                ),
            )


        # -------------------------------------------------
        # AUDIO
        # -------------------------------------------------

        audio_bytes = (
            await file.read()
        )


        if not audio_bytes:

            raise HTTPException(
                status_code=400,

                detail=(
                    "Audio file is empty."
                ),
            )


        max_bytes = (
            25
            *
            1024
            *
            1024
        )


        if (
            len(
                audio_bytes
            )
            >
            max_bytes
        ):

            raise HTTPException(
                status_code=413,

                detail=(
                    "Audio file is too large."
                ),
            )


        # -------------------------------------------------
        # PARAMETERIZED WORKER
        # -------------------------------------------------

        worker = (
            ASRWorker(
                language=code
            )
        )


        try:

            result = (
                await worker
                .transcribe
                .remote
                .aio(
                    audio_bytes
                )
            )


        except Exception as error:

            print(
                "ASR ERROR:",

                type(
                    error
                ).__name__,

                str(
                    error
                ),
            )


            raise HTTPException(
                status_code=500,

                detail=(
                    "N-ATLAS transcription "
                    "failed."
                ),
            )


        return result


    return api