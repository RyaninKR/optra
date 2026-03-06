"""Local credential storage (~/.worklog/credentials.json)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

WORKLOG_DIR = Path.home() / ".worklog"
CREDENTIALS_FILE = WORKLOG_DIR / "credentials.json"


def _load() -> dict[str, Any]:
    if CREDENTIALS_FILE.exists():
        return json.loads(CREDENTIALS_FILE.read_text())
    return {}


def _save(data: dict[str, Any]) -> None:
    WORKLOG_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))
    CREDENTIALS_FILE.chmod(0o600)


def get_token(service: str) -> Optional[str]:
    return _load().get(service, {}).get("access_token")


def save_token(service: str, access_token: str, **extra: Any) -> None:
    data = _load()
    data[service] = {"access_token": access_token, **extra}
    _save(data)


def remove_token(service: str) -> None:
    data = _load()
    data.pop(service, None)
    _save(data)


def list_connections() -> dict[str, dict[str, Any]]:
    """Return all stored services with metadata (excluding raw tokens)."""
    data = _load()
    result = {}
    for service, info in data.items():
        safe = {k: v for k, v in info.items() if k != "access_token"}
        safe["connected"] = bool(info.get("access_token"))
        result[service] = safe
    return result
