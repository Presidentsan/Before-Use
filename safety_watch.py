import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
WATCH_FILE = DATA_DIR / "safety_watch.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _watch_fingerprint(product: Dict[str, Any]) -> str:
    parts = [
        _clean(product.get("product_name")) or "",
        _clean(product.get("nafdac_number")) or "",
        _clean(product.get("manufacturer")) or "",
        _clean(product.get("batch_number")) or "",
        _clean(product.get("expiry_date")) or "",
    ]

    normalized = "|".join(
        part.upper()
        for part in parts
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:16]


def _ensure_store() -> None:
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not WATCH_FILE.exists():
        WATCH_FILE.write_text(
            "[]",
            encoding="utf-8",
        )


def load_watchlist() -> List[Dict[str, Any]]:
    _ensure_store()

    try:
        raw = WATCH_FILE.read_text(
            encoding="utf-8"
        )

        data = json.loads(
            raw
        )

        if isinstance(
            data,
            list,
        ):
            return data

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return []


def _save_watchlist(
    items: List[Dict[str, Any]],
) -> None:
    _ensure_store()

    temp_file = (
        WATCH_FILE.with_suffix(
            ".tmp"
        )
    )

    temp_file.write_text(
        json.dumps(
            items,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temp_file.replace(
        WATCH_FILE
    )


def is_watched(
    product: Dict[str, Any],
) -> bool:

    watch_id = (
        _watch_fingerprint(
            product
        )
    )

    return any(
        item.get("id")
        == watch_id
        for item
        in load_watchlist()
    )


def add_to_watchlist(
    product: Dict[str, Any],
    evidence_result: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:

    items = (
        load_watchlist()
    )

    watch_id = (
        _watch_fingerprint(
            product
        )
    )

    now = (
        _utc_now_iso()
    )

    cleaned_product = {
        "product_name": _clean(
            product.get(
                "product_name"
            )
        ),

        "nafdac_number": _clean(
            product.get(
                "nafdac_number"
            )
        ),

        "manufacturer": _clean(
            product.get(
                "manufacturer"
            )
        ),

        "batch_number": _clean(
            product.get(
                "batch_number"
            )
        ),

        "expiry_date": _clean(
            product.get(
                "expiry_date"
            )
        ),
    }

    existing = next(
        (
            item
            for item in items
            if item.get("id")
            == watch_id
        ),
        None,
    )

    if existing:

        existing[
            "product"
        ] = cleaned_product

        if (
            evidence_result
            is not None
        ):

            existing[
                "last_result"
            ] = evidence_result

            existing[
                "last_checked_at"
            ] = now

        _save_watchlist(
            items
        )

        return existing

    record = {
        "id": watch_id,
        "product": cleaned_product,
        "watched_at": now,
        "last_checked_at": (
            now
            if evidence_result
            is not None
            else None
        ),
        "last_result": (
            evidence_result
        ),
    }

    items.insert(
        0,
        record,
    )

    _save_watchlist(
        items
    )

    return record


def update_watch_result(
    watch_id: str,
    evidence_result: Dict[
        str,
        Any,
    ],
) -> Optional[
    Dict[str, Any]
]:

    items = (
        load_watchlist()
    )

    for item in items:

        if (
            item.get("id")
            == watch_id
        ):

            item[
                "last_result"
            ] = evidence_result

            item[
                "last_checked_at"
            ] = _utc_now_iso()

            _save_watchlist(
                items
            )

            return item

    return None


def remove_from_watchlist(
    watch_id: str,
) -> bool:

    items = (
        load_watchlist()
    )

    filtered = [
        item
        for item in items
        if (
            item.get("id")
            != watch_id
        )
    ]

    if (
        len(filtered)
        ==
        len(items)
    ):
        return False

    _save_watchlist(
        filtered
    )

    return True