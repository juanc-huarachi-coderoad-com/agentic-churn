# Quickstart: Real Gmail Connector

## Prerequisites

- A Google Cloud project with the Gmail API enabled, an OAuth consent screen configured (scope
  `https://www.googleapis.com/auth/gmail.readonly`, the operator's own account added as a test
  user), and a "Desktop app" OAuth 2.0 Client ID — `GMAIL_CLIENT_ID`/`GMAIL_CLIENT_SECRET` in
  `backend/.env`.
- A refresh token, obtained by running `scripts/generate_gmail_token.py` once locally (opens a
  browser, the operator approves access, the script prints/saves `GMAIL_REFRESH_TOKEN` to add to
  `.env`) — this step needs a real, interactive login and cannot be automated.

## Setup

1. `uv run python scripts/generate_gmail_token.py` — one-time, run by a human with access to the
   Gmail account being connected. Follow the printed URL, approve access, paste the resulting code
   back if prompted. Add the printed `GMAIL_REFRESH_TOKEN` line to `backend/.env`.
2. No migration needed — no schema change.
3. `docker compose exec worker python -m app.worker --run-once gmail` runs one collection cycle
   immediately.

## Validation

**Story 1 (real emails become real signals)**:
1. Ensure the connected mailbox has at least one email from within the last 24 hours (or wait for
   a new one to arrive).
2. Run `--run-once gmail` (or wait for the scheduled interval).
3. Confirm via `GET /api/coverage` that `gmail` shows connected with a recent
   `last_successful_sync_at`, and via `GET /api/dashboard`/the ledger that the email is now a real,
   citable event.
4. Run the same cycle again with no new mail — confirm no duplicate event (SC-002).

**Story 2 (simulated sources are unaffected)**:
1. With the real Gmail connector present and configured, run `scripts/run_collector.py --source
   simulated` exactly as documented before this feature.
2. Confirm identical output to before this feature existed — same envelope count, same fixture
   items collected, including its own simulated `gmail`-sourced items.
3. Run `tests/unit/test_simulated_collector.py` unchanged — confirm it still passes with zero
   modification.

**Story 3 (a connection failure is visible)**:
1. Temporarily set `GMAIL_REFRESH_TOKEN` to an invalid value and run `--run-once gmail`.
2. Confirm the run fails visibly (a coverage gap for `gmail`, logged), not a silent zero-events
   success indistinguishable from a quiet mailbox.
3. Restore the valid token and confirm a subsequent run succeeds normally.

## Expected outcome

Real email becomes real, citable ledger events on Gmail's own schedule, with zero duplicate
collection across runs; every existing simulated-source flow (including `SimulatedCollector`'s own
`gmail` fixture items) continues to work completely unmodified; a real connection problem is always
visibly distinguishable from a healthy, quiet mailbox.
