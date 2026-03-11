from __future__ import annotations

from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
from typing import Optional

from rich.console import Console
from sqlmodel import select

from optra.adapters.base import BaseAdapter
from optra.adapters.notion import NotionAdapter
from optra.adapters.slack import SlackAdapter
from optra.models.db import get_session
from optra.models.work_item import Source, WorkItem

console = Console()

ADAPTER_MAP: dict[str, type[BaseAdapter]] = {
    "slack": SlackAdapter,
    "notion": NotionAdapter,
}


def get_last_collected_at(source: Source) -> Optional[datetime]:
    """Get the most recent collected timestamp for a source."""
    with get_session() as session:
        stmt = (
            select(WorkItem.timestamp)
            .where(WorkItem.source == source)
            .order_by(WorkItem.timestamp.desc())  # type: ignore[union-attr]
            .limit(1)
        )
        result = session.exec(stmt).first()
        return result


def save_items(items: list[WorkItem]) -> int:
    """Save work items to the database, skipping duplicates.

    Returns:
        Number of newly inserted items.
    """
    inserted = 0
    with get_session() as session:
        for item in items:
            existing = session.exec(
                select(WorkItem).where(
                    WorkItem.source == item.source,
                    WorkItem.source_id == item.source_id,
                )
            ).first()
            if existing is None:
                session.add(item)
                inserted += 1
        session.commit()
    return inserted


def collect(source_name: Optional[str] = None, days: int = 7) -> None:
    """Run collection for specified source(s).

    Args:
        source_name: 'slack', 'notion', or None for all.
        days: Number of days to look back for initial collection.
    """
    sources = [source_name] if source_name else list(ADAPTER_MAP.keys())

    for src in sources:
        if src not in ADAPTER_MAP:
            console.print(f"[red]Unknown source: {src}[/red]")
            continue

        console.print(f"[bold blue]Collecting from {src}...[/bold blue]")

        adapter = ADAPTER_MAP[src]()
        source_enum = Source(src)

        # Determine start time: last collected or N days ago
        last_ts = get_last_collected_at(source_enum)
        if last_ts:
            since = last_ts
            console.print(f"  Incremental collection since {since.isoformat()}")
        else:
            since = datetime.now(tz=KST) - timedelta(days=days)
            console.print(f"  Initial collection: last {days} days")

        items = adapter.collect(since=since)
        console.print(f"  Fetched {len(items)} items")

        inserted = save_items(items)
        console.print(f"  [green]Saved {inserted} new items[/green] ({len(items) - inserted} duplicates skipped)")
