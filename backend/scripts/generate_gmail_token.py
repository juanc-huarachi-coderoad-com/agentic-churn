"""One-time, interactive Gmail OAuth consent flow — run by a human, not automation.

Prerequisites (specs/028-real-gmail-connector/quickstart.md):
    A Google Cloud project with the Gmail API enabled, an OAuth consent screen
    (scope https://www.googleapis.com/auth/gmail.readonly, your own account added
    as a test user), and a "Desktop app" OAuth 2.0 Client ID — GMAIL_CLIENT_ID /
    GMAIL_CLIENT_SECRET already set in backend/.env.

This opens a real browser window for you to approve read-only access to the
connected mailbox, then prints the resulting refresh token. Add it to backend/.env
as GMAIL_REFRESH_TOKEN — GmailCollector (backend/app/ingestion/adapters/
gmail_collector.py) uses it, together with the client id/secret, to refresh its
own access token automatically on every real run; no human needs to repeat this
flow again unless access is revoked.

Run:
    uv run python scripts/generate_gmail_token.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from app.config import settings  # noqa: E402

_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def run() -> None:
    if not settings.gmail_client_id or not settings.gmail_client_secret:
        print(
            "GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET are not set in backend/.env — "
            "create them first (specs/028-real-gmail-connector/quickstart.md Prerequisites)."
        )
        return

    client_config = {
        "installed": {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, _SCOPES)
    # A real, interactive browser-based consent flow — cannot be run headlessly or
    # by an agent; this is the one step in this feature a human must perform.
    credentials = flow.run_local_server(port=0)

    print("\nAuthorization complete. Add this line to backend/.env:\n")
    print(f"GMAIL_REFRESH_TOKEN={credentials.refresh_token}\n")


if __name__ == "__main__":
    run()
