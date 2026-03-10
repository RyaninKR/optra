"""Auth status and management endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from optra.auth.store import get_token, list_connections, remove_token

router = APIRouter(prefix="/api/auth")


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

    # Ensure slack and notion always appear
    for svc in ("slack", "notion"):
        if svc not in result:
            result[svc] = {"connected": False}

    return result


@router.delete("/{service}")
async def disconnect(service: str):
    """Disconnect a service."""
    remove_token(service)
    return {"success": True, "message": f"{service} disconnected"}


@router.get("/slack/connect")
async def slack_connect():
    """Return the Slack OAuth URL for the frontend to open."""
    import urllib.parse

    from optra.auth.slack_oauth import (
        BOT_SCOPES,
        CALLBACK_PORT,
        REDIRECT_URI,
        SLACK_AUTHORIZE_URL,
    )
    from optra.config import settings

    if not settings.slack_client_id:
        return {"error": "SLACK_CLIENT_ID not configured"}

    params = {
        "client_id": settings.slack_client_id,
        "scope": ",".join(BOT_SCOPES),
        "redirect_uri": REDIRECT_URI,
    }
    url = f"{SLACK_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return {"auth_url": url, "callback_port": CALLBACK_PORT}


@router.get("/notion/connect")
async def notion_connect():
    """Return the Notion OAuth URL for the frontend to open."""
    import urllib.parse

    from optra.auth.notion_oauth import (
        CALLBACK_PORT,
        NOTION_AUTHORIZE_URL,
        REDIRECT_URI,
    )
    from optra.config import settings

    if not settings.notion_client_id:
        return {"error": "NOTION_CLIENT_ID not configured"}

    params = {
        "client_id": settings.notion_client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "owner": "user",
    }
    url = f"{NOTION_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return {"auth_url": url, "callback_port": CALLBACK_PORT}
