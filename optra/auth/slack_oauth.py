"""Slack OAuth 2.0 V2 flow."""
from __future__ import annotations

import urllib.parse

import httpx

from optra.auth.server import run_oauth_flow
from optra.auth.store import save_token
from optra.config import settings

SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
CALLBACK_PORT = 9274
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

BOT_SCOPES = [
    "channels:history",
    "channels:read",
    "groups:history",
    "groups:read",
    "im:history",
    "im:read",
    "mpim:history",
    "mpim:read",
    "users:read",
]


def start() -> tuple[bool, str]:
    """Run the Slack OAuth flow.

    Returns:
        (success, message)
    """
    client_id = settings.slack_client_id
    client_secret = settings.slack_client_secret

    if not client_id or not client_secret:
        return False, (
            "SLACK_CLIENT_ID and SLACK_CLIENT_SECRET are required.\n"
            "Create a Slack App at https://api.slack.com/apps and add them to .env"
        )

    params = {
        "client_id": client_id,
        "scope": ",".join(BOT_SCOPES),
        "redirect_uri": REDIRECT_URI,
    }
    auth_url = f"{SLACK_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    code, error = run_oauth_flow(auth_url, port=CALLBACK_PORT)

    if error:
        return False, f"Authorization denied: {error}"
    if not code:
        return False, "No authorization code received (timed out after 2 minutes)"

    # Exchange code for access token
    resp = httpx.post(
        SLACK_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    data = resp.json()

    if not data.get("ok"):
        return False, f"Token exchange failed: {data.get('error', 'unknown')}"

    access_token = data.get("access_token", "")
    team_name = data.get("team", {}).get("name", "Unknown")
    bot_user_id = data.get("bot_user_id", "")

    save_token(
        "slack",
        access_token,
        team=team_name,
        bot_user_id=bot_user_id,
    )

    return True, f"Connected to Slack workspace: {team_name}"
