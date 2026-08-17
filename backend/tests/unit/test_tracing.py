"""Pure unit test for `traced()` (specs/011-production-hardening, User Story 3) —
no DB, no live OTel collector: a real `TracerProvider` wired to OTel's own
`InMemorySpanExporter` testing utility, read back in-process.

Patches `get_tracer` directly (`monkeypatch`) rather than touching OTel's global
`TracerProvider` singleton — that singleton can only be set once per process (by
design, to prevent runtime reconfiguration in production), and this test suite's
other files (via `app.main`/`app.worker` imports) may have already set it to a
real, non-in-memory provider before this module even loads. Patching the
function `traced()` actually calls sidesteps that race entirely.
"""

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.observability.adapters import tracing as tracing_module
from app.observability.adapters.tracing import traced


@pytest.fixture
def exporter(monkeypatch):
    provider = TracerProvider()
    memory_exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(memory_exporter))
    test_tracer = provider.get_tracer("test")
    monkeypatch.setattr(tracing_module.trace, "get_tracer", lambda *_args, **_kwargs: test_tracer)
    yield memory_exporter


def test_successful_block_records_success_outcome_and_nonnegative_duration(exporter):
    with traced("some_operation"):
        pass

    (span,) = exporter.get_finished_spans()
    assert span.name == "some_operation"
    assert span.attributes["outcome"] == "success"
    assert span.attributes["duration_ms"] >= 0


def test_degraded_block_records_degraded_outcome(exporter):
    with traced("reader_execution:recurrence") as span_state:
        span_state.mark_degraded()

    (span,) = exporter.get_finished_spans()
    assert span.attributes["outcome"] == "degraded"


def test_exception_records_failure_outcome_and_still_propagates(exporter):
    with pytest.raises(ValueError, match="boom"), traced("some_operation"):
        raise ValueError("boom")

    (span,) = exporter.get_finished_spans()
    assert span.attributes["outcome"] == "failure"
    assert span.attributes["duration_ms"] >= 0
