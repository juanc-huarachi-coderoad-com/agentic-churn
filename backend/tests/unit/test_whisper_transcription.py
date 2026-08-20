"""`WhisperTranscriptionAdapter` (specs/019-meeting-audio-ingestion,
FR-006/FR-007) — mocked `AsyncOpenAI` client (no live OpenAI call), a fake
`LLMPort` (mirrors `test_meeting_reader.py`'s `_FakeLLM`), and a fake
`diarize` callable (no real `pyannote`/`torch` call)."""

from dataclasses import dataclass
from typing import Any, TypeVar
from unittest.mock import AsyncMock, patch

from app.ingestion.adapters.whisper_transcription import (
    DiarizationSegment,
    SpeakerMatch,
    SpeakerMatchOutput,
    WhisperTranscriptionAdapter,
)
from app.readers.application.ports import LLMPort

T = TypeVar("T")


class _FakeLLM(LLMPort):
    def __init__(self, response: Any) -> None:
        self._response = response
        self.call_count = 0
        self.last_prompt: str | None = None

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        self.call_count += 1
        self.last_prompt = prompt
        return self._response


@dataclass
class _FakeSegment:
    start: float
    end: float
    text: str


def _mock_openai_response(segments: list[_FakeSegment]) -> AsyncMock:
    response = AsyncMock()
    response.segments = segments
    return response


def _patched_client(segments: list[_FakeSegment]):
    client = AsyncMock()
    client.audio.transcriptions.create = AsyncMock(
        return_value=_mock_openai_response(segments)
    )
    return patch(
        "app.ingestion.adapters.whisper_transcription.AsyncOpenAI", return_value=client
    )


async def test_lazy_client_construction_and_honest_missing_key_failure():
    """Mirrors OpenAIEmbeddingAdapter's own precedent — no eager `__init__`
    raise, so a missing key is isolated to this one item's failure
    (FR-013), not a whole-run crash."""
    adapter = WhisperTranscriptionAdapter(
        openai_api_key="", llm=_FakeLLM(SpeakerMatchOutput(matches=[])), diarize=lambda _: []
    )
    threw = False
    try:
        await adapter.transcribe(b"audio", "meeting.mp3", [])
    except ValueError as exc:
        threw = True
        assert "OPENAI_API_KEY" in str(exc)
    assert threw


async def test_confident_speaker_match_substitutes_the_real_name():
    segments = [_FakeSegment(start=0.0, end=2.0, text="We'll ship the export fix by Friday.")]
    diarization = [DiarizationSegment(start=0.0, end=2.0, speaker_label="SPEAKER_00")]
    llm = _FakeLLM(
        SpeakerMatchOutput(
            matches=[SpeakerMatch(speaker_label="SPEAKER_00", matched_name="Jane", confidence=0.9)]
        )
    )
    adapter = WhisperTranscriptionAdapter(
        openai_api_key="sk-test", llm=llm, diarize=lambda _: diarization
    )

    with _patched_client(segments):
        result = await adapter.transcribe(b"audio", "meeting.mp3", ["Jane", "Diego"])

    assert result.text == "Jane: We'll ship the export fix by Friday."
    assert result.primary_speaker_name == "Jane"
    assert llm.call_count == 1


async def test_ambiguous_segment_stays_unattributed_never_guessed():
    """FR-007: a low-confidence or null match must never surface as a real
    name — the segment stays labeled "Unknown Speaker" instead."""
    segments = [_FakeSegment(start=0.0, end=2.0, text="Sounds good, thanks.")]
    diarization = [DiarizationSegment(start=0.0, end=2.0, speaker_label="SPEAKER_01")]
    llm = _FakeLLM(
        SpeakerMatchOutput(
            matches=[
                SpeakerMatch(speaker_label="SPEAKER_01", matched_name="Jane", confidence=0.4)
            ]
        )
    )
    adapter = WhisperTranscriptionAdapter(
        openai_api_key="sk-test", llm=llm, diarize=lambda _: diarization
    )

    with _patched_client(segments):
        result = await adapter.transcribe(b"audio", "meeting.mp3", ["Jane", "Diego"])

    assert result.text == "Unknown Speaker: Sounds good, thanks."
    assert result.primary_speaker_name is None


async def test_no_candidate_names_skips_the_matching_call_entirely():
    segments = [_FakeSegment(start=0.0, end=2.0, text="Internal standup notes.")]
    diarization = [DiarizationSegment(start=0.0, end=2.0, speaker_label="SPEAKER_00")]
    llm = _FakeLLM(SpeakerMatchOutput(matches=[]))
    adapter = WhisperTranscriptionAdapter(
        openai_api_key="sk-test", llm=llm, diarize=lambda _: diarization
    )

    with _patched_client(segments):
        result = await adapter.transcribe(b"audio", "meeting.mp3", [])

    assert result.text == "Unknown Speaker: Internal standup notes."
    assert result.primary_speaker_name is None
    assert llm.call_count == 0


async def test_matching_llm_failure_falls_back_to_unattributed_not_a_crash():
    segments = [_FakeSegment(start=0.0, end=2.0, text="We'll ship Friday.")]
    diarization = [DiarizationSegment(start=0.0, end=2.0, speaker_label="SPEAKER_00")]

    class _RaisingLLM(LLMPort):
        async def generate_structured(self, prompt: str, schema: type[T]) -> T:
            raise TimeoutError("model call exhausted retries")

    adapter = WhisperTranscriptionAdapter(
        openai_api_key="sk-test", llm=_RaisingLLM(), diarize=lambda _: diarization
    )

    with _patched_client(segments):
        result = await adapter.transcribe(b"audio", "meeting.mp3", ["Jane"])

    assert result.text == "Unknown Speaker: We'll ship Friday."
    assert result.primary_speaker_name is None


async def test_consecutive_same_speaker_segments_are_grouped_into_one_turn():
    segments = [
        _FakeSegment(start=0.0, end=1.0, text="We'll ship"),
        _FakeSegment(start=1.0, end=2.0, text="the export fix by Friday."),
    ]
    diarization = [DiarizationSegment(start=0.0, end=2.0, speaker_label="SPEAKER_00")]
    llm = _FakeLLM(
        SpeakerMatchOutput(
            matches=[SpeakerMatch(speaker_label="SPEAKER_00", matched_name="Jane", confidence=0.9)]
        )
    )
    adapter = WhisperTranscriptionAdapter(
        openai_api_key="sk-test", llm=llm, diarize=lambda _: diarization
    )

    with _patched_client(segments):
        result = await adapter.transcribe(b"audio", "meeting.mp3", ["Jane"])

    assert result.text == "Jane: We'll ship the export fix by Friday."
    assert result.text.count("Jane:") == 1
