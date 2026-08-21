# Manual Test Plan — Meeting Audio Ingestion (local storage + Whisper + pyannote.ai)

Companion to `INSTALL.md` (the Wara demo). This walks through the **real**
audio→transcript path (`specs/019-meeting-audio-ingestion`) — local storage
discovery, OpenAI Whisper transcription, pyannote.ai hosted-API diarization
— against a local `demo/meeting-audio/` folder, layered on top of the Wara
demo's already-loaded profile (stakeholders `stk_juan` / `stk_fernando`).

It follows the same four user stories as the feature's own
`specs/019-meeting-audio-ingestion/quickstart.md`, expanded with concrete
values from this environment (Wara stakeholder names, existing API keys).
Treat `quickstart.md` as the canonical spec-kit source of truth if the two
ever disagree.

**2026-08-20 revision**: this feature's audio source moved from Google Drive
to local storage (installation friction — Drive's OAuth/app-registration
setup was too heavy for a demo). Every Drive-specific step below is gone;
setup is now two commands, verified end-to-end while writing this revision.

---

## Current state in this environment

| Prerequisite | Status |
|---|---|
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | ✅ set in `.env` |
| `PYANNOTEAI_API_KEY` (pyannote.ai hosted diarization) | ✅ set in `.env` |
| Local storage root (`demo/meeting-audio/`) | No setup needed — just create a subfolder and drop a file in |
| Docker image | Needs a rebuild after this revision to drop the removed `google-api-python-client`/`google-auth` dependencies |

Everything on the code side (Whisper adapter, pyannote.ai adapter, the
local storage client, the consent/refresh endpoints, `worker.py --run-once
audio`) is already implemented and unit-tested. There is no setup gap left
— local storage needs no credential, no account, and no one-time grant.

---

## Step 0 — One-time local storage setup (30 seconds)

1. Create one subfolder per test meeting series under `demo/meeting-audio/`
   — **the subfolder's name is the `series_id`**, matched literally against
   whatever string you grant consent for later (e.g. `wara-weekly-sync`).
2. Drop one short test audio file into it:
   ```bash
   mkdir -p demo/meeting-audio/wara-weekly-sync
   cp demo-wara/wara-weekly-sync-recovery.m4a demo/meeting-audio/wara-weekly-sync/
   ```
   This lands inside the `./demo` directory both `api` and `worker` already
   mount read-only (`docker-compose.yml`) — no compose or mount change, no
   container restart needed to pick up a new recording, since the file is
   only ever read at collection time.
3. Bring up the stack (rebuild picks up the removed Drive dependencies and
   the new `local_storage_client.py`):
   ```bash
   docker compose up -d --build
   ```
4. For speaker attribution to actually resolve, have the recording mention
   **"Juan Huarachi"** and/or **"Fernando Juarez"** by name (or have them
   self-introduce) — those are the two stakeholder names in the
   currently-loaded Wara profile (`demo-wara/wara-profile.yaml`) that
   speaker-matching tries to match against. Include a clear verbal
   commitment ("we'll have the integration live by Friday") so the Meeting
   reader has something to extract.

That's the entire setup — no OAuth client, no Cloud Console project, no
token file, no interactive grant.

---

## Step 1 — User Story 2: consent gate (validate first — it blocks everything else)

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 1. Confirm no consent decision exists yet
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/meeting-audio/consent

# 2. Run a cycle with no consent — the recording must never be read/transcribed
docker compose exec worker python -m app.worker --run-once audio
docker compose exec -T db psql -U postgres -d agentic_churn -c \
  "SELECT count(*) FROM raw_envelopes WHERE source_native_id = 'wara-weekly-sync/wara-weekly-sync-recovery.m4a';"
# Expected: 0 — proves the structural gate (FR-003), not just a convention

# 3. Grant consent
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"series_id":"wara-weekly-sync","status":"granted","all_parties_confirmed":true}' \
  http://localhost:8000/api/meeting-audio/consent   # expect 201

# 4. Confirm it shows granted
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/meeting-audio/consent

# 5. Negative case — a partial-party grant must be rejected, never persisted
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"series_id":"wara-weekly-sync","status":"granted","all_parties_confirmed":false}' \
  http://localhost:8000/api/meeting-audio/consent   # expect 422
