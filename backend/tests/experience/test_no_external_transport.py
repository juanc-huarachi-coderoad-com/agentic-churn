"""SC-004's "code-level architecture review" as a real, mechanically-run
test (`research.md` Decision 14, `/speckit-analyze` finding G2) — statically
scans every file this feature added or extended for an import of an
outbound-transport client. A `POST /api/drafts/{id}/log-as-sent` route that
returns `204` with no `/send` route existing (`test_draft_routes_real_db.py`)
proves no *route* transmits externally; this proves no *import* could,
which is the stronger, structural guarantee REQ-M10-P1 requires.
"""

import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_SCANNED_FILES = (
    "app/experience/adapters/draft_router.py",
    "app/experience/adapters/sqlalchemy_repository.py",
    "app/experience/application/use_cases.py",
    "app/experience/application/prompts/draft_composer_v1.py",
    "app/experience/domain/entities.py",
    "app/experience/domain/services.py",
)

_FORBIDDEN_MODULES = (
    "smtplib",
    "httpx",
    "requests",
    "aiohttp",
    "boto3",  # SES/SNS
    "twilio",
    "slack_sdk",
    "sendgrid",
    "urllib.request",
)


def _imported_module_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


def test_no_file_this_feature_touches_imports_an_outbound_transport_client():
    violations: dict[str, set[str]] = {}
    for relative_path in _SCANNED_FILES:
        path = _BACKEND_ROOT / relative_path
        assert path.exists(), f"expected file missing: {relative_path}"
        imported = _imported_module_names(path)
        matched = {
            module
            for module in imported
            if any(
                module == forbidden or module.startswith(f"{forbidden}.")
                for forbidden in _FORBIDDEN_MODULES
            )
        }
        if matched:
            violations[relative_path] = matched

    assert not violations, (
        "outbound-transport import found — violates REQ-M10-P1's structural "
        f"no-send guarantee: {violations}"
    )


def test_scanned_file_list_covers_every_new_or_extended_file():
    """A weaker but still useful guard: fails loudly if this feature's own
    file set drifts from `plan.md`'s Project Structure without this test
    being updated to match."""
    for relative_path in _SCANNED_FILES:
        assert (_BACKEND_ROOT / relative_path).is_file()
