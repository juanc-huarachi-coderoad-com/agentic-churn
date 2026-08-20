"""`diarize()` — speaker-turn segmentation via `pyannote.audio`
(specs/019-meeting-audio-ingestion, research.md Decision 7). The `pyannote`/
`torch` import is deferred to inside the function body, not module level —
mirrors `OpenAIEmbeddingAdapter`'s lazy-client pattern, and matters more here
than there: `pyannote.audio`'s pretrained pipeline is a multi-hundred-
megabyte, gated Hugging Face model download, so importing this module (e.g.
transitively, while running an unrelated test that only mocks
`WhisperTranscriptionAdapter`'s `diarize` callable) must never force that
weight in.
"""

import tempfile
from pathlib import Path
from typing import Any

from app.ingestion.adapters.whisper_transcription import DiarizationSegment

_PIPELINE_NAME = "pyannote/speaker-diarization-3.1"

_pipeline: Any = None


def diarize(audio_bytes: bytes) -> list[DiarizationSegment]:
    global _pipeline
    from pyannote.audio import Pipeline

    if _pipeline is None:
        _pipeline = Pipeline.from_pretrained(_PIPELINE_NAME)

    # pyannote's pipeline takes a file path, not in-memory bytes — a
    # short-lived temp file, deleted in the `finally` block regardless of
    # outcome (the same "audio never persists" discipline
    # `AudioCollector.fetch()` itself already applies to the original
    # download, research.md Decision 8 — this is its own audio copy, held no
    # longer than this one diarization call needs it for).
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = Path(tmp.name)
    try:
        diarization = _pipeline(str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)

    return [
        DiarizationSegment(start=turn.start, end=turn.end, speaker_label=speaker)
        for turn, _, speaker in diarization.itertracks(yield_label=True)
    ]
