import os
import re
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


load_dotenv()


MODEL_ID = "gemini-3.5-flash-lite"


# =========================================================
# GEMINI STRUCTURED OUTPUT
# =========================================================

class InterpretedProductDetails(BaseModel):

    product_name: Optional[str] = Field(
        default=None,
        description=(
            "Product or medicine name understood from the transcript."
        ),
    )

    manufacturer: Optional[str] = Field(
        default=None,
        description=(
            "Manufacturer, applicant, or company name understood "
            "from the transcript."
        ),
    )

    nafdac_number: Optional[str] = Field(
        default=None,
        description=(
            "Possible NAFDAC registration number. "
            "Do not invent missing characters."
        ),
    )

    nafdac_source_span: Optional[str] = Field(
        default=None,
        description=(
            "Exact words or characters from the transcript that "
            "support the proposed NAFDAC number. Copy directly "
            "from the transcript. Do not translate."
        ),
    )

    batch_number: Optional[str] = Field(
        default=None,
        description=(
            "Possible batch or lot number. "
            "Do not invent missing characters."
        ),
    )

    batch_source_span: Optional[str] = Field(
        default=None,
        description=(
            "Exact words or characters from the transcript that "
            "support the proposed batch or lot number. Copy "
            "directly from the transcript."
        ),
    )

    expiry_date: Optional[str] = Field(
        default=None,
        description=(
            "Expiry date only if explicitly mentioned."
        ),
    )

    expiry_source_span: Optional[str] = Field(
        default=None,
        description=(
            "Exact words from the transcript referring to the "
            "expiry date. Copy directly from the transcript."
        ),
    )


# =========================================================
# HELPERS
# =========================================================

def _get_client():

    api_key = (
        os.environ.get(
            "GEMINI_API_KEY",
            "",
        )
        .strip()
    )

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(
        api_key=api_key
    )


def _clean(
    value: Optional[str],
) -> Optional[str]:

    if value is None:
        return None

    value = (
        str(
            value
        )
        .strip()
    )

    return (
        value
        or None
    )


def _normalize_identifier(
    value: Optional[str],
) -> str:
    """
    Remove formatting characters while preserving
    the actual underlying letters and digits.

    Examples:

    04-0005 -> 040005
    A4-1409 -> A41409
    """

    if not value:
        return ""

    return (
        re.sub(
            r"[^A-Za-z0-9]",
            "",
            str(
                value
            ),
        )
        .upper()
    )


def _normalize_transcript_for_identifier(
    transcript: str,
) -> str:
    """
    Used only for deterministic identifier checking.

    This deliberately does NOT convert number words
    into digits.

    Therefore:

    'A41409' can support 'A4-1409'

    but:

    'zero four one eight seven six'

    cannot automatically support '04-1876'.

    That is intentional for safety.
    """

    return (
        re.sub(
            r"[^A-Za-z0-9]",
            "",
            transcript,
        )
        .upper()
    )


def _exact_source_span_exists(
    source_span: Optional[str],
    transcript: str,
) -> bool:

    source_span = (
        _clean(
            source_span
        )
    )

    if not source_span:
        return False

    return (
        source_span.casefold()
        in
        transcript.casefold()
    )


def _identifier_is_supported(
    candidate: Optional[str],
    transcript: str,
) -> bool:
    """
    Safety-critical identifiers are accepted only
    when their underlying alphanumeric characters
    are visibly present in the N-ATLAS transcript.

    Formatting may change.

    Characters may not.
    """

    candidate_normalized = (
        _normalize_identifier(
            candidate
        )
    )

    if not candidate_normalized:
        return False


    transcript_normalized = (
        _normalize_transcript_for_identifier(
            transcript
        )
    )


    if not transcript_normalized:
        return False


    return (
        candidate_normalized
        in
        transcript_normalized
    )


def _expiry_is_supported(
    candidate: Optional[str],
    source_span: Optional[str],
    transcript: str,
) -> bool:
    """
    Expiry dates are treated differently from registration
    numbers and batch IDs because ordinary spoken dates may
    legitimately be normalised.

    Gemini must still provide an exact span copied from the
    transcript proving that an expiry date was actually said.
    """

    candidate = (
        _clean(
            candidate
        )
    )

    if not candidate:
        return False


    if not _exact_source_span_exists(
        source_span,
        transcript,
    ):
        return False


    source_span = (
        _clean(
            source_span
        )
        or ""
    )


    # Require some meaningful date-like content.
    #
    # This is intentionally broad enough for multilingual
    # speech while preventing an unsupported expiry value
    # from appearing from nowhere.

    if len(
        source_span
    ) < 3:
        return False


    return True


# =========================================================
# INTERPRETER
# =========================================================

