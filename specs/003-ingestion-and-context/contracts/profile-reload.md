# Contract: Profile Reload

Full route already specified in `architecture/07-api-spec.md` (`POST /api/profile/reload`
and `GET /api/profile`) — not re-specified here. This document states only what's
specific to this feature's implementation.

## `POST /api/profile/reload`

- **Auth**: bearer token required (feature 002's gate — every route except `/auth/login`
  and `/health`).
- **Effect**: reads the on-disk client profile YAML (path from `Settings`), validates it
  against `context/domain/profile_schema.py` (`REQ-M3-07`), and on success:
  1. Inserts a new `client_profile_versions` row (+ `stakeholders`/`product_areas`/
     `commitments`/`profile_history_entries`) with `is_current = true`.
  2. Flips the previous current version's `is_current` to `false` in the same
     transaction.
  3. Triggers a full replay (`REQ-M3-06`) — this feature records the `replay_runs` row
     and re-derives `event_threads`/`response_pairs`; it does **not** yet touch
     `rollups` (deferred, spec.md Assumptions).
- **Success (200)**: the new profile, in `ProfileResponse`'s existing shape
  (`architecture/07-api-spec.md`).
- **Failure (422)**: schema validation failed — body includes the specific field and
  reason (`REQ-M3-07`; Pydantic's structured error, per `research.md`). No new version
  is created; `is_current` is untouched.

## `GET /api/profile`

Unchanged from `architecture/07-api-spec.md` — returns the current version, read-only.
This feature is what makes the response real instead of empty.

## Traceability

`REQ-M3-01, 02, 03, 05, 06, 07`; `architecture/07-api-spec.md` §Client profile (M3).
