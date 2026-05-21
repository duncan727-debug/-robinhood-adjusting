#!/usr/bin/env python3
"""One-time OAuth flow: prints consent URL up-front, runs a local server to
catch the redirect, exchanges code for refresh token, writes
config/google_calendar_token.json."""
import json
import os
import pathlib
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

SCOPES = ["https://www.googleapis.com/auth/calendar"]
REPO = pathlib.Path(__file__).resolve().parents[1]
SECRETS = REPO / "config" / ".secrets"
TOKEN_OUT = REPO / "config" / "google_calendar_token.json"


def load_secret(name: str) -> str:
    for line in SECRETS.read_text().splitlines():
        if line.startswith(f"export {name}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"missing {name} in {SECRETS}")


received: dict = {}


class CB(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        qs = urllib.parse.urlparse(self.path).query
        params = dict(urllib.parse.parse_qsl(qs))
        received.update(params)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        body = b"<h2>OAuth complete. You can close this tab.</h2>"
        self.wfile.write(body)

    def log_message(self, *a, **kw):  # noqa: D401
        return


def main() -> None:
    client_id = load_secret("GOOGLE_CALENDAR_CLIENT_ID")
    client_secret = load_secret("GOOGLE_CALENDAR_CLIENT_SECRET")

    port = 8765
    redirect_uri = f"http://localhost:{port}/"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)
    print("AUTH_URL:", auth_url, flush=True)

    server = HTTPServer(("localhost", port), CB)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    # Wait up to 5 min for callback
    import time
    deadline = time.time() + 300
    while time.time() < deadline and "code" not in received and "error" not in received:
        time.sleep(0.5)
    server.shutdown()

    if "error" in received:
        sys.exit(f"oauth error: {received}")
    if "code" not in received:
        sys.exit("timeout waiting for oauth callback")

    code = received["code"]
    print("got code, exchanging for tokens", flush=True)
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    resp.raise_for_status()
    tok = resp.json()
    refresh_token = tok.get("refresh_token")
    if not refresh_token:
        sys.exit(f"no refresh_token in response: {tok}")

    TOKEN_OUT.write_text(
        json.dumps(
            {
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": SCOPES,
            },
            indent=2,
        )
    )
    os.chmod(TOKEN_OUT, 0o600)
    print(f"wrote {TOKEN_OUT}", flush=True)


if __name__ == "__main__":
    main()
