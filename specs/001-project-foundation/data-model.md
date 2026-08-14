# Data Model: Project Foundation

## No new entities

This feature provisions the *container* for data — schema, migration history, seed data —
it does not introduce any new business entity. The full entity set (`events`, `findings`,
`score_runs`, `client_profile_versions`, and every other table) is already defined,
field-by-field, in `data-base/02-schema-ingestion.md` through `data-base/09-erd-full.md`,
with the runnable DDL in `data-base/10-ddl-appendix.md`. Restating any of it here would be
exactly the duplication this SDD rollout is structured to avoid (see `spec.md`'s scope
note).

## What this feature is responsible for

| Concern | Source of truth | This feature's job |
|---|---|---|
| Table shapes, columns, constraints | `data-base/10-ddl-appendix.md` | Import verbatim as the first Alembic revision (FR-002) |
| Seed rows (`finding_type_config`, playbook, Meridian demo profile, identity map) | `data-base/11-seed-data.sql` | Apply via a dedicated seed script, kept separate from schema migrations (FR-003) |
| `users` / `auth_tokens` tables | `data-base/12-users-and-auth.md` | Provisioned now (schema only — no auth *logic* yet) so every later "who did this" column can FK to `users.id` from the start (FR-009, `AGENTS.md`) |

## Validation

The acceptance test for this feature's data concern is structural equality, not new
business rules: `SELECT` against the freshly-migrated database's `information_schema`
and diff it against `data-base/10-ddl-appendix.md` — see `quickstart.md` for the runnable
version of this check, and spec.md's User Story 1 / Acceptance Scenario 2 for the
requirement it satisfies.
