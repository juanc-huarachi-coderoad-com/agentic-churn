"""`GoogleDriveClient` — lists meeting-series folders and their recordings,
and downloads recording bytes, via the Google Drive API
(specs/019-meeting-audio-ingestion, FR-001/FR-015). One folder per meeting
series (research.md Decision 1's resolved clarification) — a folder's name
*is* the series_id it maps to, matched exactly against the same string
`meeting_series_consent`/`structured_payload` already use elsewhere.

Deliberately does no consent filtering itself (P3 — collectors don't judge):
every folder is returned as a candidate, whatever its name. `AudioCollector`
checks each one's name against `MeetingSeriesConsentRepositoryPort.
is_active()` — a folder whose name matches no real series simply never has
an active consent row either, so it's skipped by that same check, not a
second "known series" lookup this class would otherwise need to duplicate
(research.md Decision 11, corrected during implementation to reuse Decision
3's existing gate rather than adding a parallel one).
"""

import io
import logging
from dataclasses import dataclass
from typing import Any

from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from app.ingestion.adapters.google_drive_token_store import GoogleDriveTokenStore

logger = logging.getLogger(__name__)

_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class GoogleDriveAuthenticationError(Exception):
    """The stored Drive authorization is no longer valid (an expired or
    revoked token, or any other auth-shaped failure from the API) — a
    whole-connection failure `RunCollectorUseCase.execute()`'s try/except
    (research.md Decision 5) records as an honest, visible coverage gap
    (FR-012), distinct from a single recording's own download/transcription
    failure (FR-013, handled per-item inside `AudioCollector.fetch()`)."""


@dataclass(frozen=True)
class DriveRecording:
    file_id: str
    name: str
    modified_time: str
    series_id: str


class GoogleDriveClient:
    def __init__(self, token_store: GoogleDriveTokenStore, root_folder_id: str) -> None:
        self._token_store = token_store
        self._root_folder_id = root_folder_id

    def _service(self) -> Any:  # googleapiclient's Resource has no real stub type
        try:
            credentials = self._token_store.credentials()
        except RefreshError as exc:
            raise GoogleDriveAuthenticationError(
                f"Google Drive authorization is no longer valid: {exc}"
            ) from exc
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    def list_recordings(self) -> list[DriveRecording]:
        """Every recording in every series-folder under the deployment's
        configured root folder — one entry per file, `series_id` set to its
        containing folder's name (FR-015)."""
        try:
            service = self._service()
            folders = (
                service.files()
                .list(
                    q=(
                        f"'{self._root_folder_id}' in parents and "
                        f"mimeType = '{_FOLDER_MIME_TYPE}' and trashed = false"
                    ),
                    fields="files(id, name)",
                )
                .execute()
            )
            recordings: list[DriveRecording] = []
            for folder in folders.get("files", []):
                series_id = folder["name"]
                files = (
                    service.files()
                    .list(
                        q=f"'{folder['id']}' in parents and trashed = false",
                        fields="files(id, name, modifiedTime)",
                    )
                    .execute()
                )
                recordings.extend(
                    DriveRecording(
                        file_id=f["id"],
                        name=f["name"],
                        modified_time=f["modifiedTime"],
                        series_id=series_id,
                    )
                    for f in files.get("files", [])
                )
            return recordings
        except RefreshError as exc:
            raise GoogleDriveAuthenticationError(
                f"Google Drive authorization is no longer valid: {exc}"
            ) from exc
        except HttpError as exc:
            if exc.resp.status in (401, 403):
                raise GoogleDriveAuthenticationError(
                    f"Google Drive authorization is no longer valid: {exc}"
                ) from exc
            raise

    def download(self, file_id: str) -> bytes:
        service = self._service()
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()
