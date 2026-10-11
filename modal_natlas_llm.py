import os
from datetime import datetime
from typing import List, Literal

import modal


APP_NAME = "before-use-natlas-llm"

MODEL_ID = "NCAIR1/N-ATLaS"

MODEL_CACHE = "/model-cache"


app = modal.App(
    APP_NAME
)


image = (
    modal.Image.debian_slim(
        python_version="3.11"
    )
    .pip_install(
        "torch",
        "transformers>=4.48.0",
        "accelerate",
        "huggingface-hub",
        "fastapi",
        "pydantic",
    )
)


model_volume = modal.Volume.from_name(
    "before-use-natlas-llm-cache",
    create_if_missing=True,
)


hf_secret = modal.Secret.from_name(
    "before-use-hf"
)


api_secret = modal.Secret.from_name(
    "before-use-asr-api"
)


@app.cls(
    image=image,
    gpu="L4",
    memory=32768,
    timeout=600,
    scaledown_window=300,
    max_containers=1,
    volumes={
        MODEL_CACHE: model_volume
    },
    secrets=[
        hf_secret,
    ],
)
class NAtlasLLMWorker:

    @modal.enter()
    def load_model(self):

        import torch

        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
        )


        print(
            f"Loading N-ATLAS LLM: {MODEL_ID}"
        )


        hf_token = (
            os.environ.get(
                "HF_TOKEN",
                ""
            )
            .strip()
        )


        if not hf_token:

            raise RuntimeError(
                "HF_TOKEN is not available."
            )


        self.tokenizer = (
            AutoTokenizer
            .from_pretrained(
                MODEL_ID,
                token=hf_token,
                cache_dir=MODEL_CACHE,
            )
        )


        self.model = (
            AutoModelForCausalLM
            .from_pretrained(
                MODEL_ID,
                token=hf_token,
                cache_dir=MODEL_CACHE,
                torch_dtype=torch.bfloat16,
                device_map="auto",
            )
        )


        self.model.eval()


        print(
            "N-ATLAS LLM loaded successfully."
        )


    @modal.method()
    def chat(
        self,
        messages: list,
        max_tokens: int = 400,
        temperature: float = 0.0,
    ):

        import torch


        if not isinstance(
            messages,
            list,
        ):

            raise ValueError(
                "messages must be a list."
            )


        current_date = (
            datetime.utcnow()
            .strftime(
                "%d %b %Y"
            )
        )


        formatted_prompt = (
            self.tokenizer
            .apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=False,
                date_string=current_date,
            )
        )


        inputs = (
            self.tokenizer(
                formatted_prompt,
                return_tensors="pt",
            )
        )


        model_device = (
            next(
                self.model.parameters()
            )
            .device
        )


        inputs = {
            key: value.to(
                model_device
            )
            for key, value
            in inputs.items()
        }


        input_length = (
            inputs[
                "input_ids"
            ]
            .shape[1]
        )


        generation_kwargs = {
            "max_new_tokens": max_tokens,
            "pad_token_id": (
                self.tokenizer.eos_token_id
            ),
        }


        if temperature > 0:

            generation_kwargs.update(
                {
                    "do_sample": True,
                    "temperature": temperature,
                    "top_p": 0.9,
                }
            )

        else:

            generation_kwargs.update(
                {
                    "do_sample": False,
                }
            )


        with torch.inference_mode():

            output = (
                self.model.generate(
                    **inputs,
                    **generation_kwargs,
                )
            )


        generated_tokens = (
            output[
                0,
                input_length:
            ]
        )


        text = (
            self.tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True,
            )
            .strip()
        )


        return {
            "text": text,
            "model": MODEL_ID,
        }


# =========================================================
# FASTAPI GATEWAY
# =========================================================

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
)

from pydantic import (
    BaseModel,
    Field,
)


web_app = FastAPI(
    title="Before Use N-ATLAS LLM"
)


class ChatMessage(BaseModel):

    role: Literal[
        "system",
        "user",
        "assistant",
    ]

    content: str


class ChatRequest(BaseModel):

    model: str = MODEL_ID

    messages: List[
        ChatMessage
    ]

    language: str | None = None

    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
    )

    max_tokens: int = Field(
        default=400,
        ge=1,
        le=1200,
    )

    stream: bool = False


def verify_authorization(
    authorization: str | None,
):

    expected_key = (
        os.environ.get(
            "BEFORE_USE_ASR_API_KEY",
            ""
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
                "Missing Authorization header."
            ),
        )


    prefix = "Bearer "


    if not authorization.startswith(
        prefix
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "Authorization must use Bearer."
            ),
        )


    supplied_key = (
        authorization[
            len(
                prefix
            ):
        ]
        .strip()
    )


    if supplied_key != expected_key:

        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )


@web_app.get(
    "/health"
)
def health():

    return {
        "status": "ok",
        "service": (
            "before-use-natlas-llm"
        ),
        "model": MODEL_ID,
        "languages": [
            "en",
            "yo",
            "ha",
            "ig",
        ],
    }


@web_app.post(
    "/v1/chat/completions"
)
def chat_completions(
    request: ChatRequest,
    authorization: str | None = Header(
        default=None
    ),
):

    verify_authorization(
        authorization
    )


    if request.stream:

        raise HTTPException(
            status_code=400,
            detail=(
                "Streaming is not enabled "
                "in this prototype."
            ),
        )


    messages = [
        {
            "role": item.role,
            "content": item.content,
        }
        for item in request.messages
    ]


    worker = (
        NAtlasLLMWorker()
    )


    try:

        result = (
            worker.chat.remote(
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=(
                    request.temperature
                ),
            )
        )

    except Exception as exc:

        print(
            "N-ATLAS LLM ERROR:",
            type(
                exc
            ).__name__,
            str(
                exc
            ),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "N-ATLAS language model "
                "could not complete the request."
            ),
        )


    answer = (
        result.get(
            "text",
            ""
        )
        .strip()
    )


    return {
        "id": "before-use-natlas",
        "object": "chat.completion",
        "model": MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": answer,
                },
                "finish_reason": "stop",
            }
        ],
    }


@app.function(
    image=image,
    secrets=[
        api_secret,
    ],
)
@modal.asgi_app()
def fastapi_app():

    return web_app