"""`LocalStorageClient` — lists meeting-series folders and their recordings,
and reads recording bytes, from a local filesystem directory
(specs/019-meeting-audio-ingestion, FR-001/FR-015, research.md Decision 12).
Replaces the Google Drive-based design (`google_drive_client.py`,
`google_drive_token_store.py`, both removed) — one folder per meeting series,
a folder's name *is* the series_id it maps to, matched exactly against the
same string `meeting_series_consent`/`structured_payload` already use
elsewhere. Unchanged from the Drive-era design.

Deliberately does no consent filtering itself (P3 — collectors don't judge):
every folder is returned as a candidate, whatever its name. `AudioCollector`
checks each one's name against `MeetingSeriesConsentRepositoryPort.
is_active()` — a folder whose name matches no real series simply never has
an active consent row either, so it's skipped by that same check, not a
second "known series" lookup this class would otherwise need to duplicate
(research.md Decision 11).

Requires no credential, token, or external account of any kind — the one
material difference from the Drive-era design this replaces, and the entire
point of this revision (research.md Decision 12).
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".webm"}


class LocalStorageAccessError(Exception):
    """The configured local storage location is not accessible — missing,
    not a directory, or unreadable (removed, unmounted, or
    permission-denied). A whole-connection failure
    `RunCollectorUseCase.execute()`'s try/except (research.md Decision 5)
    records as an honest, visible coverage gap (FR-012), distinct from a
    single recording's own read/transcription failure (FR-013, handled
    per-item inside `AudioCollector.fetch()`)."""


@dataclass(frozen=True)
class LocalRecording:
    file_id: str
    name: str
    modified_time: str
    series_id: str


class LocalStorageClient:
    def __init__(self, root_path: str) -> None:
        self._root = Path(root_path)

    def list_recordings(self) -> list[LocalRecording]:
        """Every recording in every series-folder under the deployment's
        configured local storage root — one entry per audio file,
        `series_id` set to its containing folder's name (FR-015)."""
        if not self._root.is_dir():
            raise LocalStorageAccessError(
                f"Meeting audio storage location is not accessible: {self._root}"
            )
        try:
            series_folders = [entry for entry in self._root.iterdir() if entry.is_dir()]
        except OSError as exc:
            raise LocalStorageAccessError(
                f"Meeting audio storage location is not accessible: {self._root}"
            ) from exc

        recordings: list[LocalRecording] = []
        for folder in series_folders:
            series_id = folder.name
            try:
                files = [
                    entry
                    for entry in folder.iterdir()
                    if entry.is_file() and entry.suffix.lower() in _AUDIO_EXTENSIONS
                ]
            except OSError:
                logger.exception("meeting audio series folder unreadable, skipped: %s", folder)
                continue
            for file_path in files:
                relative_path = file_path.relative_to(self._root).as_posix()
                modified_time = datetime.fromtimestamp(
                    file_path.stat().st_mtime, tz=UTC
                ).isoformat()
                recordings.append(
                    LocalRecording(
                        file_id=relative_path,
                        name=file_path.name,
                        modified_time=modified_time,
                        series_id=series_id,
                    )
                )
        return recordings

    def read(self, file_id: str) -> bytes:
        return (self._root / file_id).read_bytes()
