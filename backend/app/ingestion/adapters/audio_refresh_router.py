"""`POST /api/meeting-audio/refresh` (specs/019-meeting-audio-ingestion,
`contracts/meeting-audio.md`). CS-lead-only (`require_full_access`, FR-002)
— synchronously runs one on-demand collection cycle through the same
`RunCollectorUseCase.execute()` the scheduled `worker.py` job calls
(`trigger="manual"` here, `"poll"` there — both real, caller-supplied
values now, research.md Decision 5's correction).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.application.dependencies import CurrentUser, require_full_access
from app.config import settings
from app.db import get_session
from app.ingestion.adapters.audio_collector import AudioCollector
from app.ingestion.adapters.encryption import BucketedFernetEncryption
from app.ingestion.adapters.google_drive_client import GoogleDriveClient
from app.ingestion.adapters.google_drive_token_store import GoogleDriveTokenStore
from app.ingestion.adapters.key_store import FileKeyStore
from app.ingestion.adapters.pyannote_diarization import diarize
from app.ingestion.adapters.sqlalchemy_repositories import (
    SqlAlchemyClientProfileContext,
    SqlAlchemyCollectorRunRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyMeetingSeriesConsentRepository,
)
from app.ingestion.adapters.whisper_transcription import WhisperTranscriptionAdapter
from app.ingestion.application.use_cases import RunCollectorUseCase
from app.readers.adapters.anthropic_llm import AnthropicLLMAdapter

router = APIRouter()


class AudioRefreshResponse(BaseModel):
    recordings_found: int
    transcribed: int
    skipped_no_consent: int
    failed: int
    coverage_report_id: str
    source_error: str | None = None


def _build_audio_collector(session: AsyncSession) -> AudioCollector:
    return AudioCollector(
        drive=GoogleDriveClient(
            token_store=GoogleDriveTokenStore(
                settings.google_drive_token_path,
                settings.google_drive_client_id,
                settings.google_drive_client_secret,
            ),
            root_folder_id=settings.google_drive_root_folder_id,
        ),
        transcriber=WhisperTranscriptionAdapter(
            openai_api_key=settings.openai_api_key,
            llm=AnthropicLLMAdapter(settings.anthropic_api_key, settings.reader_model_id),
            diarize=diarize,
        ),
        consent=SqlAlchemyMeetingSeriesConsentRepository(session),
        collector_runs=SqlAlchemyCollectorRunRepository(session),
        profile_context=SqlAlchemyClientProfileContext(session),
    )


@router.post("/api/meeting-audio/refresh", response_model=AudioRefreshResponse)
async def refresh_meeting_audio(
    current_user: CurrentUser = Depends(require_full_access),
    session: AsyncSession = Depends(get_session),
) -> AudioRefreshResponse:
    key_store = FileKeyStore(settings.data_keys_dir)
    encryption = BucketedFernetEncryption(key_store, settings.encryption_key_path)
    collector = _build_audio_collector(session)
    use_case = RunCollectorUseCase(
        collector_runs=SqlAlchemyCollectorRunRepository(session),
        events=SqlAlchemyEventRepository(session),
        profile_context=SqlAlchemyClientProfileContext(session),
        encryption=encryption,
        key_store=key_store,
    )
    now = datetime.now(UTC)
    result = await use_case.execute(
        collector, window_start=now, window_end=now, trigger="manual"
    )

    # `source_error` (contracts/meeting-audio.md's "degraded" response
    # shape) — the detailed message lives on `collector_runs.error`, not
    # `coverage_reports.gap_reason` (which only ever holds the generic
    # "{source_type} unreachable" summary `GET /api/coverage` shows;
    # `RunCollectorUseCase.execute()`'s own `gap_reasons` list, use_cases.py
    # — a real gap found writing this route's own test: the two columns
    # serve different views, and this route needs the more specific one).
    error_row = (
        await session.execute(
            text(
                "SELECT cr.error FROM collector_runs cr "
                "JOIN coverage_reports cov ON cov.collector_run_id = cr.id "
                "WHERE cov.id = :id"
            ),
            {"id": result.coverage_report_id},
        )
    ).one()

    stats = collector.last_run_stats
    return AudioRefreshResponse(
        recordings_found=stats.recordings_found,
        transcribed=stats.transcribed,
        skipped_no_consent=stats.skipped_no_consent,
        failed=stats.failed,
        coverage_report_id=str(result.coverage_report_id),
        source_error=error_row.error,
    )
