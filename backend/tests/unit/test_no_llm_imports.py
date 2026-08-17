"""Statically scans every file feature 010 added or extended — not only
`app/context/`, but also the `app/experience/` disclosure-read extension
and the `app/scoring/` `pattern_signature` refactor — for an import of
`anthropic` or `openai`. REQ-M4-05/SC-005: feedback memory never touches a
model, prompt, or embedding, across its full footprint, not just its
newest module (`specs/010-feedback-memory/research.md`, `/speckit-analyze`
finding C1, 2026-08-16).
"""

from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_FEATURE_010_FILES = [
    "app/context/domain/entities.py",
    "app/context/domain/damping_calculator.py",
    "app/context/application/ports.py",
    "app/context/application/use_cases.py",
    "app/context/adapters/sqlalchemy_repository.py",
    "app/context/adapters/feedback_router.py",
    "app/experience/application/ports.py",
    "app/experience/adapters/sqlalchemy_repository.py",
    "app/experience/application/use_cases.py",
    "app/experience/adapters/evidence_router.py",
    "app/scoring/application/use_cases.py",
]

_FORBIDDEN_IMPORTS = ("anthropic", "openai")


@pytest.mark.parametrize("relative_path", _FEATURE_010_FILES)
def test_file_imports_no_llm_sdk(relative_path: str) -> None:
    path = _BACKEND_ROOT / relative_path
    assert path.is_file(), f"{relative_path} not found"
    source = path.read_text()
    for forbidden in _FORBIDDEN_IMPORTS:
        assert f"import {forbidden}" not in source, f"{relative_path} imports {forbidden}"
        assert f"from {forbidden}" not in source, f"{relative_path} imports from {forbidden}"
