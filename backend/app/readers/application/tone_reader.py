"""`ToneReader` (REQ-M5-06, REQ-M5-12) — is this stakeholder writing
differently than *they* normally do, judged against a baseline frozen at a
human-confirmed healthy period for that specific person (P7), never a generic
sentiment scale. Zero tools, zero side effects (REQ-M5-P2/P3) — the model
only ever classifies text, it is never handed a capability."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.readers.application.ports import (
    ConfirmedBaselineRepositoryPort,
    FindingRepositoryPort,
    LLMPort,
    MessageEventRepositoryPort,
)
from app.readers.application.reader import Reader
from app.readers.domain.entities import ConfirmedBaselineWindow, MessageEventInfo
from app.scoring.domain.entities import Finding

_FINDING_TYPE = "tone_deterioration"
_MIN_BASELINE_SAMPLES = 5  # REQ-M6-CAL-04


@dataclass
class ToneModelOutput:
    """The model's closed, structured output schema (REQ-M5-12) —
    `architecture/04-ai-safety-and-model-usage.md`'s Tone reader row. The
    reader itself, not the model, assigns `cited_event_ids` (`data-model.md`'s
    `Finding.cited_event_ids` — "Set by: Reader"): the single new message
    being judged is already known deterministically, so there is nothing for
    the model to cite that the reader doesn't already know, and asking it to
    would only invite a hallucinated ID the gate would have to catch."""

    deviation: float
    magnitude: float
    confidence: float


def _build_prompt(baseline: ConfirmedBaselineWindow, message: MessageEventInfo) -> str:
    samples = "\n".join(f"- {text}" for text in baseline.sample_texts)
    return (
        "You are comparing one person's new message against their own "
        "historical writing style — never against a generic sentiment scale.\n\n"
        f"Baseline (this person's normal messages, {baseline.sample_count} samples):\n"
        f"{samples}\n\n"
        f"New message to evaluate:\n{message.text}\n\n"
        "Does the new message deviate from this person's own baseline style "
        "(e.g. shorter, more terse, colder, less detail, no greeting)? Return "
        "deviation (how confident you are that a real deviation occurred, "
        "0-1), magnitude (how large the deviation is, 0-1, 0 if none), and "
        "confidence (your certainty in this judgment, 0-1)."
    )


class ToneReader(Reader):
    reader_type = "tone"
    reader_version = "v1"

    def __init__(
        self,
        messages: MessageEventRepositoryPort,
        baselines: ConfirmedBaselineRepositoryPort,
        llm: LLMPort,
        findings: FindingRepositoryPort,
    ) -> None:
        self._messages = messages
        self._baselines = baselines
        self._llm = llm
        self._findings = findings

    async def interpret(self) -> list[Finding]:
        emitted: list[Finding] = []
        all_messages = await self._messages.list_all()
        stakeholder_ids: set[UUID] = {
            m.stakeholder_id for m in all_messages if m.stakeholder_id is not None
        }

        for stakeholder_id in stakeholder_ids:
            baseline = await self._baselines.get_confirmed_window(stakeholder_id)
            if baseline is None or baseline.sample_count < _MIN_BASELINE_SAMPLES:
                # "No history, no opinion" (REQ-M5-04, REQ-M6-CAL-04) — abstain
                # without ever calling the model.
                continue

            candidates = [
                m
                for m in all_messages
                if m.stakeholder_id == stakeholder_id and m.occurred_at > baseline.window_end
            ]
            for message in candidates:
                if await self._findings.already_interpreted(
                    reader_type=self.reader_type,
                    reader_version=self.reader_version,
                    event_id=message.event_id,
                ):
                    continue

                try:
                    result = await self._llm.generate_structured(
                        _build_prompt(baseline, message), ToneModelOutput
                    )
                except ValueError:
                    # A missing/misconfigured API key (AnthropicLLMAdapter's
                    # own fail-fast check, raised before any retry) is a
                    # systemic problem, not a per-call transient one —
                    # propagates as a reader-level failure, matching
                    # RecurrenceReader/OpenAIEmbeddingAdapter's identical
                    # precedent, rather than silently "abstaining" on every
                    # candidate message and masking a misconfigured
                    # deployment as an honestly-quiet one (found while
                    # verifying against the real container: a missing key
                    # was otherwise indistinguishable from a healthy,
                    # nothing-to-report run).
                    raise
                except Exception:
                    # Timeout/retry exhaustion -> abstain, never quarantine
                    # (architecture/06-error-handling.md — nothing was
                    # produced to quarantine).
                    continue

                if result.magnitude <= 0.0:
                    continue  # no deviation worth reporting

                emitted.append(
                    Finding(
                        id=uuid4(),
                        reader_type=self.reader_type,
                        reader_version=self.reader_version,
                        finding_type=_FINDING_TYPE,
                        magnitude=result.magnitude,
                        confidence=result.confidence,
                        cited_event_ids=(message.event_id,),
                        stakeholder_id=stakeholder_id,
                        product_area_id=None,
                        status="pending_validation",
                        state=None,
                        is_positive=False,
                    )
                )
        return emitted
