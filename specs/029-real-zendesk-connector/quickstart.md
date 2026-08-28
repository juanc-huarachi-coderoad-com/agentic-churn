# Quickstart: Real Zendesk Connector

## Prerequisites

- A Zendesk account with an API token (Admin Center → Apps and integrations → APIs → Zendesk API
  → Add API token), and the agent email that will authenticate.
- `ZENDESK_SUBDOMAIN`, `ZENDESK_AGENT_EMAIL`, `ZENDESK_API_TOKEN` set in `backend/.env` — no
  interactive consent flow needed (unlike Gmail), since Zendesk uses static API-token auth.

## Setup

1. No migration needed — no schema change.
2. `docker compose exec worker python -m app.worker --run-once zendesk` runs one collection cycle
   immediately.

## Validation

**Story 1 (real ticket activity becomes real signals)**:
1. Create a ticket in the connected Zendesk account within the last 24 hours (or use an existing
   recent one).
2. Run `--run-once zendesk` (or wait for the scheduled interval).
3. Confirm via `GET /api/coverage` that `zendesk` shows connected with a recent
   `last_successful_sync_at`, and that a `created` event now exists in the ledger for that ticket.
4. Resolve the ticket, run the connector again, confirm a `resolved` event appears.
5. Reopen the ticket, run again, confirm a `reopened` event appears — distinct from the original
   `created` event.
6. Run the same cycle again with no new activity — confirm no duplicate events (SC-002).

**Story 2 (simulated sources are unaffected)**:
1. With the real Zendesk connector present and configured, run `scripts/run_collector.py --source
   simulated` exactly as documented before this feature.
2. Confirm identical output to before this feature existed.
3. Run `tests/unit/test_simulated_collector.py` unchanged — confirm it still passes with zero
   modification.

**Story 3 (a connection failure is visible)**:
1. Temporarily set `ZENDESK_API_TOKEN` to an invalid value and run `--run-once zendesk`.
2. Confirm the run fails visibly (a coverage gap for `zendesk`, logged), not a silent
   zero-events success.
3. Restore the valid token and confirm a subsequent run succeeds normally.

**Multiple reopenings (FR-012/SC-005)**:
1. Within one connector run's window, resolve and reopen the same ticket twice.
2. Confirm two distinct `reopened` events exist for that ticket, not one collapsed event.

## Expected outcome

Real ticket creation/reopening/resolution becomes real, correctly-typed, citable ledger events on
Zendesk's own schedule, with zero duplicate collection; every existing simulated-source flow
(including `SimulatedCollector`'s own `zendesk` fixture items) continues to work completely
unmodified; a real connection problem is always visibly distinguishable from a healthy, quiet
account.
