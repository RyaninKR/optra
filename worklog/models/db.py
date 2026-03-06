from __future__ import annotations

from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine

from worklog.config import settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)
        SQLModel.metadata.create_all(_engine)
        # Create FTS5 virtual table after main tables
        with _engine.connect() as conn:
            conn.execute(text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS work_items_fts "
                "USING fts5(content, channel_or_space, source_id UNINDEXED)"
            ))
            conn.commit()
    return _engine


def get_session() -> Session:
    return Session(get_engine())
