"""In-memory conversation state management."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Conversation:
    id: str
    title: str
    messages: list[dict]
    created_at: datetime


_conversations: dict[str, Conversation] = {}


def create_conversation() -> Conversation:
    conv = Conversation(
        id=str(uuid.uuid4()),
        title="새 대화",
        messages=[],
        created_at=datetime.now(tz=timezone.utc),
    )
    _conversations[conv.id] = conv
    return conv


def get_conversation(conv_id: str) -> Conversation | None:
    return _conversations.get(conv_id)


def list_conversations() -> list[dict]:
    convs = sorted(_conversations.values(), key=lambda c: c.created_at, reverse=True)
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "message_count": len([m for m in c.messages if m.get("role") == "user"]),
        }
        for c in convs
    ]


def update_title(conv_id: str, title: str) -> None:
    conv = _conversations.get(conv_id)
    if conv:
        conv.title = title
