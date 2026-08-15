"""SC-005/FR-015 — no `anthropic`/`openai` import anywhere in
`app.readers.domain`/`app.readers.application`. `.importlinter`'s
`readers-application-purity` contract already enforces this mechanically
(`app.readers.adapters` is itself forbidden there too, alongside the two AI
SDKs); this test confirms `lint-imports` passes clean, the same check
`quickstart.md`'s Automated coverage section runs manually.
"""

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_LINT_IMPORTS = Path(sys.executable).parent / "lint-imports"


def test_lint_imports_passes_clean():
    result = subprocess.run(
        [str(_LINT_IMPORTS), "--config", "../.importlinter"],
        cwd=_BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
