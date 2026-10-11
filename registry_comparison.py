"""Conservative field comparison for regulatory records.

A registration-number match is distinct from physical product authentication.
Brand-family consistency must never be presented as an exact variant match.
"""
import re
from difflib import SequenceMatcher

LEGAL_WORDS = {"nigeria", "nigerian", "plc", "ltd", "limited", "inc", "incorporated", "company", "co", "llc", "the"}
GENERIC_PRODUCT_WORDS = {"toothpaste", "paste", "product", "cosmetic", "cosmetics", "medicine", "tablet", "tablets", "cream", "soap", "gel", "formula", "formulation", "brand"}


def words(value):
    text = str(value or "").lower()
    text = re.sub(r"(?<=\w)[-\s]+(?=\w)", " ", text)
    return re.findall(r"[a-z0-9]+", text)


def _brand_key(value):
    # Collapse typography differences, e.g. Close-Up / Closeup.
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _strip_registration_suffix(value):
    """Remove only a terminal parenthesized NAFDAC-style number, not variant words."""
    return re.sub(
        r"\s*\(\s*[0-9]{2}\s*[-/]\s*[0-9A-Z]{3,8}\s*\)\s*$",
        "",
        str(value or ""),
        flags=re.IGNORECASE,
    ).strip()


def compare_field(*, field, user_value, official_value, threshold):
    if not user_value:
        return dict(field=field, user_value=user_value, official_value=official_value,
                    state="not_provided", similarity=None)
    if not official_value:
        return dict(field=field, user_value=user_value, official_value=None,
                    state="not_available_officially", similarity=None)

    label = field.lower()
    # NAPAMS sometimes appends the registration number to a product title.
    # Remove that presentation suffix for name comparison only.
    comparison_official = (
        _strip_registration_suffix(official_value)
        if "product" in label or "brand" in label
        else official_value
    )
    user = " ".join(words(user_value))
    official = " ".join(words(comparison_official))
    score = SequenceMatcher(None, user, official).ratio()
    state = "mismatch"
    note = None

    if user == official or _brand_key(user_value) == _brand_key(comparison_official):
        state = "match"
    elif "manufacturer" in label or "applicant" in label:
        # A shortened legal name may identify the same entity. Only ignore
        # common legal/geographic suffixes; never erase substantive words.
        u = [w for w in words(user_value) if w not in LEGAL_WORDS]
        o = [w for w in words(official_value) if w not in LEGAL_WORDS]
        if u and o and u == o:
            state = "match"
            note = "Company name matches after removing legal/geographic suffixes."
        elif score >= threshold:
            state = "needs_verification"
            note = "Names are similar, but the legal entity could not be confirmed automatically."
    elif "product" in label or "brand" in label:
        # A user may say 'Close-Up Toothpaste' when NAPAMS lists the
        # narrower 'Closeup Triple Fresh Formula'. Do not claim an exact
        # variant match from the shared brand alone.
        u = [w for w in words(user_value) if w not in GENERIC_PRODUCT_WORDS]
        o = [w for w in words(comparison_official) if w not in GENERIC_PRODUCT_WORDS]
        ucore = "".join(u)
        ocore = "".join(o)
        if ucore and ocore and ucore == ocore:
            state = "match"
        elif ucore and ocore and (ocore.startswith(ucore) or ucore.startswith(ocore)):
            state = "needs_verification"
            note = "Brand is consistent, but the exact product variant is not confirmed."
        elif score >= threshold:
            state = "needs_verification"
            note = "Descriptions are similar, but the exact variant is not confirmed."
    elif score >= threshold:
        state = "match"

    result = dict(field=field, user_value=user_value, official_value=official_value,
                  state=state, similarity=round(score, 3))
    if note:
        result["note"] = note
    return result
