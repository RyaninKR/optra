from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlmodel import func, select

from worklog.models.db import get_session
from worklog.models.work_item import WorkItem

app = typer.Typer(
    name="worklog",
    help="Personal work history aggregator",
    no_args_is_help=True,
)
auth_app = typer.Typer(help="Connect and manage service accounts")
app.add_typer(auth_app, name="auth")

console = Console()


# ── Auth commands ──────────────────────────────────────────────


@auth_app.command("slack")
def auth_slack() -> None:
    """Connect to Slack via OAuth (opens browser)."""
    from worklog.auth.slack_oauth import start

    console.print("[bold]Connecting to Slack...[/bold]")
    console.print("A browser window will open — please authorize the app.\n")

    ok, msg = start()
    console.print(f"[green]{msg}[/green]" if ok else f"[red]{msg}[/red]")


@auth_app.command("notion")
def auth_notion() -> None:
    """Connect to Notion via OAuth (opens browser)."""
    from worklog.auth.notion_oauth import start

    console.print("[bold]Connecting to Notion...[/bold]")
    console.print("A browser window will open — please authorize the app.\n")

    ok, msg = start()
    console.print(f"[green]{msg}[/green]" if ok else f"[red]{msg}[/red]")


@auth_app.command("status")
def auth_status() -> None:
    """Show which services are connected."""
    from worklog.auth.store import list_connections

    connections = list_connections()
    if not connections:
        console.print("[yellow]No services connected yet.[/yellow]")
        console.print("  Run: worklog auth slack")
        console.print("  Run: worklog auth notion")
        return

    table = Table(title="Connected Services")
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    for service, info in connections.items():
        connected = info.pop("connected", False)
        status = "[green]Connected[/green]" if connected else "[red]Not connected[/red]"
        details = ", ".join(f"{k}={v}" for k, v in info.items() if v)
        table.add_row(service, status, details)

    console.print(table)


@auth_app.command("logout")
def auth_logout(
    service: str = typer.Argument(help="Service to disconnect (slack/notion)"),
) -> None:
    """Disconnect a service."""
    from worklog.auth.store import remove_token

    remove_token(service)
    console.print(f"[green]Disconnected from {service}.[/green]")


# ── Collect command ────────────────────────────────────────────


@app.command()
def collect(
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Source to collect from (slack/notion/all)"
    ),
    days: int = typer.Option(7, "--days", "-d", help="Days to look back for initial collection"),
) -> None:
    """Collect work items from collaboration tools."""
    from worklog.engine.collector import collect as run_collect

    src = None if source == "all" else source
    run_collect(source_name=src, days=days)


# ── Summary & Insight commands ─────────────────────────────────


