"""Local HTTP server for capturing OAuth callbacks."""
from __future__ import annotations

import http.server
import urllib.parse
import webbrowser
from typing import Optional


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Captures the authorization code from the OAuth redirect."""

    auth_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            self._respond(
                200,
                "<h2>Authorization successful!</h2>"
                "<p>You can close this tab and return to the terminal.</p>",
            )
        elif "error" in params:
            _CallbackHandler.error = params.get("error", ["unknown"])[0]
            self._respond(
                400,
                f"<h2>Authorization failed</h2><p>{_CallbackHandler.error}</p>",
            )
        else:
            self._respond(404, "<h2>Not found</h2>")

    def _respond(self, status: int, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"<html><body style='font-family:system-ui;text-align:center;padding:60px'>{body}</body></html>"
        self.wfile.write(html.encode())

    def log_message(self, format: str, *args: object) -> None:
        pass  # Suppress request logs


def run_oauth_flow(
    auth_url: str,
    port: int = 9274,
    timeout: int = 120,
) -> tuple[Optional[str], Optional[str]]:
    """Open browser for OAuth and wait for the callback.

    Args:
        auth_url: The full authorization URL to open.
        port: Local port for the callback server.
        timeout: Seconds to wait before giving up.

    Returns:
        (auth_code, error) — one of them will be None.
    """
    _CallbackHandler.auth_code = None
    _CallbackHandler.error = None

    server = http.server.HTTPServer(("localhost", port), _CallbackHandler)
    server.timeout = timeout

    # Open browser AFTER the server is bound (port is ready)
    webbrowser.open(auth_url)

    # Block until one request is handled or timeout
    server.handle_request()
    server.server_close()

    return _CallbackHandler.auth_code, _CallbackHandler.error