def interpret_transcript(
    transcript: str,
    language: Optional[str] = None,
) -> dict:

    transcript = (
        str(
            transcript
            or ""
        )
        .strip()
    )


    if not transcript:

        return {
            "product_name": None,
            "nafdac_number": None,
            "manufacturer": None,
            "batch_number": None,
            "expiry_date": None,
        }


    language_names = {
        "en": "Nigerian English",
        "yo": "Yorùbá",
        "ha": "Hausa",
        "ig": "Igbo",
    }


    if language in language_names:

        language_instruction = (
            "The user selected "
            f"{language_names[language]}."
        )

    else:

        language_instruction = (
            "The transcript may be Nigerian English, "
            "Yorùbá, Hausa, Igbo, or natural "
            "code-switching between them."
        )


    system_instruction = """
You are the language interpretation layer for Before Use,
a voice-first consumer product-safety application.

Your job is to understand an N-ATLAS transcript and extract
product information.

The transcript may contain:

- Nigerian English
- Yorùbá
- Hausa
- Igbo
- code-switching with English
- brand names
- company names
- spoken numbers
- alphanumeric registration numbers

UNDERSTAND THE ORIGINAL LANGUAGE DIRECTLY.

Do not translate the entire transcript into English first.

Do not output a translation.

PRODUCT NAME AND MANUFACTURER

You may correct obvious phonetic or speech-recognition errors
in ordinary names when the intended name is strongly supported
by the transcript.

Examples:

"panador extra"
may become
"Panadol Extra"

"glassow smith clean"
may become
"GlaxoSmithKline"

"kadifin"
may become
"Cadiphen"

"kadila fámásítíkás"
may become
"Cadila Pharmaceuticals"

But do not use outside databases to fill fields that were not
communicated by the user.

SAFETY-CRITICAL IDENTIFIERS

NAFDAC registration numbers and batch numbers must be treated
much more strictly.

Never guess a digit.

Never guess a letter.

Never insert a missing digit.

Never substitute one digit for another because a known product
usually has a different number.

Never use your knowledge of a product's official registration
number to repair what the user said.

Examples:

A4-0005 must NOT become 04-0005.

A4149 must NOT become A4-1409.

A41409 may be formatted as A4-1409 because the underlying
characters are identical.

If a user speaks a number in Yorùbá, Hausa, Igbo, or English
words but the N-ATLAS transcript is ambiguous, you may describe
a possible candidate internally, but Before Use will perform a
deterministic character check after your response.

Do not pretend an uncertain number is certain.

SOURCE SPANS

For:

- NAFDAC number
- batch number
- expiry date

you must also copy the exact supporting words or characters
from the N-ATLAS transcript into the matching source_span
field.

Do not translate the source span.

Do not rewrite it.

Do not correct it.

Copy it exactly.

If there is no clear supporting span, return null for both the
value and source span.

EXPIRY DATES

An explicitly spoken expiry date may be normalised into a
human-readable form.

Example:

"December twenty twenty seven"

may become:

"December 2027"

But an expiry date must still have a source span that appears
in the transcript.

MISSING OR UNCERTAIN INFORMATION

Return null.

Accuracy is more important than completeness.

It is better for Before Use to ask the user again than to show
a confident but incorrect safety-critical value.
"""


    prompt = f"""
{language_instruction}

Interpret the following exact N-ATLAS transcript.

Remember:

- understand its original language directly
- preserve product-specific names
- do not invent identifiers
- copy exact transcript evidence for safety-critical fields

N-ATLAS TRANSCRIPT:

{transcript}
"""


    client = (
        _get_client()
    )


    response = (
        client.models.generate_content(

            model=MODEL_ID,

            contents=prompt,

            config=types.GenerateContentConfig(

                system_instruction=(
                    system_instruction
                ),

                response_mime_type=(
                    "application/json"
                ),

                response_schema=(
                    InterpretedProductDetails
                ),

                temperature=0,
            ),
        )
    )


    parsed = (
        getattr(
            response,
            "parsed",
            None,
        )
    )


    if isinstance(
        parsed,
        InterpretedProductDetails,
    ):

        details = parsed


    elif parsed:

        details = (
            InterpretedProductDetails
            .model_validate(
                parsed
            )
        )


    else:

        response_text = (
            response.text
            or ""
        ).strip()


        if not response_text:

            raise RuntimeError(
                "Gemini returned an empty interpretation."
            )


        details = (
            InterpretedProductDetails
            .model_validate_json(
                response_text
            )
        )


    # =====================================================
    # NORMAL LANGUAGE FIELDS
    # =====================================================

    product_name = (
        _clean(
            details.product_name
        )
    )


    manufacturer = (
        _clean(
            details.manufacturer
        )
    )


    # =====================================================
    # STRICT NAFDAC NUMBER GUARD
    # =====================================================

    proposed_nafdac = (
        _clean(
            details.nafdac_number
        )
    )


    if _identifier_is_supported(
        proposed_nafdac,
        transcript,
    ):

        nafdac_number = (
            proposed_nafdac
        )

    else:

        nafdac_number = None


    # =====================================================
    # STRICT BATCH NUMBER GUARD
    # =====================================================

    proposed_batch = (
        _clean(
            details.batch_number
        )
    )


    if _identifier_is_supported(
        proposed_batch,
        transcript,
    ):

        batch_number = (
            proposed_batch
        )

    else:

        batch_number = None


    # =====================================================
    # EXPIRY GUARD
    # =====================================================

    proposed_expiry = (
        _clean(
            details.expiry_date
        )
    )


    if _expiry_is_supported(

        proposed_expiry,

        details.expiry_source_span,

        transcript,

    ):

        expiry_date = (
            proposed_expiry
        )

    else:

        expiry_date = None


    return {
        "product_name": product_name,
        "nafdac_number": nafdac_number,
        "manufacturer": manufacturer,
        "batch_number": batch_number,
        "expiry_date": expiry_date,
    }