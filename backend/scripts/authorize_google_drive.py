"""One-time, operator-run OAuth grant for the meeting-audio Google Drive
connection (specs/019-meeting-audio-ingestion, research.md Decision 6).
Never invoked by the running application — run once per deployment, before
the first scheduled or manual audio collection cycle:

    uv run python scripts/authorize_google_drive.py

Opens a browser for the Google OAuth consent screen (an installed-app flow),
then writes the resulting refresh token to `settings.google_drive_token_path`.
The running app (`GoogleDriveTokenStore`) only ever refreshes the access
token from that file afterward — it never performs this interactive flow
itself (FR-001's "no manual re-authentication between cycles").

Requires `GOOGLE_DRIVE_CLIENT_ID`/`GOOGLE_DRIVE_CLIENT_SECRET` already set
(the deployment's own OAuth app registration, `architecture/03-technology-
stack.md`'s "own set of OAuth app registrations... per deployment" note) —
this script does not create that registration, only completes the consent
grant against it.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from app.config import settings  # noqa: E402
from app.ingestion.adapters.google_drive_token_store import SCOPES  # noqa: E402


def main() -> None:
    if not settings.google_drive_client_id or not settings.google_drive_client_secret:
        raise SystemExit(
            "GOOGLE_DRIVE_CLIENT_ID / GOOGLE_DRIVE_CLIENT_SECRET must be set before "
            "running this one-time grant — see this deployment's .env file."
        )
    client_config = {
        "installed": {
            "client_id": settings.google_drive_client_id,
            "client_secret": settings.google_drive_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    token_path = Path(settings.google_drive_token_path)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(
        json.dumps({"token": creds.token, "refresh_token": creds.refresh_token})
    )
    print(f"Wrote refresh token to {token_path}")


if __name__ == "__main__":
    main()
