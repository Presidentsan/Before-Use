from typing import Dict, List


LANGUAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "label": "Nigerian English",
        "short_label": "English",
        "locale": "en-NG",
    },
    "yo": {
        "label": "Yorùbá",
        "short_label": "Yorùbá",
        "locale": "yo-NG",
    },
    "ha": {
        "label": "Hausa",
        "short_label": "Hausa",
        "locale": "ha-NG",
    },
    "ig": {
        "label": "Igbo",
        "short_label": "Igbo",
        "locale": "ig-NG",
    },
}


LANGUAGE_ALIASES = {
    "en": "en",
    "english": "en",
    "nigerian english": "en",
    "en-ng": "en",
    "en-us": "en",
    "en-gb": "en",

    "yo": "yo",
    "yoruba": "yo",
    "yorùbá": "yo",
    "yo-ng": "yo",

    "ha": "ha",
    "hausa": "ha",
    "ha-ng": "ha",

    "ig": "ig",
    "igbo": "ig",
    "ig-ng": "ig",
}


def normalize_language(
    language: str,
) -> str:
    value = (
        str(
            language
            or "en"
        )
        .strip()
        .lower()
        .replace(
            "_",
            "-",
        )
    )

    if value in LANGUAGES:
        return value

    return (
        LANGUAGE_ALIASES.get(
            value,
            "en",
        )
    )


def language_options() -> List[str]:
    return list(
        LANGUAGES.keys()
    )


def language_label(
    language: str,
) -> str:
    code = normalize_language(
        language
    )

    return LANGUAGES[
        code
    ][
        "label"
    ]


def language_short_label(
    language: str,
) -> str:
    code = normalize_language(
        language
    )

    return LANGUAGES[
        code
    ][
        "short_label"
    ]


def language_locale(
    language: str,
) -> str:
    code = normalize_language(
        language
    )

    return LANGUAGES[
        code
    ][
        "locale"
    ]