"""Auth status and management endpoints."""
from __future__ import annotations

import base64
import urllib.parse

import httpx
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from optra.auth.store import get_token, list_connections, remove_token, save_token
from optra.config import settings

router = APIRouter(prefix="/api/auth")

WEB_CALLBACK_PORT = 8000
WEB_REDIRECT_URI = f"http://localhost:{WEB_CALLBACK_PORT}/api/auth/callback"

# ── Status / Disconnect ──────────────────────────────────────────────


@router.get("/status")
async def auth_status():
    """Get connection status for all services."""
    connections = list_connections()
    result = {}
    for service, info in connections.items():
        result[service] = {
            "connected": info.get("connected", False),
            **{k: v for k, v in info.items() if k != "connected" and v},
        }

    for svc in ("slack", "notion"):
        if svc not in result:
            result[svc] = {"connected": False}

    return result


@router.delete("/{service}")
async def disconnect(service: str):
    """Disconnect a service."""
    remove_token(service)
    return {"success": True, "message": f"{service} disconnected"}


# ── OAuth Connect (return URL for frontend popup) ────────────────────


@router.get("/slack/connect")
async def slack_connect():
    """Return the Slack OAuth URL for the frontend to open."""
    if not settings.slack_client_id:
        return {"error": "SLACK_CLIENT_ID가 설정되지 않았습니다."}

    from optra.auth.slack_oauth import BOT_SCOPES, SLACK_AUTHORIZE_URL

    params = {
        "client_id": settings.slack_client_id,
        "scope": ",".join(BOT_SCOPES),
        "redirect_uri": WEB_REDIRECT_URI,
        "state": "slack",
    }
    url = f"{SLACK_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return {"auth_url": url}


@router.get("/notion/connect")
async def notion_connect():
    """Return the Notion OAuth URL for the frontend to open."""
    if not settings.notion_client_id:
        return {"error": "NOTION_CLIENT_ID가 설정되지 않았습니다."}

    from optra.auth.notion_oauth import NOTION_AUTHORIZE_URL

    params = {
        "client_id": settings.notion_client_id,
        "redirect_uri": WEB_REDIRECT_URI,
        "response_type": "code",
        "owner": "user",
        "state": "notion",
    }
    url = f"{NOTION_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return {"auth_url": url}


# ── OAuth Callback (receives redirect from Slack/Notion) ─────────────

_CALLBACK_SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>Optra</title></head>
<body style="font-family:system-ui;text-align:center;padding:60px;background:#1a1a1a;color:#e8e8e8">
  <h2 style="color:#c4704b">{service} 연결 완료</h2>
  <p>{detail}</p>
  <p style="color:#888;font-size:13px">이 탭을 닫고 Optra로 돌아가세요.</p>
  <script>setTimeout(()=>window.close(),2000)</script>
</body></html>
"""

_CALLBACK_ERROR_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>Optra</title></head>
<body style="font-family:system-ui;text-align:center;padding:60px;background:#1a1a1a;color:#e8e8e8">
  <h2 style="color:#ef4444">연결 실패</h2>
  <p>{message}</p>
  <p style="color:#888;font-size:13px">Optra로 돌아가서 다시 시도해주세요.</p>
</body></html>
"""


@router.get("/callback")
async def oauth_callback(code: str | None = None, error: str | None = None, state: str | None = None):
    """Handle OAuth redirect from Slack/Notion."""
    if error:
        return HTMLResponse(_CALLBACK_ERROR_HTML.format(message=error), status_code=400)

    if not code or not state:
        return HTMLResponse(
            _CALLBACK_ERROR_HTML.format(message="인증 코드가 누락되었습니다."),
            status_code=400,
        )

    if state == "slack":
        return await _exchange_slack(code)
    elif state == "notion":
        return await _exchange_notion(code)
    else:
        return HTMLResponse(
            _CALLBACK_ERROR_HTML.format(message=f"알 수 없는 서비스: {state}"),
            status_code=400,
        )


async def _exchange_slack(code: str) -> HTMLResponse:
    """Exchange Slack auth code for token and save."""
    from optra.auth.slack_oauth import SLACK_TOKEN_URL

    if not settings.slack_client_id or not settings.slack_client_secret:
        return HTMLResponse(
            _CALLBACK_ERROR_HTML.format(message="Slack OAuth 설정이 없습니다."),
            status_code=500,
        )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SLACK_TOKEN_URL,
            data={
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "code": code,
                "redirect_uri": WEB_REDIRECT_URI,
            },
        )

    data = resp.json()
    if not data.get("ok"):
        return HTMLResponse(
            _CALLBACK_ERROR_HTML.format(message=f"토큰 교환 실패: {data.get('error', 'unknown')}"),
            status_code=400,
        )

    access_token = data.get("access_token", "")
    team_name = data.get("team", {}).get("name", "Unknown")
    bot_user_id = data.get("bot_user_id", "")

    save_token("slack", access_token, team=team_name, bot_user_id=bot_user_id)

    return HTMLResponse(
        _CALLBACK_SUCCESS_HTML.format(service="Slack", detail=f"워크스페이스: {team_name}"),
    )


async def _exchange_notion(code: str) -> HTMLResponse:
    """Exchange Notion auth code for token and save."""
    from optra.auth.notion_oauth import NOTION_TOKEN_URL

    if not settings.notion_client_id or not settings.notion_client_secret:
        return HTMLResponse(
            _CALLBACK_ERROR_HTML.format(message="Notion OAuth 설정이 없습니다."),
            status_code=500,
        )

    credentials = base64.b64encode(
        f"{settings.notion_client_id}:{settings.notion_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            NOTION_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": WEB_REDIRECT_URI,
            },
        )

    data = resp.json()
    if "error" in data:
        return HTMLResponse(
            _CALLBACK_ERROR_HTML.format(message=f"토큰 교환 실패: {data.get('error', 'unknown')}"),
            status_code=400,
        )

    access_token = data.get("access_token", "")
    workspace_name = data.get("workspace_name", "Unknown")
    workspace_id = data.get("workspace_id", "")

    save_token("notion", access_token, workspace=workspace_name, workspace_id=workspace_id)

    return HTMLResponse(
        _CALLBACK_SUCCESS_HTML.format(service="Notion", detail=f"워크스페이스: {workspace_name}"),
    )
