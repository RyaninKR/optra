from __future__ import annotations

from sqlmodel import SQLModel, Session, create_engine

from worklog.config import settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{settings.db_path}", echo=False)
        SQLModel.metadata.create_all(_engine)
    return _engine


def get_session() -> Session:
    return Session(get_engine())
