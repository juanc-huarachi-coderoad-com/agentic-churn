# Contract: Meeting audio ingestion (consent + manual refresh)

Three new endpoints, all under the same bearer-token auth every other endpoint in this API
already requires. Consent and refresh are both write-capable, client-affecting actions, so both
use `require_full_access` — the same dependency `POST /api/profile/reload` and
`POST /api/profile` already use (`backend/app/context/adapters/profile_router.py`) — which
already excludes `role = account_executive` per `specs/011-production-hardening` FR-005.

## `GET /api/meeting-audio/consent`

- **Auth**: bearer token required (any role — read-only).
- **Response (200)**: current consent status per known meeting series.

  ```json
  {
    "series": [
      {
        "series_id": "acme-weekly-sync",
        "status": "granted",
        "all_parties_confirmed": true,
        "documented_by": "jane.cs@meridian.example",
        "documented_at": "2026-08-10T09:00:00Z"
      },
      {
        "series_id": "acme-qbr",
        "status": "revoked",
        "all_parties_confirmed": true,
        "documented_by": "jane.cs@meridian.example",
        "documented_at": "2026-08-18T14:00:00Z"
      }
    ]
  }
  ```

  One row per `series_id` that has ever had a consent decision — the latest
  `meeting_series_consent` row for each, per `data-model.md`'s query pattern. A series with no
  decision ever recorded does not appear in this list (equivalent to "never consented").

## `POST /api/meeting-audio/consent`

- **Auth**: bearer token required, `require_full_access` (FR-016).
- **Request**:

  ```json
  {
    "series_id": "acme-weekly-sync",
    "status": "granted",
    "all_parties_confirmed": true,
    "note": "Confirmed verbally with all three Acme attendees on the 2026-08-10 call."
  }
  ```

- **Response (201)**: the created `meeting_series_consent` row (same shape as one entry in the
  `GET` response above).
- **Failure (422)**: `status = "granted"` with `all_parties_confirmed = false` — a partial-party
  grant is rejected at the application boundary (`data-model.md`'s validation rule), never
  persisted.
- **Failure (401 / 403)**: no token, or a token without `require_full_access`.

Revocation uses the same endpoint with `"status": "revoked"` — always a new row, never an
update to an existing one (append-only, `research.md` Decision 4).

## `POST /api/meeting-audio/refresh`

Manual, on-demand collection cycle (FR-002/User Story 3) — synchronously runs one
`RunCollectorUseCase.execute(audio_collector, ...)` pass and returns its outcome, the same
trigger the scheduled `worker.py` job uses (`trigger = "manual"` vs `"poll"`).

- **Auth**: bearer token required, `require_full_access`.
- **Response (200)**:

  ```json
  {
    "recordings_found": 2,
    "transcribed": 1,
    "skipped_no_consent": 1,
    "failed": 0,
    "coverage_report_id": "b3f1...-uuid"
  }
  ```

  - `recordings_found`: total items discovered in the connected Drive location this cycle,
    before the consent gate.
  - `skipped_no_consent`: items belonging to a series without active consent — dropped before
    download, per FR-003.
  - `failed`: items whose download or transcription failed (per-item failure, FR-013) —
    distinct from a whole-cycle failure (next response shape).
  - A cycle where nothing new is found still returns `200` with all counts `0` — the explicit
    "nothing new" outcome User Story 3's second acceptance scenario requires, never conflated
    with an error.

- **Response (200, degraded)**:

  ```json
  {
    "recordings_found": 0,
    "transcribed": 0,
    "skipped_no_consent": 0,
    "failed": 0,
    "coverage_report_id": "b3f1...-uuid",
    "source_error": "Google Drive authorization is no longer valid — reconnect required."
  }
  ```

  `source_error` present (FR-012) means the whole cycle failed before any item-level processing
  — the Drive connection itself, not an individual recording. Still `200`: the request to
  *trigger* a refresh succeeded; the refresh itself surfaced a real, visible degradation,
  consistent with `GET /api/coverage`'s existing pattern of reporting source health as data, not
  as an HTTP error (`specs/006-dashboard-evidence-trace/contracts/coverage.md`).

- **Failure (401 / 403)**: no token, or a token without `require_full_access`.

## Traceability

FR-001, FR-002, FR-003, FR-004, FR-005, FR-012, FR-013, FR-016; `data-model.md`'s
`meeting_series_consent`; `research.md` Decisions 3, 5, 9.