@app.command()
def summary(
    date: Optional[str] = typer.Option(None, "--date", help="Daily summary (YYYY-MM-DD)"),
    week: Optional[str] = typer.Option(None, "--week", help="Weekly summary (YYYY-Www, e.g. 2026-W10)"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source"),
) -> None:
    """Generate a daily or weekly work summary using LLM."""
    from worklog.engine.summarizer import daily_summary, weekly_summary

    if not date and not week:
        # Default to today
        from datetime import datetime, timezone

        date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    if date:
        console.print(f"[bold]Generating daily summary for {date}...[/bold]\n")
        result = daily_summary(date, source)
    else:
        console.print(f"[bold]Generating weekly summary for {week}...[/bold]\n")
        result = weekly_summary(week, source)  # type: ignore[arg-type]

    console.print(result)


@app.command()
def categorize() -> None:
    """Auto-categorize uncategorized work items using LLM."""
    from worklog.engine.summarizer import categorize_uncategorized

    console.print("[bold]Categorizing work items...[/bold]")
    count = categorize_uncategorized()
    console.print(f"[green]Categorized {count} items.[/green]")


@app.command()
def insight(
    month: Optional[str] = typer.Option(None, "--month", help="Month to analyze (YYYY-MM)"),
    days: int = typer.Option(30, "--days", "-d", help="Days to look back (if --month not set)"),
) -> None:
    """Show activity insights (category breakdown, top collaborators)."""
    from collections import Counter
    from datetime import datetime, timedelta, timezone

    if month:
        start = datetime.strptime(f"{month}-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
        # Next month
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        period_label = month
    else:
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=days)
        period_label = f"last {days} days"

    with get_session() as session:
        stmt = (
            select(WorkItem)
            .where(WorkItem.timestamp >= start, WorkItem.timestamp < end)
        )
        items = list(session.exec(stmt).all())

    if not items:
        console.print(f"[yellow]{period_label}: no data.[/yellow]")
        return

    # Category breakdown
    cat_counter: Counter[str] = Counter()
    for item in items:
        cat_counter[item.category or "uncategorized"] += 1

    table_cat = Table(title=f"Category Breakdown ({period_label})")
    table_cat.add_column("Category", style="cyan")
    table_cat.add_column("Count", justify="right")
    table_cat.add_column("Ratio", justify="right", style="dim")

    total = len(items)
    for cat, count in cat_counter.most_common():
        pct = f"{count / total * 100:.1f}%"
        table_cat.add_row(cat, str(count), pct)

    table_cat.add_section()
    table_cat.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]", "")
    console.print(table_cat)
    console.print()

    # Top collaborators
    collab_counter: Counter[str] = Counter()
    for item in items:
        for p in item.participants:
            collab_counter[p] += 1

    if collab_counter:
        table_collab = Table(title=f"Top Collaborators ({period_label})")
        table_collab.add_column("Person", style="magenta")
        table_collab.add_column("Interactions", justify="right")

        for person, count in collab_counter.most_common(10):
            table_collab.add_row(person, str(count))

        console.print(table_collab)
        console.print()

    # Source breakdown
    src_counter: Counter[str] = Counter()
    for item in items:
        src_counter[item.source] += 1

    table_src = Table(title=f"Source Breakdown ({period_label})")
    table_src.add_column("Source", style="cyan")
    table_src.add_column("Count", justify="right")

    for src, count in src_counter.most_common():
        table_src.add_row(src, str(count))

    console.print(table_src)


# ── Search command ─────────────────────────────────────────────


@app.command()
def search(
    query: str = typer.Argument(help="Search query (e.g. '배포 관련 논의')"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
) -> None:
    """Search work items by keyword."""
    from worklog.engine.search import fts_search

    items = fts_search(query, limit=limit)

    if not items:
        console.print(f"[yellow]'{query}'에 대한 결과가 없습니다.[/yellow]")
        return

    table = Table(title=f"Search: '{query}' ({len(items)} results)")
    table.add_column("Time", style="dim", width=19)
    table.add_column("Source", style="cyan", width=7)
    table.add_column("Channel", style="magenta", width=20)
    table.add_column("Content", max_width=60, no_wrap=True)

    for item in items:
        ts = item.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        content = item.content[:60].replace("\n", " ")
        table.add_row(ts, item.source, item.channel_or_space, content)

    console.print(table)


# ── Query commands ─────────────────────────────────────────────


@app.command()
def stats() -> None:
    """Show collection statistics."""
    with get_session() as session:
        stmt = select(WorkItem.source, func.count(WorkItem.id)).group_by(WorkItem.source)
        results = session.exec(stmt).all()

        if not results:
            console.print("[yellow]No items collected yet. Run 'worklog collect' first.[/yellow]")
            return

        table = Table(title="WorkLog Statistics")
        table.add_column("Source", style="cyan")
        table.add_column("Items", justify="right", style="green")

        total = 0
        for source, count in results:
            table.add_row(source, str(count))
            total += count

        table.add_section()
        table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")
        console.print(table)


@app.command()
def recent(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of items to show"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source"),
) -> None:
    """Show recently collected work items."""
    with get_session() as session:
        stmt = select(WorkItem).order_by(WorkItem.timestamp.desc()).limit(limit)  # type: ignore[union-attr]
        if source:
            stmt = stmt.where(WorkItem.source == source)

        items = session.exec(stmt).all()

        if not items:
            console.print("[yellow]No items found.[/yellow]")
            return

        table = Table(title=f"Recent {len(items)} Items")
        table.add_column("Time", style="dim", width=19)
        table.add_column("Source", style="cyan", width=7)
        table.add_column("Channel", style="magenta", width=20)
        table.add_column("Type", width=8)
        table.add_column("Content", max_width=60, no_wrap=True)

        for item in items:
            ts = item.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            content = item.content[:60].replace("\n", " ")
            table.add_row(ts, item.source, item.channel_or_space, item.item_type, content)

        console.print(table)


if __name__ == "__main__":
    app()
