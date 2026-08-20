"""`GoogleDriveTokenStore` — a file-backed OAuth token store for the Google
Drive connection (specs/019-meeting-audio-ingestion, research.md Decision 6),
mirroring `FileKeyStore`'s shape (`key_store.py`): a thin, swappable adapter
behind no port at all (nothing above `AudioCollector`/`google_drive_client.py`
— both adapter-layer code — ever touches it, so no application-layer port is
needed, constitution P8).

The stored file holds a persisted refresh token, written once by
`scripts/authorize_google_drive.py`'s one-time, operator-run OAuth grant.
This class only ever refreshes the access token from that persisted refresh
token — it never performs an interactive OAuth flow itself (FR-001's "no
manual re-authentication between cycles").
"""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class GoogleDriveTokenStoreError(Exception):
    """No valid token file exists yet — the one-time
    `scripts/authorize_google_drive.py` grant hasn't been run for this
    deployment. Distinct from a token that exists but has expired/been
    revoked (`GoogleDriveAuthenticationError`, `google_drive_client.py`) —
    that's a real, ongoing operational failure `AudioCollector.fetch()`
    surfaces honestly on every cycle; this is a one-time deployment-setup
    gap, raised only until the grant script has been run."""


class GoogleDriveTokenStore:
    def __init__(self, token_path: str, client_id: str, client_secret: str) -> None:
        self._path = Path(token_path)
        self._client_id = client_id
        self._client_secret = client_secret

    def credentials(self) -> Credentials:
        """Loads the persisted refresh token and returns valid credentials —
        refreshing the access token in-process via the stored refresh token
        alone if it's expired. Never prompts interactively."""
        if not self._path.is_file():
            raise GoogleDriveTokenStoreError(
                f"No Google Drive token file at {self._path} — run "
                "scripts/authorize_google_drive.py once for this deployment."
            )
        data = json.loads(self._path.read_text())
        creds = Credentials(  # type: ignore[no-untyped-call]
            token=data.get("token"),
            refresh_token=data["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=SCOPES,
        )
        if not creds.valid:
            creds.refresh(Request())  # type: ignore[no-untyped-call]
            self._persist(creds)
        return creds

    def _persist(self, creds: Credentials) -> None:
        self._path.write_text(
            json.dumps({"token": creds.token, "refresh_token": creds.refresh_token})
        )
