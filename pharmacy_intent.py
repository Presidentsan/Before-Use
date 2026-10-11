import os
import re
from typing import Optional

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field


load_dotenv()

MODEL_ID = "gemini-3.5-flash-lite"


class PharmacyIntent(BaseModel):
    intent: str = Field(default="find_pharmacy")
    location: Optional[str] = None
    radius_km: int = 5
    raw_request: Optional[str] = None


def _clamp_radius(value: int) -> int:
    return max(1, min(int(value), 10))


def _local_fallback(text: str) -> PharmacyIntent:
    cleaned = (text or "").strip()
    radius = 5

    radius_match = re.search(
        r"\b(?:within|about|around|roughly)?\s*(\d{1,2})\s*(?:km|kilometres?|kilometers?)\b",
        cleaned,
        flags=re.IGNORECASE,
    )

    if radius_match:
        radius = _clamp_radius(int(radius_match.group(1)))

    location = None

    patterns = [
        r"(?:around|near|in|at|within)\s+(.+?)(?:\s+within\s+\d|\s+about\s+\d|\s+\d+\s*km|$)",
        r"pharmac(?:y|ies)\s+(?:around|near|in|at)\s+(.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)

        if match:
            candidate = match.group(1).strip(" .,")

            if candidate:
                location = candidate
                break

    return PharmacyIntent(
        location=location,
        radius_km=radius,
        raw_request=cleaned,
    )


def interpret_pharmacy_request(
    text: str,
) -> PharmacyIntent:

    cleaned = (text or "").strip()

    if not cleaned:
        return PharmacyIntent(
            raw_request=""
        )

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        return _local_fallback(
            cleaned
        )

    prompt = f"""
You are the intent interpreter for Before Use,
a Nigerian consumer medicine-safety app.

Extract the pharmacy-search intent from the user's words.

Rules:
- intent must be exactly: find_pharmacy
- Do not invent a location the user did not say.
- Preserve Nigerian place names carefully.
- Do not infer a home address.
- radius_km must be an integer from 1 to 10.
- If no radius was spoken, use 5.
- If the location is missing or unclear, return location as null.
- raw_request must contain the original request.

User request:
{cleaned}
"""

    try:
        client = genai.Client(
            api_key=api_key
        )

        response = (
            client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config={
                    "response_mime_type": (
                        "application/json"
                    ),
                    "response_schema": (
                        PharmacyIntent
                    ),
                    "temperature": 0,
                },
            )
        )

        parsed = response.parsed

        if parsed is None:
            return _local_fallback(
                cleaned
            )

        if isinstance(
            parsed,
            PharmacyIntent,
        ):
            result = parsed

        else:
            result = (
                PharmacyIntent
                .model_validate(
                    parsed
                )
            )

        result.intent = (
            "find_pharmacy"
        )

        result.radius_km = (
            _clamp_radius(
                result.radius_km
            )
        )

        result.raw_request = (
            cleaned
        )

        return result

    except Exception:
        return _local_fallback(
            cleaned
        )