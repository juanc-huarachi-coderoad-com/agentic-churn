# Contract: System health (coverage)

`architecture/07-api-spec.md` defines the full `CoverageResponse` schema —
not re-specified here.

## `GET /api/coverage`

- **Auth**: bearer token required.
- **Response (200)**:

  ```json
  {
    "sources": [
      { "source_type": "zendesk", "status": "connected", "last_successful_sync_at": "2026-08-15T13:00:00Z" },
      { "source_type": "gmail", "status": "connected", "last_successful_sync_at": "2026-08-15T13:00:00Z" },
      { "source_type": "warehouse", "status": "connected", "last_successful_sync_at": "2026-08-15T13:00:00Z" }
    ],
    "quarantine": []
  }
  ```

  - `sources`: every configured `sources` row, real `status`/
    `last_successful_sync_at`.
  - `quarantine`: real, and **permanently empty until feature 007's
    `ValidationGate` exists** — `findings.status = 'quarantined'` never occurs
    yet (spec.md's Note on scope). Not a placeholder — an honest reflection
    of "no finding has ever been quarantined."

- **Failure (401)**: no token, or an invalid one.

## Traceability

`REQ-M8-06`; `architecture/07-api-spec.md`'s `CoverageResponse`; spec.md's
Note on scope (quarantine list).