```

`source_native_id` is the recording's path relative to `demo/meeting-audio/`
(`research.md` Decision 10/12) — e.g. `wara-weekly-sync/<filename>`, not an
opaque Drive file ID.

---

## Step 2 — User Story 1: real end-to-end ingestion

```bash
docker compose exec worker python -m app.worker --run-once audio
```

Check:
- `raw_envelopes` has a new row for the recording; `events` has a new row
  with `event_type = 'meeting'` and `structured_payload->>'series_id' =
  'wara-weekly-sync'`
- the source file is still sitting in `demo/meeting-audio/wara-weekly-sync/`
  untouched (local storage is read-only mounted and the collector never
  writes to or deletes it, `research.md` Decision 8) — only the in-memory/
  temp copy made during transcription is discarded, no lingering audio
  anywhere beyond that (FR-008/SC-004)
- readers pick up the new event:
  ```bash
  docker compose exec api python scripts/run_readers.py
  ```
  → a `meeting_commitment` finding appears, citing the new event
- score reflects it:
  ```bash
  docker compose exec worker python -m app.worker --run-once score
  ```
- **Idempotency**: re-run `--run-once audio` a second time with the same
  file still present in `demo/meeting-audio/` → **no new**
  `raw_envelopes`/`events` row (FR-011; confirmed live —
  `envelopes_emitted=0` on the second run, versus `1` on the first)

---

## Step 3 — User Story 3: on-demand refresh

Add a second recording to the same local storage folder, then:

```bash
cp <another-file>.m4a demo/meeting-audio/wara-weekly-sync/second-recording.m4a
curl -s -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/meeting-audio/refresh
```

Expect `200` with `transcribed: 1` in the response body itself (the
request completes before returning, no polling needed on your end).
Confirm the dashboard / evidence trace reflects it immediately, without
waiting for a scheduled cycle.

Call `refresh` again immediately with nothing new in local storage →
expect `200`, every count `0`, never an error (the explicit "nothing new"
outcome; confirmed live — `{"recordings_found":2,"transcribed":0,...}`).

---

## Step 4 — User Story 4: honest degradation

```bash
# Simulate an inaccessible local storage location
mv demo/meeting-audio demo/meeting-audio.bak

curl -s -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/meeting-audio/refresh
# Expect 200 with a `source_error` field present — not a 500, and not
# indistinguishable from "nothing new". Confirmed live:
# {"source_error":"Meeting audio storage location is not accessible: demo/meeting-audio"}

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/coverage
# Expect the `transcripts` source to show status "degraded" (confirmed live)

docker compose exec worker python -m app.worker --run-once score
# Expect the score unchanged from its prior value — frozen, not computed
# on incomplete evidence

# Restore the folder and confirm normal behavior resumes with no
# reconnection step of any kind — there is none to perform (FR-001)
mv demo/meeting-audio.bak demo/meeting-audio
curl -s -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/meeting-audio/refresh
# Confirmed live: source_error becomes null, GET /api/coverage shows
# status "connected" again, immediately — no token to refresh, nothing to
# re-authorize.
```

---

## Step 5 — Confirm the pyannote.ai diarization path specifically

Diarization runs against the pyannote.ai hosted API rather than a local
pipeline, unaffected by this revision — worth checking beyond
`quickstart.md`'s own steps: after a successful `--run-once audio` run,
inspect the resulting meeting transcript text (decrypted event body, or the
evidence trace in the dashboard) and confirm segments are attributed to
`Juan Huarachi:` / `Fernando Juarez:` — or left unattributed if the match
genuinely wasn't confident, never a guessed name (FR-007). This proves
diarization → Whisper segment alignment → roster matching still works end
to end, not just that the code imports cleanly.

```bash
docker compose exec -T db psql -U postgres -d agentic_churn -c \
  "SELECT id, occurred_at FROM events WHERE event_type = 'meeting' ORDER BY occurred_at DESC LIMIT 1;"
# Then fetch that event's evidence via the dashboard or GET /api/evidence/{id}
# and read the transcript text directly.
```

---

## Troubleshooting

### `PyannoteAIFailedJob` / `HTTPError: Failed to authenticate to pyannoteAI API`
`PYANNOTEAI_API_KEY` is missing or invalid. Create/verify one at
https://dashboard.pyannote.ai/. This surfaces as a per-item failure
(FR-013) — the cycle continues, that one recording is skipped and logged.

### `LocalStorageAccessError` on the very first run
`demo/meeting-audio/` doesn't exist, isn't mounted into the container, or
isn't readable. Confirm `docker-compose.yml`'s `./demo:/app/demo:ro` mount
is present for both `api` and `worker`, and that
`settings.meeting_audio_storage_path` (default `./demo/meeting-audio`)
matches where you actually created the folder.

### A recording is silently never processed
Check the local storage subfolder's name exactly matches the `series_id`
you granted consent for (case-sensitive, exact string match —
`local_storage_client.py` uses the folder name as-is). A folder whose name
matches no known series is skipped and logged, never treated as implicitly
consented.

### Diarization succeeds but every segment is unattributed
Either the recording never says the stakeholder names clearly enough for
the LLM speaker-matching step to reach its confidence floor (0.7), or
`ANTHROPIC_API_KEY` is missing/invalid for that structured-output call —
check both before assuming diarization itself failed.

---

## Cleanup

```bash
# Revoke consent for the test series (new row, doesn't delete prior evidence)
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"series_id":"wara-weekly-sync","status":"revoked","all_parties_confirmed":true}' \
  http://localhost:8000/api/meeting-audio/consent

# Remove the test recordings from local storage once you're done, if desired
# — the collector never deletes them itself (research.md Decision 8)
rm demo/meeting-audio/wara-weekly-sync/second-recording.m4a
```

No code or fixture files are modified by this manual test — it only
exercises the already-implemented real-API path against live credentials
and a local folder.
