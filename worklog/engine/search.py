"""Full-text and semantic search for work items."""
from __future__ import annotations

from sqlalchemy import text
from sqlmodel import select

from worklog.models.db import get_session
from worklog.models.work_item import WorkItem


def sync_fts_index() -> int:
    """Populate FTS index with any items not yet indexed. Returns count added."""
    with get_session() as session:
        # Get IDs already in FTS
        existing = session.exec(
            text("SELECT source_id FROM work_items_fts")
        ).all()
        existing_ids = {row[0] for row in existing}

        # Get all work items
        items = session.exec(select(WorkItem)).all()
        added = 0
        for item in items:
            if item.source_id not in existing_ids:
                session.exec(
                    text(
                        "INSERT INTO work_items_fts(content, channel_or_space, source_id) "
                        "VALUES(:content, :channel, :source_id)"
                    ),
                    params={
                        "content": item.content,
                        "channel": item.channel_or_space,
                        "source_id": item.source_id,
                    },
                )
                added += 1
        session.commit()
        return added


def fts_search(query: str, limit: int = 20) -> list[WorkItem]:
    """Search work items using SQLite FTS5.

    Args:
        query: Search query string.
        limit: Max results to return.

    Returns:
        List of matching WorkItem objects, ranked by relevance.
    """
    # Sync index first
    sync_fts_index()

    with get_session() as session:
        # FTS5 match query → get source_ids
        fts_results = session.exec(
            text(
                "SELECT source_id, rank FROM work_items_fts "
                "WHERE work_items_fts MATCH :query "
                "ORDER BY rank LIMIT :limit"
            ),
            params={"query": query, "limit": limit},
        ).all()

        if not fts_results:
            return []

        source_ids = [row[0] for row in fts_results]

        # Fetch full WorkItem objects
        items = session.exec(
            select(WorkItem).where(WorkItem.source_id.in_(source_ids))  # type: ignore[union-attr]
        ).all()

        # Preserve FTS rank order
        id_order = {sid: i for i, sid in enumerate(source_ids)}
        items.sort(key=lambda it: id_order.get(it.source_id, 999))

        return list(items)
