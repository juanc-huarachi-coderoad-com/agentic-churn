# Quickstart: Production Hardening

Prerequisites: the same fully containerized stack every prior feature validates against
(`docker compose up --build -d`), already bootstrapped through feature 010's sequence
(`scripts/seed.py` → `run_collector.py` → `seed_score_fixture.py` → `compute_score.py`), plus
this feature's own migration applied (`alembic upgrade head`).

## User Story 1 — Retention & crypto-shredding

1. Seed an event with `occurred_at` older than the retention window, ingested under an old,
   already-expired daily key bucket (`scripts/seed_retention_fixture.py`, new for this
   feature — sets `data_key_ref` to a bucket date safely past the window).
2. Run the retention job once: `python -m app.worker --run-once retention` (mirrors the
   existing `--run-once absence`/`--run-once score` pattern already used for manual triggers).
3. Confirm via `psql`: the seeded event's `body_encrypted` is `NULL`; `retention_job_runs` has
   one new row with `status = succeeded`, `buckets_shredded >= 1`.
4. `GET /api/evidence/{id}` for any finding citing that event — confirm the response still
   renders (citation metadata present, message body marked unavailable), not a `500`.
5. Re-run the job — confirm no error, `buckets_shredded` counts only newly-eligible buckets.
6. Force a failure (e.g. temporarily point `data_keys_dir` at a read-only path) and re-run —
   confirm a `retention_job_runs` row with `status = failed` **and** a `logger.error(...)` line
   in the container's own logs (`docker compose logs worker`), independent of whether User
   Story 3 has shipped yet (FR-004a fully satisfied by User Story 1 alone — `/speckit-analyze`
   finding I1).

## User Story 2 — Account executive read-only access

1. Seed a user with `role = account_executive` (`scripts/seed.py`, extended this feature).
2. `POST /auth/login` as that user; capture the token.
3. `GET /api/dashboard` with that token — expect `200`, same payload shape a `cs_lead` token
   returns for the same client. (Informal timing check only, not an automated task —
   `/speckit-analyze` finding L2: confirm this feels like the same sub-second load a `cs_lead`
   token gets, satisfying SC-002's load-time-parity language.)
4. `POST /api/feedback` with that token — expect `403`, no row inserted into
   `feedback_verdicts`, and one `access_decision` log line with `role: account_executive`,
   `outcome: denied` (FR-008).
5. Repeat step 3 with the existing `marta` (`cs_lead`) fixture token — confirm unchanged `200`
   behavior (no regression, FR-007) and an `access_decision` log line with `outcome: allowed`.

## User Story 3 — Observability

1. Trigger a collector run (`python scripts/run_collector.py`), a score recompute, a
   `GET /api/dashboard` call, and a `POST /api/ask` call against the running stack — the four
   operation types FR-009/FR-010/FR-011 name explicitly (`/speckit-analyze` finding G2: the
   first and third of these were previously untraced).
2. Query the OTel collector/exporter's local backend (`docker compose logs otel-collector`, or
   the configured trace sink) — confirm one span per operation (`collector_run`,
   `score_recompute`, `dashboard_load`, `ask_query`) with `duration` and `outcome`.
3. Stop the trace exporter, repeat step 1 — confirm every operation still completes and every
   existing endpoint still returns its normal status code (FR-012).

## User Story 4 — Weight recalibration

1. Seed an `admin`-role user and log in.
2. Note the current `finding_type_config.version` and a `finding_type`'s `base_points`
   (`broken_response_promise` = 20, per the worked example).
3. `PATCH /api/admin/finding-types/broken_response_promise {"base_points": 25}` — expect `200`,
   a new `finding_type_config_changes` row, `finding_type_config.version` changed.
4. Confirm a new `score_runs` row exists with `trigger = weight_edit_replay` and a different
   `finding_type_config_version` than the prior run.
5. Fetch the prior `score_run` by id — confirm its stored `score`/contributions are unchanged
   (byte-identical) despite the weight edit (FR-015).
6. Repeat step 3 as a `cs_lead` token — expect `403`, and confirm an `access_decision` log line
   with `role: cs_lead`, `outcome: denied` (FR-008).

## User Story 5 — Profile editor

1. `GET /api/profile` — note the current `version_number`.
2. `POST /api/profile` with one changed field (e.g. a new stakeholder) via the frontend form,
   or directly via `curl` for a backend-only check. (Informal timing check only, not an
   automated task — `/speckit-analyze` finding L2: confirm this feels faster than editing the
   YAML file and re-running `/api/profile/reload`, satisfying SC-005's comparative language.)
3. Confirm `version_number` incremented, the change is attributed to the submitting user, and
   a subsequent `GET /api/dashboard` reflects it (e.g. a new stakeholder card).
4. Submit an invalid edit (nonexistent stakeholder reference) — expect `422`, `version_number`
   unchanged.

## User Story 6 — Post-MVP sources

1. Extend `demo/fixtures/meridian-week.json` with a `slack` array entry (already shipped as
   part of this feature, not a manual step in production use).
2. Run the collector: `python scripts/run_collector.py`.
3. `GET /api/coverage` — confirm a new `slack` source entry.
4. Confirm the next `RunReadersUseCase` pass produces an Absence or Relationship finding citing
   the new Slack-sourced event (or correctly produces none, if the fixture data doesn't cross
   either reader's threshold — either is a valid, checkable outcome).
5. Repeat for `csat` (confirm a Usage-reader finding or Tone-reader input) and for `calendar`
   with `consent_documented: true` (confirm a Meeting-reader finding) and `consent_documented:
   false` (confirm zero transcript collection, verified via `raw_envelopes` — no row for that
   series).
6. Confirm a client fixture with none of the three arrays present behaves identically to
   feature 010's existing quickstart (FR-024) — re-run feature 010's own quickstart unchanged
   as the regression check.
