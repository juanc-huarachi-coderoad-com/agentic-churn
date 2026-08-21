# Quickstart: Meeting Audio Ingestion

Prerequisites: the fully containerized stack (`docker compose up --build -d`), this feature's
migration applied (`alembic upgrade head`), `OPENAI_API_KEY` and `PYANNOTEAI_API_KEY` set
(reused from the existing Recurrence-reader configuration and `research.md` Decision 7,
`app/config.py`), and one meeting-series folder created under the local storage root containing
a short test recording (`research.md` Decisions 1 and 12's folder-per-series convention,
`spec.md` FR-015) — no external account, OAuth grant, or secret file required:

```bash
mkdir -p demo/meeting-audio/wara-weekly-sync
cp demo-wara/wara-weekly-sync-recovery.m4a demo/meeting-audio/wara-weekly-sync/
```

This lands inside the `./demo` directory already bind-mounted read-only into both the `api` and
`worker` containers (`docker-compose.yml`, `research.md` Decision 12) — no compose or mount
change needed, no container rebuild needed to pick up a new recording. `wara-weekly-sync` is
the `series_id` used in the steps below; substitute your own test series name if different.

## User Story 2 — Consent is documented and enforced (validate first — it gates User Story 1)

1. `GET /api/meeting-audio/consent` — confirm the test series does not appear (no decision
   recorded yet).
2. `python -m app.worker --run-once audio` (mirrors the existing `--run-once absence`/`--run-
   once score`/`--run-once retention` pattern, `worker.py`) — confirm via `psql` that
   `raw_envelopes` has zero rows for the test recording's `source_native_id` (FR-003, mirroring
   `tests/ingestion/test_post_mvp_sources_real_db.py::
   test_unconsented_calendar_series_never_reaches_the_ledger`'s existing assertion shape).
3. `POST /api/meeting-audio/consent` as a `cs_lead` user: `{"series_id": "<test-series>",
   "status": "granted", "all_parties_confirmed": true}` — expect `201`.
4. `GET /api/meeting-audio/consent` — confirm the series now shows `status: "granted"`.
5. Repeat step 3 with `"all_parties_confirmed": false` — expect `422`, no row inserted
   (`data-model.md`'s validation rule).

## User Story 1 — Meeting evidence appears in the score automatically

1. With consent granted (previous section), run `python -m app.worker --run-once audio` again.
2. Confirm via `psql`: one new `raw_envelopes` row for the test recording, one new `events` row
   with `event_type = 'meeting'`, and the audio file itself is gone from wherever it was
   downloaded to (no lingering temp file — FR-008/SC-004).
3. Run the existing reader pass (`scripts/run_readers.py`, per `demo/03-environment-and-
   fixtures-checklist.md`'s documented approach) — confirm a `meeting_commitment` finding
   appears if the test recording contains a verbal commitment, citing the new event's ID (P1 —
   evidence or it does not exist).
4. `python -m app.worker --run-once score` — confirm the next `score_runs` row reflects the new
   finding.
5. Run `python -m app.worker --run-once audio` a second time with the same recording still
   present in local storage — confirm no new `raw_envelopes`/`events` row is created (FR-011,
   idempotency via `Envelope.idempotency_key`).

## User Story 3 — On-demand refresh

1. Add a second test recording to the same consented series folder under local storage
   (`cp <another-file>.m4a demo/meeting-audio/wara-weekly-sync/`).
2. `POST /api/meeting-audio/refresh` as a `cs_lead` user — expect `200` within the request
   itself (excluding transcription time), `transcribed: 1` in the response body.
3. Confirm the evidence trace (`GET /api/evidence/{id}` for the resulting finding, or the
   dashboard) reflects the new recording without waiting for the next scheduled cycle (SC-003).
4. Call `POST /api/meeting-audio/refresh` again immediately, with nothing new in local storage —
   expect `200`, every count `0`, no error (User Story 3's second acceptance scenario).

## User Story 4 — Honest degradation

1. Temporarily make the local storage location inaccessible to the running containers — e.g.
   rename the directory (`mv demo/meeting-audio demo/meeting-audio.bak`) or, to simulate a
   permission failure instead of a missing path, `chmod 000 demo/meeting-audio` on the host.
2. `POST /api/meeting-audio/refresh` — expect `200` with `source_error` present (contract's
   "degraded" response shape), not a `500` and not a response indistinguishable from "nothing
   new."
3. `GET /api/coverage` — confirm the `transcripts` source shows a real gap, consistent with how
   any other source's failure already renders there
   (`specs/006-dashboard-evidence-trace/contracts/coverage.md`).
4. `python -m app.worker --run-once score` — confirm the score is unchanged from its prior value
   (frozen, per `specs/004-score-engine` FR-011) rather than computed as if the audio source were
   healthy.
5. Restore the directory (`mv demo/meeting-audio.bak demo/meeting-audio`, or `chmod 755
   demo/meeting-audio`) and repeat step 2 — confirm normal (non-degraded) behavior resumes
   immediately, with no re-authentication or reconnection step of any kind (FR-001) — the local
   storage design has nothing to re-authenticate.
