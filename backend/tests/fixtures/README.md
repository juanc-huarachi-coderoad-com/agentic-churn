# Test fixtures

Empty in this feature (Project Foundation) — populated in build-order Phase 4 (Score
engine), per `tests/strategy.md`.

The golden-replay test fixture will live at `demo/fixtures/meridian-week.json` (repo
root, not this directory — it's shared with the demo's contingency path,
`demo/03-environment-and-fixtures-checklist.md`), fed through `SimulatedCollector` into a
fresh database. This directory exists now so `backend/tests/golden_replay/` and
`backend/tests/scoring/`'s placeholder tests (`spec.md` User Story 3) have a documented,
stable path to point at once that fixture is written.
