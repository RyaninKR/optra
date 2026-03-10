"""In-memory conversation state management."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
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


def delete_conversation(conv_id: str) -> bool:
    return _conversations.pop(conv_id, None) is not None


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


def get_display_messages(conv_id: str) -> list[dict] | None:
    """Return messages in a frontend-friendly format.

    Transforms Claude API message format into simple {role, content, tools} objects.
    Filters out tool_result user messages (internal to the tool loop).
    """
    conv = _conversations.get(conv_id)
    if conv is None:
        return None

    result: list[dict] = []
    for msg in conv.messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "user":
            # Skip tool_result messages (list of dicts with type=tool_result)
            if isinstance(content, list):
                continue
            result.append({"role": "user", "content": content})

        elif role == "assistant":
            # content is a list of ContentBlock objects from Claude API
            if isinstance(content, list):
                text_parts: list[str] = []
                tools: list[dict] = []
                for block in content:
                    if hasattr(block, "type"):
                        if block.type == "text" and block.text.strip():
                            text_parts.append(block.text)
                        elif block.type == "tool_use":
                            tools.append({
                                "tool": block.name,
                                "status": "done",
                            })
                entry: dict = {
                    "role": "assistant",
                    "content": "".join(text_parts),
                }
                if tools:
                    entry["tools"] = tools
                result.append(entry)
            elif isinstance(content, str):
                result.append({"role": "assistant", "content": content})

    return result


def update_title(conv_id: str, title: str) -> None:
    conv = _conversations.get(conv_id)
    if conv:
        conv.title = title
