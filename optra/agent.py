"""Optra — 에이전트 네이티브 CLI (Claude Code 스타일)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
from typing import Any

import anthropic
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from optra.config import settings

console = Console()
err_console = Console(stderr=True)

SYSTEM_PROMPT = """\
You are Optra, a personal work history assistant.
You help users collect, search, summarize, and understand their work activities from Slack and Notion.

Behavior rules:
- Always respond in Korean (한국어).
- Be concise, friendly, and proactive.
- On the very first interaction:
  1. Call get_user_profile to check if user identity is set up.
  2. Call check_auth_status to see what's connected.
  3. If profile has no slack_user_id/notion_user_id but services are connected:
     → Ask the user for their Slack display name or nickname.
     → Use lookup_slack_user to find them, confirm with the user, then save_user_profile.
  4. If nothing is connected, guide to connect first. After connecting, ask for identity.
  5. If profile and connections exist but no data, offer to collect.
  6. If everything is set up, greet and ask how you can help.
- The user profile (slack_user_id, display_name) is critical — it determines whose
  work history to focus on in summaries and searches. Always complete this setup.
- When the user asks about their work, decide which tool to use:
  - Specific date → daily summary
  - A week → weekly summary
  - Keyword search → search
  - Stats/patterns → insights
  - Recent activity → recent items
