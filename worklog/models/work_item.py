from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, Column, JSON


class Source(str, Enum):
    slack = "slack"
    notion = "notion"


class ItemType(str, Enum):
    message = "message"
    thread = "thread"
    page = "page"
    task = "task"
    meeting_note = "meeting_note"


class WorkItem(SQLModel, table=True):
    __tablename__ = "work_items"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    source: Source
    source_id: str = Field(index=True)
    item_type: ItemType
    content: str
    summary: Optional[str] = None
    category: Optional[str] = None
    channel_or_space: str = ""
    participants: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    timestamp: datetime
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    metadata_: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))
