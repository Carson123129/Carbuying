"""
Simple waitlist storage for FindingMyCar.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

WAITLIST_PATH = Path(__file__).parent / "data" / "waitlist.json"


def _load_waitlist() -> List[Dict[str, str]]:
    if not WAITLIST_PATH.exists():
        return []
    try:
        with open(WAITLIST_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _save_waitlist(entries: List[Dict[str, str]]) -> None:
    WAITLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(WAITLIST_PATH, "w", encoding="utf-8") as file:
        json.dump(entries, file, indent=2)


def add_waitlist_email(email: str, source: str = "landing") -> bool:
    normalized = email.strip().lower()
    if not normalized:
        return False

    entries = _load_waitlist()
    if any(entry.get("email") == normalized for entry in entries):
        return False

    entries.append(
        {
            "email": normalized,
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _save_waitlist(entries)
    return True


