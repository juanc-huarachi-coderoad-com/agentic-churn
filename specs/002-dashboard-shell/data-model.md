# Data Model: Dashboard Shell

## No new tables

This feature adds no new tables and no migration. `users`, `auth_tokens`
(`data-base/12-users-and-auth.md`) and `client_profile_versions`
(`data-base/04-schema-context.md`) already exist and are seeded — this feature is the
first to read and write them at runtime.

## What this feature actually exercises

| Table | Written by this feature | Read by this feature |
|---|---|---|
| `users` | Never — no signup flow exists (users are seeded/admin-provisioned) | On login, to verify `password_hash` and `is_active` (FR-001, FR-010) |
| `auth_tokens` | On login (`INSERT`, `token_hash`/`expires_at`) and on logout (`UPDATE revoked_at`) | On every protected request, to validate the presented token (FR-005) |
| `client_profile_versions` | Never — profile editing is `requirements/03-client-profile.md`'s job, a later feature | On every `/api/dashboard` request, to read the current row's `client_name` (FR-008) |

## Auth token lifecycle (this feature's actual new behavior)

```text
issued (login) --> valid (every request until...) --> expired (expires_at passed)
                                                    \-> revoked (logout, before expires_at)
```

Both `expired` and `revoked` are terminal — a token is never re-validated or extended.
This is exactly `auth_tokens.expires_at`/`revoked_at`'s existing shape
(`data-base/12-users-and-auth.md`); this feature is the first code to actually drive that
state machine, not a new one.

## Validation

The acceptance test for this feature's data concern is behavioral, not structural (unlike
feature 001's DDL-import concern): exercise the full login → protected-request → logout →
rejected-request sequence against the real database and confirm each transition in the
lifecycle above happens exactly once and in order — see `quickstart.md`.
