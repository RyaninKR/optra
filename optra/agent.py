"""Conversational agent powered by Claude with optra tools."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from optra.config import settings

console = Console()

SYSTEM_PROMPT = """\
You are Optra, a personal work history assistant.
You help users collect, search, summarize, and understand their work activities from Slack and Notion.

Behavior rules:
- Always respond in Korean (한국어).
- Be concise, friendly, and proactive.
- On the very first interaction, call check_auth_status to see what's connected.
  - If nothing is connected, naturally guide the user to connect Slack or Notion.
  - If connected but no data collected yet, offer to collect.
  - If data exists, greet and ask how you can help.
- When the user asks about their work, decide which tool to use:
  - Specific date → daily summary
  - A week → weekly summary
  - Keyword search → search
  - Stats/patterns → insights
  - Recent activity → recent items
- After running a tool, summarize the results conversationally. Don't just dump raw data.
- When auth or collect actions succeed, naturally transition to the next step.
- Keep responses SHORT. 2-4 sentences max unless presenting summary/search results.
- Today's date: {today}
"""

TOOLS = [
    {
        "name": "check_auth_status",
        "description": "Check which services (Slack, Notion) are currently connected.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "connect_slack",
        "description": "Start Slack OAuth flow. Opens a browser for the user to authorize.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "connect_notion",
        "description": "Start Notion OAuth flow. Opens a browser for the user to authorize.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "collect_items",
        "description": "Collect work items from connected sources.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source to collect from: 'slack', 'notion', or null for all.",
                },
                "days": {
                    "type": "integer",
                    "description": "Days to look back for initial collection. Default 7.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "generate_summary",
        "description": "Generate a work summary for a specific date or ISO week.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format for daily summary.",
                },
                "week": {
                    "type": "string",
                    "description": "ISO week in YYYY-Www format (e.g. 2026-W10) for weekly summary.",
                },
                "source": {
                    "type": "string",
                    "description": "Optional source filter: 'slack' or 'notion'.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "search_items",
        "description": "Search work items by keyword.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword or phrase."},
                "limit": {"type": "integer", "description": "Max results. Default 10."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_insights",
        "description": "Get activity insights: category breakdown, top collaborators, source stats.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {
                    "type": "string",
                    "description": "Month in YYYY-MM format.",
                },
                "days": {
                    "type": "integer",
                    "description": "Days to look back. Default 30.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_recent_items",
        "description": "Get recently collected work items.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of items. Default 10."},
                "source": {"type": "string", "description": "Optional source filter."},
            },
            "required": [],
        },
    },
    {
        "name": "get_stats",
        "description": "Get collection statistics (total items per source).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "categorize_items",
        "description": "Auto-categorize uncategorized work items using LLM.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


# ── Tool implementations ──────────────────────────────────────


def _run_check_auth_status() -> str:
    from optra.auth.store import list_connections

    connections = list_connections()
    if not connections:
        return json.dumps({"connected": [], "message": "No services connected."})

    result = []
    for service, info in connections.items():
        if info.get("connected"):
            details = {k: v for k, v in info.items() if k != "connected" and v}
            result.append({"service": service, **details})

    if not result:
        return json.dumps({"connected": [], "message": "No services connected."})
    return json.dumps({"connected": result})


def _run_connect_slack() -> str:
    from optra.auth.slack_oauth import start

    console.print("[dim]브라우저에서 Slack 인증을 진행해주세요...[/dim]")
    ok, msg = start()
    return json.dumps({"success": ok, "message": msg})


def _run_connect_notion() -> str:
    from optra.auth.notion_oauth import start

    console.print("[dim]브라우저에서 Notion 인증을 진행해주세요...[/dim]")
    ok, msg = start()
    return json.dumps({"success": ok, "message": msg})


def _run_collect_items(source: str | None = None, days: int = 7) -> str:
    from optra.engine.collector import collect as run_collect, save_items, get_last_collected_at, ADAPTER_MAP
    from optra.models.work_item import Source
    from datetime import timedelta

    sources = [source] if source else list(ADAPTER_MAP.keys())
    total_fetched = 0
    total_inserted = 0

    for src in sources:
        if src not in ADAPTER_MAP:
            continue
        adapter = ADAPTER_MAP[src]()
        source_enum = Source(src)
        last_ts = get_last_collected_at(source_enum)
        since = last_ts if last_ts else datetime.now(tz=timezone.utc) - timedelta(days=days)

        try:
            items = adapter.collect(since=since)
            inserted = save_items(items)
            total_fetched += len(items)
            total_inserted += inserted
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    return json.dumps({
        "success": True,
        "fetched": total_fetched,
        "new_items": total_inserted,
        "duplicates_skipped": total_fetched - total_inserted,
    })


def _run_generate_summary(
    date: str | None = None, week: str | None = None, source: str | None = None,
) -> str:
    from optra.engine.summarizer import daily_summary, weekly_summary

    try:
        if week:
            result = weekly_summary(week, source)
        else:
            d = date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            result = daily_summary(d, source)
        return json.dumps({"success": True, "summary": result})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def _run_search_items(query: str, limit: int = 10) -> str:
    from optra.engine.search import fts_search

    items = fts_search(query, limit=limit)
    results = []
    for item in items:
        results.append({
            "time": item.timestamp.strftime("%Y-%m-%d %H:%M"),
            "source": item.source,
            "channel": item.channel_or_space,
            "content": item.content[:300],
        })
    return json.dumps({"count": len(results), "results": results})


def _run_get_insights(month: str | None = None, days: int = 30) -> str:
    from collections import Counter
    from datetime import timedelta
    from sqlmodel import select
    from optra.models.db import get_session
    from optra.models.work_item import WorkItem

    if month:
        start = datetime.strptime(f"{month}-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    else:
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=days)

    with get_session() as session:
        items = list(session.exec(
            select(WorkItem).where(WorkItem.timestamp >= start, WorkItem.timestamp < end)
        ).all())

    if not items:
        return json.dumps({"total": 0, "message": "No data for this period."})

    cat_counter: Counter[str] = Counter()
    collab_counter: Counter[str] = Counter()
    src_counter: Counter[str] = Counter()

    for item in items:
        cat_counter[item.category or "uncategorized"] += 1
        src_counter[item.source] += 1
        for p in item.participants:
            collab_counter[p] += 1

    return json.dumps({
        "total": len(items),
        "categories": dict(cat_counter.most_common()),
        "top_collaborators": dict(collab_counter.most_common(10)),
        "sources": dict(src_counter.most_common()),
    })


def _run_get_recent_items(limit: int = 10, source: str | None = None) -> str:
    from sqlmodel import select
    from optra.models.db import get_session
    from optra.models.work_item import WorkItem

    with get_session() as session:
        stmt = select(WorkItem).order_by(WorkItem.timestamp.desc()).limit(limit)  # type: ignore
        if source:
            stmt = stmt.where(WorkItem.source == source)
        items = list(session.exec(stmt).all())

    results = []
    for item in items:
        results.append({
            "time": item.timestamp.strftime("%Y-%m-%d %H:%M"),
            "source": item.source,
            "channel": item.channel_or_space,
            "type": item.item_type,
            "content": item.content[:200],
        })
    return json.dumps({"count": len(results), "results": results})


def _run_get_stats() -> str:
    from sqlmodel import select, func
    from optra.models.db import get_session
    from optra.models.work_item import WorkItem

    with get_session() as session:
        results = session.exec(
            select(WorkItem.source, func.count(WorkItem.id)).group_by(WorkItem.source)
        ).all()

    stats = {source: count for source, count in results}
    total = sum(stats.values())
    return json.dumps({"sources": stats, "total": total})


def _run_categorize_items() -> str:
    from optra.engine.summarizer import categorize_uncategorized

    try:
        count = categorize_uncategorized()
        return json.dumps({"success": True, "categorized": count})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


TOOL_HANDLERS: dict[str, Any] = {
    "check_auth_status": lambda **_: _run_check_auth_status(),
    "connect_slack": lambda **_: _run_connect_slack(),
    "connect_notion": lambda **_: _run_connect_notion(),
    "collect_items": lambda **kw: _run_collect_items(kw.get("source"), kw.get("days", 7)),
    "generate_summary": lambda **kw: _run_generate_summary(kw.get("date"), kw.get("week"), kw.get("source")),
    "search_items": lambda **kw: _run_search_items(kw["query"], kw.get("limit", 10)),
    "get_insights": lambda **kw: _run_get_insights(kw.get("month"), kw.get("days", 30)),
    "get_recent_items": lambda **kw: _run_get_recent_items(kw.get("limit", 10), kw.get("source")),
    "get_stats": lambda **_: _run_get_stats(),
    "categorize_items": lambda **_: _run_categorize_items(),
}


# ── Agent loop ─────────────────────────────────────────────────


def _execute_tool(name: str, input_args: dict) -> str:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return handler(**input_args)
    except Exception as e:
        return json.dumps({"error": str(e)})


def start() -> None:
    """Launch the conversational agent."""
    if not settings.anthropic_api_key:
        console.print(Panel(
            "[bold red]ANTHROPIC_API_KEY가 설정되지 않았습니다.[/bold red]\n\n"
            "1. https://console.anthropic.com/ 에서 API 키 발급\n"
            "2. 환경변수 설정: [bold]export ANTHROPIC_API_KEY=sk-ant-...[/bold]\n"
            "   또는 ~/.optra/.env 파일에 추가",
            title="Setup Required",
        ))
        return

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    system = SYSTEM_PROMPT.format(today=today)

    messages: list[dict] = []

    console.print()
    console.print(Panel(
        "[bold]Optra[/bold]  —  업무 히스토리 어시스턴트\n"
        "[dim]자연어로 질문하세요. 종료: Ctrl+C[/dim]",
        border_style="blue",
    ))
    console.print()

    # Kick off with an empty user message to trigger onboarding
    messages.append({"role": "user", "content": "시작"})

    try:
        while True:
            # Call Claude
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system,
                tools=TOOLS,
                messages=messages,
            )

            # Process response
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            # Handle tool use
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in assistant_content:
                    if block.type == "text" and block.text.strip():
                        console.print(Markdown(block.text))
                    elif block.type == "tool_use":
                        result = _execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})
                continue  # Let Claude process tool results

            # Display text response
            for block in assistant_content:
                if block.type == "text" and block.text.strip():
                    console.print()
                    console.print(Markdown(block.text))
                    console.print()

            # Get user input
            try:
                user_input = console.input("[bold blue]>[/bold blue] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Bye![/dim]")
                break

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "종료", "나가기"):
                console.print("[dim]Bye![/dim]")
                break

            messages.append({"role": "user", "content": user_input})

    except KeyboardInterrupt:
        console.print("\n[dim]Bye![/dim]")
