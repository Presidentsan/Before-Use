import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from supabase import Client, create_client


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

SUPABASE_URL = (
    os.getenv(
        "SUPABASE_URL"
    )
    or ""
).strip()

SUPABASE_SERVICE_ROLE_KEY = (
    os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY"
    )
    or ""
).strip()


# =========================================================
# CLIENT
# =========================================================

_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL:
        raise RuntimeError(
            "SUPABASE_URL is missing from .env"
        )

    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is missing from .env"
        )

    _supabase_client = create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY,
    )

    return _supabase_client


# =========================================================
# HELPERS
# =========================================================

def _now_iso() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )


def _clean(
    value: Any,
) -> Optional[str]:

    if value is None:
        return None

    value = str(
        value
    ).strip()

    return value or None


def _make_test_id() -> str:
    return (
        "BU-T-"
        + uuid.uuid4().hex[:10].upper()
    )


def _make_participant_code() -> str:
    return (
        "BU-P-"
        + uuid.uuid4().hex[:8].upper()
    )


# =========================================================
# CONNECTION TEST
# =========================================================

def test_connection() -> Dict[str, Any]:
    """
    Confirms that:
    - Supabase credentials are present
    - the backend can connect
    - validation tables are reachable
    """

    client = get_supabase()

    result = (
        client.table(
            "validation_participants"
        )
        .select(
            "id",
            count="exact",
        )
        .limit(1)
        .execute()
    )

    return {
        "ok": True,
        "count": result.count,
    }


# =========================================================
# PARTICIPANTS
# =========================================================

def create_participant(
    *,
    consent_given: bool,
    preferred_language: Optional[str] = None,
    age_band: Optional[str] = None,
    validator_type: str = "external_user",
) -> Dict[str, Any]:

    client = get_supabase()

    participant_code = (
        _make_participant_code()
    )

    existing = (
        client.table(
            "validation_participants"
        )
        .select(
            "participant_sequence_number"
        )
        .order(
            "participant_sequence_number",
            desc=True,
        )
        .limit(1)
        .execute()
    )

    highest_number = 0

    if existing.data:

        current = (
            existing.data[0]
            .get(
                "participant_sequence_number"
            )
        )

        if current is not None:
            highest_number = int(
                current
            )

    next_number = (
        highest_number + 1
    )

    payload = {
        "participant_code": (
            participant_code
        ),
        "participant_sequence_number": (
            next_number
        ),
        "validator_type": (
            validator_type
        ),
        "consent_given": (
            bool(
                consent_given
            )
        ),
        "preferred_language": (
            _clean(
                preferred_language
            )
        ),
        "age_band": (
            _clean(
                age_band
            )
        ),
    }

    response = (
        client.table(
            "validation_participants"
        )
        .insert(
            payload
        )
        .execute()
    )

    if not response.data:

        raise RuntimeError(
            "Supabase did not return the "
            "created participant."
        )

    return response.data[0]


# =========================================================
# START SESSION
# =========================================================

def start_validation_session(
    *,
    participant_id: Optional[str],
    language: Optional[str],
    input_method: Optional[str],
    product_type: Optional[str],
    voice_replies_enabled: bool,
    app_version: str = "naic-2026-validation-v1",
    validation_environment: str = "real_user_test",
) -> Dict[str, Any]:

    client = get_supabase()

    payload = {
        "participant_id": (
            participant_id
        ),
        "test_id": (
            _make_test_id()
        ),
        "language": (
            _clean(
                language
            )
        ),
        "input_method": (
            _clean(
                input_method
            )
        ),
        "product_type": (
            _clean(
                product_type
            )
        ),
        "started_at": (
            _now_iso()
        ),
        "voice_replies_enabled": (
            bool(
                voice_replies_enabled
            )
        ),
        "app_version": (
            _clean(
                app_version
            )
        ),
        "validation_environment": (
            _clean(
                validation_environment
            )
            or
            "real_user_test"
        ),
    }

    response = (
        client.table(
            "validation_sessions"
        )
        .insert(
            payload
        )
        .execute()
    )

    if not response.data:

        raise RuntimeError(
            "Supabase did not return the "
            "created validation session."
        )

    return response.data[0]


# =========================================================
# SAVE VALIDATION CHECK
# =========================================================

