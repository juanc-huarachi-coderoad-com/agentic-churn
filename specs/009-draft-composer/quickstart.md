# Quickstart: Validating the Draft Composer

Prerequisites: the stack from features 001–008 running, seeded, ingested,
read, scored, validated, and narrated
(`specs/008-narrator-and-ask-agent/quickstart.md`'s steps —
`ANTHROPIC_API_KEY`/`GENERATION_MODEL_ID` already configured there). This
feature adds **no new environment variable, no new Python dependency, and no
migration** (`research.md` Decisions 1, 11) — it reuses the Sonnet-tier model
already configured for the Narrator and Ask agent.

```bash
docker compose up --build -d
```

## 1. Generate a draft for the worked example's top issue

```bash
TOKEN=$(curl -s -X POST http://localhost:${API_PORT:-8000}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# iss-A / stk-ana come from examples/01-end-to-end-walkthrough.md's own
# worked example — the same issue and stakeholder every prior feature's
# quickstart traces.
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"issue_id":"iss-A","stakeholder_id":"stk-ana","tone_variant":"direct"}' \
  http://localhost:${API_PORT:-8000}/api/drafts | jq .
```

**Expected**: `200`, `checks_passed: true`, `draft_text` opening with the
specific failure ("we took 19 hours... we promised 4") before any apology,
containing exactly one ask, `evidence_event_ids` non-empty and tracing back
to `evt-2` (ticket #456) — reproducing `examples/01-end-to-end-walkthrough.md`
§13's `draft-1` row for the first time this codebase has ever generated it.

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT id, issue_id, stakeholder_id, tone_variant, checks_passed FROM draft_messages ORDER BY created_at DESC LIMIT 1;"
```

**Expected**: 1 row — the first real `draft_messages` row this codebase has
ever had (table exists since feature 001, unpopulated until now, the same
status `narrator_outputs`/`ask_queries` had before feature 008).

## 2. Request a different tone variant

```bash
DRAFT_ID=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"issue_id":"iss-A","stakeholder_id":"stk-ana","tone_variant":"brief"}' \
  http://localhost:${API_PORT:-8000}/api/drafts | jq -r .id)
```

**Expected**: `200`, a second, distinct `draft_messages` row (`research.md`
Decision 9) — same underlying facts as step 1, shorter/more direct phrasing.

## 3. Copy and log — confirm no send path exists

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:${API_PORT:-8000}/api/drafts/$DRAFT_ID/copy
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:${API_PORT:-8000}/api/drafts/$DRAFT_ID/log-as-sent

curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:${API_PORT:-8000}/api/drafts/$DRAFT_ID/send
```

**Expected**: `204`, `204`, then `404` — there is no `/send` route to hit,
anywhere, structurally (REQ-M10-P1). `docker compose exec db psql ... -c
"SELECT copied_at, logged_manually_at FROM draft_messages WHERE id =
'$DRAFT_ID';"` shows both timestamps stamped, no `sent_at` column exists to
even query.

## 4. Trigger each of the five pre-display checks (scripted red-team)

```bash
docker compose exec api python -c "
from app.experience.domain.services import (
    verify_facts, verify_dates, verify_no_invented_cause,
    verify_no_leak, verify_no_concession,
)
from app.narrator.domain.entities import VerifiedFactSet
from app.experience.domain.entities import VerifiedDateSet

facts = VerifiedFactSet(numbers=frozenset({'19'}), names=frozenset({'Ana'}))
dates = VerifiedDateSet(dates=frozenset({'Thursday'}))

print(verify_facts('Ana — we took 19 hours to respond.', facts).passed)  # True
print(verify_facts('We also spoke with David about this.', facts).passed)  # False — 'David' isn't a verified name
print(verify_dates('I will call you before Thursday.', dates).passed)    # True
print(verify_dates('I will call you before Friday.', dates).passed)      # False — invented date
print(verify_no_invented_cause('This happened because we lost the Meridian contract with Acme.', facts).passed)  # False — invented cause
print(verify_no_leak('Ana — we took 19 hours to respond.', 'Meridian Logistics').passed)  # True
print(verify_no_leak('Your risk score dropped this week.', 'Meridian Logistics').passed)  # False — internal leak
print(verify_no_concession('Engineering is on it today.', ).passed)      # True
print(verify_no_concession('We can offer you a 10% discount.', ).passed) # False — commercial concession
"
```

**Expected**: `True`/`False` alternating exactly as commented —
demonstrates all five pure check functions directly (`research.md`
Decision 6, revised 2026-08-16 per `/speckit-analyze` findings G1/U1), the
same "prove it with the real function, not just a passing route test"
discipline `specs/008-.../quickstart.md` used for the Narrator's
fact-check. A live `POST /api/drafts` call whose generation happens to fail
any one of the five returns `422 {"detail": "Couldn't generate a draft —
try again"}` — never a `200` with `checks_passed: false`, and never a
message naming which of the five failed.

## 4b. Confirm a nonexistent stakeholder is rejected

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"issue_id":"iss-A","stakeholder_id":"00000000-0000-0000-0000-000000000000","tone_variant":"direct"}' \
  http://localhost:${API_PORT:-8000}/api/drafts
```

**Expected**: `404` — `StakeholderReadPort.get()` returns `None`
(`research.md` Decision 13, `/speckit-analyze` finding U3), the same
not-found handling `issue_id` already gets.

## 4c. Confirm the mechanical no-transport scan passes

```bash
docker compose exec api python -m pytest tests/experience/test_no_external_transport.py -v
```

**Expected**: passes — no file this feature added or extended imports an
outbound-transport client (`research.md` Decision 14, `/speckit-analyze`
finding G2, SC-004) — the mechanical form of "a code-level review," not a
manual inspection step.

## 5. Confirm the Ask agent's handoff reaches this feature

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question": "write to Ana about this"}' \
  http://localhost:${API_PORT:-8000}/api/ask | jq .
```

**Expected**: `component: "draft_handoff"`, `component_props: {"issue_id":
"iss-A", "stakeholder_id": "stk-ana"}` (feature 008, unchanged) — then, in the
browser, the Ask bar's `DraftHandoff` renders a real link into the new
`frontend/src/draft-composer/` panel instead of the static placeholder text
(`research.md` Decision 10) — the first time this handoff has connected to
anything real.

## 6. Confirm golden-replay is untouched

`draft_messages` is intentionally **not** part of the golden-replay snapshot
(`backend/tests/golden_replay/`'s snapshot covers `score_runs`/
`score_contributions`/`narrator_outputs` only) — drafts are triggered by an
explicit human action against a non-deterministic LLM call, not derived
pipeline state. No change to `tests/golden_replay/` is expected or required
by this feature; running it after steps 1–5 should still pass unchanged,
confirming this feature adds an interactive, human-triggered surface without
touching the deterministic replay guarantee (`research.md` Decision 12).