- After running a tool, summarize the results conversationally. Don't just dump raw data.
- When auth or collect actions succeed, naturally transition to the next step.
- If a connect tool returns error "oauth_not_configured", explain step-by-step:
  1. Create the app (Slack: https://api.slack.com/apps, Notion: https://www.notion.so/profile/integrations)
  2. Copy Client ID and Client Secret
  3. Add to ~/.optra/.env file
  4. Restart optra
  Never say "관리자에게 문의하세요" — the user IS the admin.
- Keep responses SHORT. 2-4 sentences max unless presenting summary/search results.
- Today's date: {today}
{user_context}"""

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
    {
        "name": "get_user_profile",
        "description": "Get the stored user profile (Slack/Notion identity).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "lookup_slack_user",
        "description": "Search Slack workspace members by display name or real name. Returns matching users.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Name or nickname to search for (partial match).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_user_profile",
        "description": "Save the user's identity for tracking their work history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "slack_user_id": {
                    "type": "string",
                    "description": "Slack user ID (e.g. U082Y6J8S3S).",
                },
                "slack_display_name": {
                    "type": "string",
                    "description": "Slack display name.",
                },
                "slack_real_name": {
                    "type": "string",
                    "description": "Slack real name.",
                },
                "notion_user_id": {
                    "type": "string",
                    "description": "Notion user ID.",
                },
                "notion_name": {
                    "type": "string",
                    "description": "Notion display name.",
                },
            },
            "required": [],
        },
    },
]

TOOL_LABELS: dict[str, str] = {
    "check_auth_status": "연결 상태 확인",
    "connect_slack": "Slack 연결",
    "connect_notion": "Notion 연결",
    "collect_items": "데이터 수집",
    "generate_summary": "요약 생성",
    "search_items": "검색",
    "get_insights": "인사이트 분석",
    "get_recent_items": "최근 항목 조회",
    "get_stats": "통계 조회",
    "categorize_items": "카테고리 분류",
    "get_user_profile": "사용자 프로필 조회",
    "lookup_slack_user": "Slack 사용자 검색",
    "save_user_profile": "사용자 프로필 저장",
}


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

    if not settings.slack_client_id or not settings.slack_client_secret:
        return json.dumps({
            "success": False,
            "error": "oauth_not_configured",
            "message": (
                "Slack OAuth 앱이 설정되지 않았습니다. "
                "~/.optra/.env 파일에 SLACK_CLIENT_ID와 SLACK_CLIENT_SECRET을 추가해주세요. "
                "Slack App은 https://api.slack.com/apps 에서 생성할 수 있습니다."
            ),
        })

    console.print("  [dim]브라우저에서 Slack 인증을 진행해주세요...[/dim]")
    ok, msg = start()
    return json.dumps({"success": ok, "message": msg})


def _run_connect_notion() -> str:
    from optra.auth.notion_oauth import start

    if not settings.notion_client_id or not settings.notion_client_secret:
        return json.dumps({
            "success": False,
            "error": "oauth_not_configured",
            "message": (
                "Notion OAuth 앱이 설정되지 않았습니다. "
                "~/.optra/.env 파일에 NOTION_CLIENT_ID와 NOTION_CLIENT_SECRET을 추가해주세요. "
                "Notion Integration은 https://www.notion.so/profile/integrations 에서 생성할 수 있습니다."
            ),
        })

    console.print("  [dim]브라우저에서 Notion 인증을 진행해주세요...[/dim]")
    ok, msg = start()
    return json.dumps({"success": ok, "message": msg})


def _run_collect_items(source: str | None = None, days: int = 7) -> str:
    from datetime import timedelta

    from optra.engine.collector import ADAPTER_MAP, get_last_collected_at, save_items
    from optra.models.work_item import Source

    sources = [source] if source else list(ADAPTER_MAP.keys())
    total_fetched = 0
    total_inserted = 0

    for src in sources:
        if src not in ADAPTER_MAP:
            continue
        adapter = ADAPTER_MAP[src]()
        source_enum = Source(src)
        last_ts = get_last_collected_at(source_enum)
        since = last_ts if last_ts else datetime.now(tz=KST) - timedelta(days=days)

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
            d = date or datetime.now(tz=KST).strftime("%Y-%m-%d")
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
        start_dt = datetime.strptime(f"{month}-01", "%Y-%m-%d").replace(tzinfo=KST)
        if start_dt.month == 12:
            end = start_dt.replace(year=start_dt.year + 1, month=1)
        else:
            end = start_dt.replace(month=start_dt.month + 1)
    else:
        end = datetime.now(tz=KST)
        start_dt = end - timedelta(days=days)

    with get_session() as session:
        items = list(session.exec(
            select(WorkItem).where(WorkItem.timestamp >= start_dt, WorkItem.timestamp < end)
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
    from sqlmodel import func, select

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


def _run_get_user_profile() -> str:
    from optra.profile import get_profile

    profile = get_profile()
    if not profile:
        return json.dumps({"configured": False, "message": "No user profile set up yet."})
    return json.dumps({"configured": True, **profile})


def _run_lookup_slack_user(query: str) -> str:
    from optra.config import get_slack_token

    token = get_slack_token()
    if not token:
        return json.dumps({"error": "Slack not connected. Connect first."})

    from slack_sdk import WebClient

    client = WebClient(token=token)
    query_lower = query.lower()

    matches = []
    cursor = None
    while True:
        resp = client.users_list(limit=200, cursor=cursor)
        for member in resp.get("members", []):
            if member.get("is_bot") or member.get("deleted"):
                continue
            profile = member.get("profile", {})
            display_name = profile.get("display_name", "")
            real_name = profile.get("real_name", "")

            if (
                query_lower in display_name.lower()
                or query_lower in real_name.lower()
            ):
                matches.append({
                    "user_id": member["id"],
                    "display_name": display_name,
                    "real_name": real_name,
                })

        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return json.dumps({"query": query, "count": len(matches), "users": matches[:10]})


def _run_save_user_profile(**kwargs: Any) -> str:
    from optra.profile import save_profile

    save_profile(**kwargs)
    return json.dumps({"success": True, "saved": kwargs})


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
    "get_user_profile": lambda **_: _run_get_user_profile(),
    "lookup_slack_user": lambda **kw: _run_lookup_slack_user(kw["query"]),
    "save_user_profile": lambda **kw: _run_save_user_profile(**kw),
}


# ── Tool execution with display ───────────────────────────────


def _execute_tool(name: str, input_args: dict) -> str:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})

    label = TOOL_LABELS.get(name, name)

    with Live(
        Spinner("dots", text=Text(f" {label}...", style="dim")),
        console=err_console,
        transient=True,
    ):
        try:
            result = handler(**input_args)
        except Exception as e:
            result = json.dumps({"error": str(e)})

    # Show completion
    err_console.print(f"  [green]✓[/green] [dim]{label}[/dim]")
    return result


# ── Streaming output ──────────────────────────────────────────


def _stream_response(
    client: anthropic.Anthropic,
    system: str,
    messages: list[dict],
    max_turns: int = 10,
) -> None:
    """Run Claude tool_use loop with streaming text output."""
    for _ in range(max_turns):
        text_chunks: list[str] = []
        tool_uses: list[dict] = []
        current_tool: dict = {}
        stop_reason = None

        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        current_tool = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input_json": "",
                        }
                    elif event.content_block.type == "text":
                        pass  # Will receive deltas

                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        text = event.delta.text
                        text_chunks.append(text)
                        # Stream text directly to terminal
                        err_console.print(text, end="", highlight=False)
                    elif event.delta.type == "input_json_delta":
                        current_tool["input_json"] += event.delta.partial_json

                elif event.type == "content_block_stop":
                    if current_tool:
                        try:
                            input_args = json.loads(current_tool["input_json"]) if current_tool["input_json"] else {}
                        except json.JSONDecodeError:
                            input_args = {}
                        tool_uses.append({
                            "id": current_tool["id"],
                            "name": current_tool["name"],
                            "input": input_args,
                        })
                        current_tool = {}

                elif event.type == "message_delta":
                    stop_reason = event.delta.stop_reason

        # End the streamed line
        full_text = "".join(text_chunks)
        if full_text.strip():
            err_console.print()  # newline after streamed text

        # Build assistant message for history
        assistant_content = stream.get_final_message().content
        messages.append({"role": "assistant", "content": assistant_content})

        if stop_reason == "tool_use":
            # Execute tools
            tool_results = []
            for tool in tool_uses:
                result = _execute_tool(tool["name"], tool["input"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool["id"],
                    "content": result,
                })
            messages.append({"role": "user", "content": tool_results})
            continue  # Let Claude process tool results

        # Done — end_turn
        break


# ── Slash commands ────────────────────────────────────────────

SLASH_HELP = """\
[bold]슬래시 커맨드[/bold]
  [cyan]/help[/cyan]    이 도움말 표시
  [cyan]/status[/cyan]  연결 상태 확인
  [cyan]/clear[/cyan]   대화 기록 초기화
  [cyan]/quit[/cyan]    종료
"""


def _handle_slash(cmd: str, messages: list[dict]) -> bool:
    """Handle slash commands. Returns True if handled."""
    cmd = cmd.strip().lower()

    if cmd in ("/help", "/도움"):
        err_console.print(SLASH_HELP)
        return True

    if cmd in ("/status", "/상태"):
        from optra.auth.store import list_connections

        connections = list_connections()
        connected = [s for s, info in connections.items() if info.get("connected")]
        if connected:
            err_console.print(f"  [green]연결됨:[/green] {', '.join(connected)}")
        else:
            err_console.print("  [yellow]연결된 서비스 없음[/yellow]")
        return True

    if cmd in ("/clear", "/초기화"):
        messages.clear()
        err_console.print("  [dim]대화 기록이 초기화되었습니다.[/dim]")
        return True

    if cmd in ("/quit", "/exit", "/종료"):
        raise SystemExit(0)

    return False


# ── Entry point ───────────────────────────────────────────────


def _print_header() -> None:
    """Display the startup header."""
    from optra.auth.store import list_connections
    from optra.profile import get_profile

    connections = list_connections()
    connected = [s for s, info in connections.items() if info.get("connected")]

    status_parts = []
    for svc in ("slack", "notion"):
        if svc in connected:
            status_parts.append(f"[green]●[/green] {svc.title()}")
        else:
            status_parts.append(f"[dim]○ {svc.title()}[/dim]")

    status_line = "  ".join(status_parts)

    profile = get_profile()
    user_name = profile.get("slack_display_name") or profile.get("slack_real_name") or profile.get("notion_name")

    err_console.print()
    err_console.print(f"  [bold]Optra[/bold] [dim]— 업무 히스토리 어시스턴트[/dim]")
    if user_name:
        err_console.print(f"  [dim]사용자:[/dim] {user_name}  {status_line}")
    else:
        err_console.print(f"  {status_line}")
    err_console.print(f"  [dim]/help 도움말  ·  Ctrl+C 종료[/dim]")
    err_console.print()


def start(query: str | None = None) -> None:
    """Launch the conversational agent.

    Args:
        query: If provided, run single-shot mode (answer and exit).
    """
    if not settings.anthropic_api_key:
        err_console.print(Panel(
            "[bold red]ANTHROPIC_API_KEY가 설정되지 않았습니다.[/bold red]\n\n"
            "1. https://console.anthropic.com/ 에서 API 키 발급\n"
            "2. 환경변수 설정: [bold]export ANTHROPIC_API_KEY=sk-ant-...[/bold]\n"
            "   또는 ~/.optra/.env 파일에 추가",
            title="설정 필요",
            border_style="red",
        ))
        sys.exit(1)

    from optra.profile import get_profile

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    today = datetime.now(tz=KST).strftime("%Y-%m-%d")

    profile = get_profile()
    if profile.get("slack_user_id"):
        user_context = (
            f"- Current user: {profile.get('slack_display_name') or profile.get('slack_real_name', 'unknown')} "
            f"(Slack ID: {profile['slack_user_id']}). "
            "Focus summaries and searches on this user's activities."
        )
    else:
        user_context = ""

    system = SYSTEM_PROMPT.format(today=today, user_context=user_context)
    messages: list[dict] = []

    # ── Single-shot mode ──
    if query:
        messages.append({"role": "user", "content": query})
        try:
            _stream_response(client, system, messages)
        except KeyboardInterrupt:
            err_console.print()
        return

    # ── Interactive mode ──
    _print_header()

    # Kick off onboarding
    messages.append({"role": "user", "content": "시작"})
    try:
        _stream_response(client, system, messages)
    except KeyboardInterrupt:
        err_console.print()

    while True:
        err_console.print()
        try:
            user_input = console.input("[bold orange3]>[/bold orange3] ").strip()
        except (EOFError, KeyboardInterrupt):
            err_console.print("\n  [dim]종료합니다.[/dim]")
            break

        if not user_input:
            continue

        # Slash commands
        if user_input.startswith("/"):
            if _handle_slash(user_input, messages):
                continue

        messages.append({"role": "user", "content": user_input})

        err_console.print()
        try:
            _stream_response(client, system, messages)
        except KeyboardInterrupt:
            err_console.print("\n  [dim]생성 중단[/dim]")
            continue
        except anthropic.APIError as e:
            err_console.print(f"\n  [red]API 오류: {e}[/red]")
            continue
