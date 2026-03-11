from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

console = Console()

app = typer.Typer(
    name="optra",
    help="업무 히스토리 AI 어시스턴트",
    invoke_without_command=True,
    add_completion=False,
    no_args_is_help=False,
)

auth_app = typer.Typer(help="서비스 계정 연결/관리")
app.add_typer(auth_app, name="auth")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Optra — 업무 히스토리 AI 어시스턴트.

    인자 없이 실행하면 대화 모드, 질문을 전달하면 원샷 응답.
    """
    if ctx.invoked_subcommand is not None:
        return

    from optra.agent import start

    # Collect non-flag args after the command name as the query
    raw_args = sys.argv[1:]
    # Filter out known subcommands — anything left is the query
    known = {"auth", "serve", "--help"}
    query_parts = [a for a in raw_args if a not in known and not a.startswith("-")]
    query = " ".join(query_parts) if query_parts else None

    start(query=query)


# ── Auth commands ──────────────────────────────────────────────


@auth_app.command("slack")
def auth_slack() -> None:
    """Slack OAuth 연결 (브라우저 열림)."""
    from optra.auth.slack_oauth import start

    console.print("[bold]Slack 연결 중...[/bold]")
    console.print("브라우저에서 인증을 진행해주세요.\n")

    ok, msg = start()
    console.print(f"[green]{msg}[/green]" if ok else f"[red]{msg}[/red]")


@auth_app.command("notion")
def auth_notion() -> None:
    """Notion OAuth 연결 (브라우저 열림)."""
    from optra.auth.notion_oauth import start

    console.print("[bold]Notion 연결 중...[/bold]")
    console.print("브라우저에서 인증을 진행해주세요.\n")

    ok, msg = start()
    console.print(f"[green]{msg}[/green]" if ok else f"[red]{msg}[/red]")


@auth_app.command("status")
def auth_status() -> None:
    """연결 상태 확인."""
    from optra.auth.store import list_connections

    connections = list_connections()
    if not connections:
        console.print("[yellow]연결된 서비스가 없습니다.[/yellow]")
        console.print("  [dim]optra auth slack[/dim]")
        console.print("  [dim]optra auth notion[/dim]")
        return

    table = Table(title="연결 상태")
    table.add_column("서비스", style="cyan")
    table.add_column("상태")
    table.add_column("세부정보", style="dim")

    for service, info in connections.items():
        connected = info.pop("connected", False)
        status_text = "[green]연결됨[/green]" if connected else "[red]미연결[/red]"
        details = ", ".join(f"{k}={v}" for k, v in info.items() if v)
        table.add_row(service, status_text, details)

    console.print(table)


@auth_app.command("logout")
def auth_logout(
    service: str = typer.Argument(help="연결 해제할 서비스 (slack/notion)"),
) -> None:
    """서비스 연결 해제."""
    from optra.auth.store import remove_token

    remove_token(service)
    console.print(f"[green]{service} 연결이 해제되었습니다.[/green]")


# ── Serve command ──────────────────────────────────────────────


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="서버 포트"),
    dev: bool = typer.Option(False, "--dev", help="자동 리로드 활성화"),
) -> None:
    """Optra 웹 서버 시작."""
    import uvicorn

    console.print(f"[bold]Optra 서버 시작: http://localhost:{port}[/bold]")
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=port,
        reload=dev,
    )


if __name__ == "__main__":
    app()
