"""LLM-based summarization and categorization of work items."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import anthropic
from rich.console import Console
from sqlmodel import select

from worklog.config import settings
from worklog.models.db import get_session
from worklog.models.work_item import WorkItem

console = Console()

CATEGORIES = [
    "dev",        # coding, debugging, code review
    "meeting",    # discussions, standups, syncs
    "review",     # PR review, document review
    "ops",        # deployment, infra, monitoring
    "planning",   # roadmap, sprint planning, estimation
    "docs",       # documentation, wiki
    "comms",      # general communication, announcements
    "other",
]

DAILY_SUMMARY_PROMPT = """\
You are a personal work assistant. Given the following work activity log from {date}, \
create a concise daily summary in Korean.

Format:
## {date} 업무 요약

### 주요 활동
- (bullet points of key activities)

### 세부 내역
- (grouped by category or project)

Rules:
- Be concise but capture all meaningful work
- Group related activities together
- Skip trivial messages (greetings, reactions, etc.)
- Write in Korean

--- Activity Log ---
{items}
"""

WEEKLY_SUMMARY_PROMPT = """\
You are a personal work assistant. Given the following work activity logs from {start} to {end}, \
create a structured weekly summary in Korean.

Format:
## {start} ~ {end} 주간 요약

### 주요 성과
- (top accomplishments)

### 진행 중
- (ongoing work)

### 블로커 / 이슈
- (any blockers or issues mentioned)

### 카테고리별 활동량
- (rough breakdown)

Rules:
- Focus on outcomes, not individual messages
- Identify patterns and themes
- Write in Korean

--- Activity Log ---
{items}
"""

CATEGORIZE_PROMPT = """\
Categorize each work item into exactly one category. \
Respond with ONLY a JSON array of category strings, in the same order as the input items.

Categories: {categories}

Items:
{items}

Response format: ["dev", "meeting", "comms", ...]
"""


def _get_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is required in .env for summarization")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _format_items(items: list[WorkItem]) -> str:
    lines = []
    for item in items:
        ts = item.timestamp.strftime("%H:%M")
        src = item.source
        ch = item.channel_or_space
        content = item.content[:300].replace("\n", " ")
        lines.append(f"[{ts}] ({src}/{ch}) {content}")
    return "\n".join(lines)


def _query_items(
    start: datetime,
    end: datetime,
    source: Optional[str] = None,
) -> list[WorkItem]:
    with get_session() as session:
        stmt = (
            select(WorkItem)
            .where(WorkItem.timestamp >= start, WorkItem.timestamp < end)
            .order_by(WorkItem.timestamp.asc())  # type: ignore[union-attr]
        )
        if source:
            stmt = stmt.where(WorkItem.source == source)
        return list(session.exec(stmt).all())


def daily_summary(date_str: str, source: Optional[str] = None) -> str:
    """Generate a daily summary for the given date (YYYY-MM-DD)."""
    date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = date + timedelta(days=1)

    items = _query_items(date, next_day, source)
    if not items:
        return f"{date_str}: 수집된 활동이 없습니다."

    client = _get_client()
    prompt = DAILY_SUMMARY_PROMPT.format(
        date=date_str,
        items=_format_items(items),
    )

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def weekly_summary(week_str: str, source: Optional[str] = None) -> str:
    """Generate a weekly summary for the given ISO week (YYYY-Www)."""
    year, week = week_str.split("-W")
    start = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w").replace(tzinfo=timezone.utc)
    end = start + timedelta(days=7)

    items = _query_items(start, end, source)
    if not items:
        return f"{week_str}: 수집된 활동이 없습니다."

    client = _get_client()
    prompt = WEEKLY_SUMMARY_PROMPT.format(
        start=start.strftime("%Y-%m-%d"),
        end=(end - timedelta(days=1)).strftime("%Y-%m-%d"),
        items=_format_items(items),
    )

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def categorize_items(items: list[WorkItem], batch_size: int = 50) -> list[str]:
    """Auto-categorize work items using LLM. Returns list of category strings."""
    import json

    if not items:
        return []

    client = _get_client()
    all_categories: list[str] = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        numbered = "\n".join(
            f"{j+1}. [{it.source}/{it.channel_or_space}] {it.content[:200]}"
            for j, it in enumerate(batch)
        )
        prompt = CATEGORIZE_PROMPT.format(
            categories=", ".join(CATEGORIES),
            items=numbered,
        )

        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()

        try:
            cats = json.loads(text)
            all_categories.extend(cats)
        except json.JSONDecodeError:
            all_categories.extend(["other"] * len(batch))

    return all_categories


def categorize_uncategorized() -> int:
    """Find and categorize all items without a category. Returns count updated."""
    with get_session() as session:
        stmt = select(WorkItem).where(WorkItem.category.is_(None))  # type: ignore[union-attr]
        items = list(session.exec(stmt).all())

        if not items:
            return 0

        categories = categorize_items(items)

        updated = 0
        for item, cat in zip(items, categories):
            if cat in CATEGORIES:
                item.category = cat
            else:
                item.category = "other"
            session.add(item)
            updated += 1

        session.commit()
        return updated
