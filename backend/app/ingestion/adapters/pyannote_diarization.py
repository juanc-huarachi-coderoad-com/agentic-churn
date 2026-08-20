"""`diarize()` — speaker-turn segmentation via the pyannote.ai hosted API
(specs/019-meeting-audio-ingestion, research.md Decision 7's correction —
was a locally-run `pyannote.audio` pipeline; moved to the hosted API because
that pipeline's PyTorch dependency alone dragged the deployed image to
~20GB, via the CUDA wheel closure `torch` pulls in on Linux, not just the
pretrained model weights). The `pyannoteai.sdk` import is deferred to inside
the function body, not module level — mirrors `OpenAIEmbeddingAdapter`'s
lazy-client pattern: constructing `pyannoteai.sdk.Client` itself makes a
network call (it validates the API key against pyannoteAI's `/test`
endpoint), which must never happen just from importing this module (e.g.
transitively, while running an unrelated test that only mocks
`WhisperTranscriptionAdapter`'s `diarize` callable).
"""

import tempfile
from pathlib import Path
from typing import Any

from app.config import settings
from app.ingestion.adapters.whisper_transcription import DiarizationSegment

_client: Any = None


def diarize(audio_bytes: bytes) -> list[DiarizationSegment]:
    global _client
    from pyannoteai.sdk import Client

    if not settings.pyannoteai_api_key:
        raise ValueError(
            "PYANNOTEAI_API_KEY is not configured — meeting audio diarization "
            "fails honestly rather than silently skipping (mirrors "
            "openai_api_key's own precedent)"
        )
    if _client is None:
        _client = Client(token=settings.pyannoteai_api_key)

    # pyannote.ai's API takes an uploaded file, not in-memory bytes — a
    # short-lived temp file, deleted in the `finally` block regardless of
    # outcome (the same "audio never persists" discipline
    # `AudioCollector.fetch()` itself already applies to the original
    # download, research.md Decision 8 — this is its own audio copy, held no
    # longer than this one diarization call needs it for). The copy that
    # briefly lands in pyannote.ai's own temporary storage (auto-deleted
    # within 24h per their API) is the same third-party exposure the
    # existing Whisper call already accepts for this same audio — not a new
    # category of data handling this feature introduces.
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = Path(tmp.name)
    try:
        media_url = _client.upload(tmp_path)
        job_id = _client.diarize(media_url)
        job = _client.retrieve(job_id)
    finally:
        tmp_path.unlink(missing_ok=True)

    return [
        DiarizationSegment(
            start=segment["start"], end=segment["end"], speaker_label=segment["speaker"]
        )
        for segment in job["output"]["diarization"]
    ]
