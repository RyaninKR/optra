"""User profile storage (~/.optra/profile.json)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

OPTRA_DIR = Path.home() / ".optra"
PROFILE_FILE = OPTRA_DIR / "profile.json"


def get_profile() -> dict[str, Any]:
    """Load user profile."""
    if PROFILE_FILE.exists():
        return json.loads(PROFILE_FILE.read_text())
    return {}


def save_profile(**kwargs: Any) -> None:
    """Update user profile fields (merge, not overwrite)."""
    data = get_profile()
    data.update({k: v for k, v in kwargs.items() if v is not None})
    OPTRA_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_slack_identity() -> Optional[dict[str, str]]:
    """Return Slack identity if configured."""
    profile = get_profile()
    uid = profile.get("slack_user_id")
    if uid:
        return {
            "user_id": uid,
            "display_name": profile.get("slack_display_name", ""),
            "real_name": profile.get("slack_real_name", ""),
        }
    return None


def get_notion_identity() -> Optional[dict[str, str]]:
    """Return Notion identity if configured."""
    profile = get_profile()
    uid = profile.get("notion_user_id")
    if uid:
        return {
            "user_id": uid,
            "name": profile.get("notion_name", ""),
        }
    return None
