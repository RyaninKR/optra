"""Notion OAuth flow."""
from __future__ import annotations

import base64
import urllib.parse

import httpx

from worklog.auth.server import run_oauth_flow
from worklog.auth.store import save_token
from worklog.config import settings

NOTION_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
CALLBACK_PORT = 9274
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"


def start() -> tuple[bool, str]:
    """Run the Notion OAuth flow.

    Returns:
        (success, message)
    """
    client_id = settings.notion_client_id
    client_secret = settings.notion_client_secret

    if not client_id or not client_secret:
        return False, (
            "NOTION_CLIENT_ID and NOTION_CLIENT_SECRET are required.\n"
            "Create a Public Integration at https://www.notion.so/profile/integrations\n"
            "and add them to .env"
        )

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "owner": "user",
    }
    auth_url = f"{NOTION_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    code, error = run_oauth_flow(auth_url, port=CALLBACK_PORT)

    if error:
        return False, f"Authorization denied: {error}"
    if not code:
        return False, "No authorization code received (timed out after 2 minutes)"

    # Notion uses Basic Auth (client_id:client_secret) for token exchange
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    resp = httpx.post(
        NOTION_TOKEN_URL,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        },
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    data = resp.json()

    if "error" in data:
        return False, f"Token exchange failed: {data.get('error', 'unknown')}"

    access_token = data.get("access_token", "")
    workspace_name = data.get("workspace_name", "Unknown")
    workspace_id = data.get("workspace_id", "")

    save_token(
        "notion",
        access_token,
        workspace=workspace_name,
        workspace_id=workspace_id,
    )

    return True, f"Connected to Notion workspace: {workspace_name}"