def save_validation_check(
    *,
    session_id: str,
    product_state: Dict[str, Any],
    evidence_result: Dict[str, Any],
    asr_success: Optional[bool],
    extraction_success: Optional[bool],
    corrections_needed: Optional[bool],
    correction_count: int = 0,
    interpreter_used: Optional[str] = None,
) -> Dict[str, Any]:

    client = get_supabase()

    product_state = (
        product_state
        or {}
    )

    evidence_result = (
        evidence_result
        or {}
    )

    sources = (
        evidence_result.get(
            "sources"
        )
        or {}
    )

    greenbook = (
        sources.get(
            "greenbook"
        )
        or {}
    )

    historical = (
        sources.get(
            "historical_nafdac"
        )
        or {}
    )

    nafdac_alerts = (
        sources.get(
            "nafdac_alerts"
        )
        or {}
    )

    who_alerts = (
        sources.get(
            "who_alerts"
        )
        or {}
    )

    registration_result = (
        evidence_result.get(
            "registration_result"
        )
        or {}
    )

    registry_used = (
        evidence_result.get(
            "registry_used"
        )
        or
        registration_result.get(
            "registry_used"
        )
    )

    overall_code = (
        evidence_result.get(
            "code"
        )
    )

    greenbook_record_found = bool(
        greenbook.get(
            "records"
        )
    )

    historical_record_found = bool(
        historical.get(
            "records"
        )
    )

    nafdac_alert_found = bool(
        nafdac_alerts.get(
            "records"
        )
    )

    who_alert_found = bool(
        who_alerts.get(
            "records"
        )
    )

    napams_record_found = (
        "NAPAMS"
        in str(
            registry_used
            or ""
        ).upper()
        and bool(
            evidence_result.get(
                "official_record"
            )
            or
            registration_result.get(
                "official_record"
            )
        )
    )

    source_incomplete = (
        overall_code
        in {
            "source_incomplete",
            "source_unavailable",
            "broader_registry_check_inconclusive",
        }
    )

    payload = {
        "session_id": (
            session_id
        ),

        "product_name": (
            _clean(
                product_state.get(
                    "product_name"
                )
            )
        ),

        "nafdac_number": (
            _clean(
                product_state.get(
                    "nafdac_number"
                )
            )
        ),

        "manufacturer": (
            _clean(
                product_state.get(
                    "manufacturer"
                )
            )
        ),

        "batch_number": (
            _clean(
                product_state.get(
                    "batch_number"
                )
            )
        ),

        "expiry_date": (
            _clean(
                product_state.get(
                    "expiry_date"
                )
            )
        ),

        "asr_success": (
            asr_success
        ),

        "extraction_success": (
            extraction_success
        ),

        "corrections_needed": (
            corrections_needed
        ),

        "correction_count": (
            int(
                correction_count
                or 0
            )
        ),

        "interpreter_used": (
            _clean(
                interpreter_used
            )
        ),

        "evidence_outcome": (
            _clean(
                evidence_result.get(
                    "headline"
                )
            )
        ),

        "overall_code": (
            _clean(
                overall_code
            )
        ),

        "registry_used": (
            _clean(
                registry_used
            )
        ),

        "greenbook_record_found": (
            greenbook_record_found
        ),

        "napams_record_found": (
            napams_record_found
        ),

        "historical_record_found": (
            historical_record_found
        ),

        "nafdac_alert_found": (
            nafdac_alert_found
        ),

        "who_alert_found": (
            who_alert_found
        ),

        "source_incomplete": (
            source_incomplete
        ),
    }

    response = (
        client.table(
            "validation_checks"
        )
        .insert(
            payload
        )
        .execute()
    )

    if not response.data:

        raise RuntimeError(
            "Supabase did not return "
            "the saved validation check."
        )

    return response.data[0]


# =========================================================
# COMPLETE SESSION
# =========================================================

def complete_validation_session(
    *,
    session_id: str,
    task_completed: bool,
    duration_seconds: Optional[int] = None,
    user_feedback: Optional[str] = None,
) -> Dict[str, Any]:

    client = get_supabase()

    payload = {
        "completed_at": (
            _now_iso()
        ),
        "task_completed": (
            bool(
                task_completed
            )
        ),
        "duration_seconds": (
            int(
                duration_seconds
            )
            if duration_seconds
            is not None
            else None
        ),
        "user_feedback": (
            _clean(
                user_feedback
            )
        ),
    }

    response = (
        client.table(
            "validation_sessions"
        )
        .update(
            payload
        )
        .eq(
            "id",
            session_id,
        )
        .execute()
    )

    if not response.data:

        raise RuntimeError(
            "Supabase did not return the "
            "completed validation session."
        )

    return response.data[0]


# =========================================================
# SAVE FEEDBACK
# =========================================================

def save_validation_feedback(
    *,
    session_id: str,
    easy_to_use: Optional[int] = None,
    understood_result: Optional[int] = None,
    trusted_explanation: Optional[int] = None,
    would_use_again: Optional[bool] = None,
    comments: Optional[str] = None,
) -> Dict[str, Any]:

    client = get_supabase()

    payload = {
        "session_id": (
            session_id
        ),
        "easy_to_use": (
            easy_to_use
        ),
        "understood_result": (
            understood_result
        ),
        "trusted_explanation": (
            trusted_explanation
        ),
        "would_use_again": (
            would_use_again
        ),
        "comments": (
            _clean(
                comments
            )
        ),
    }

    response = (
        client.table(
            "validation_feedback"
        )
        .insert(
            payload
        )
        .execute()
    )

    if not response.data:

        raise RuntimeError(
            "Supabase did not return "
            "the saved feedback."
        )

    return response.data[0]


# =========================================================
# VALIDATION SUMMARY
# =========================================================

def get_validation_summary() -> Dict[str, Any]:
    """
    Useful later for the validation report.

    Only external_user sessions count toward the genuine
    real-user validation total.
    """

    client = get_supabase()

    participants = (
        client.table(
            "validation_participants"
        )
        .select(
            "id,validator_type"
        )
        .execute()
    )

    external_participant_ids = {
        row["id"]

        for row in (
            participants.data
            or []
        )

        if (
            row.get(
                "validator_type"
            )
            ==
            "external_user"
        )
    }

    sessions = (
        client.table(
            "validation_sessions"
        )
        .select(
            "id,participant_id,task_completed"
        )
        .execute()
    )

    external_sessions = [

        row

        for row in (
            sessions.data
            or []
        )

        if (
            row.get(
                "participant_id"
            )
            in
            external_participant_ids
        )
    ]

    completed_external_sessions = [

        row

        for row in external_sessions

        if (
            row.get(
                "task_completed"
            )
            is True
        )
    ]

    return {

        "external_participants": (
            len(
                external_participant_ids
            )
        ),

        "external_interactions": (
            len(
                external_sessions
            )
        ),

        "completed_external_interactions": (
            len(
                completed_external_sessions
            )
        ),
    }