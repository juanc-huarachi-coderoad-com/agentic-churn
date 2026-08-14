# Quickstart: Validating Ingestion and Context

Prerequisites: the stack from features 001–002 running and seeded, plus an encryption
key file (`research.md` §Decision: Message-body encryption):

```bash
mkdir -p secrets
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > secrets/data.key
docker compose up --build -d   # picks up the new ./secrets mount
```

## 1. Client profile versioning (User Story 1)

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s -X POST http://localhost:8000/api/profile/reload -H "Authorization: Bearer $TOKEN"
```

**Expected**: `200`, a new `client_profile_versions` row with a higher `version_number`
than the seeded one, `is_current = true`; the prior version's `is_current` is now
`false` (verify via `docker compose exec db psql ... -c "SELECT version_number,
is_current FROM client_profile_versions ORDER BY version_number;"`).

```bash
# Corrupt the on-disk profile (remove the only signs_renewal: true stakeholder), retry
curl -s -w "\nHTTP:%{http_code}\n" -X POST http://localhost:8000/api/profile/reload \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: `422`, a specific field-level error, no new version created (`REQ-M3-07`).

## 2. Event ledger (User Story 2)

```bash
docker compose exec api pytest tests/unit/test_hash_chain.py tests/unit/test_business_hours.py -v
```

**Expected**: hash-chain round trip passes (Python-computed hash matches the DB's
`verify_hash_chain()`), and business-hours arithmetic matches `data-model.md`'s worked
numbers exactly (19.0h `open_overdue` for #456, 2.0h `resolved` for #398).

## 3. Signal collection (User Story 3)

```bash
docker compose exec api python scripts/run_collector.py --source simulated
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT event_type, occurred_at FROM events ORDER BY occurred_at;"
```

**Expected**: 6 new events (one per fixture item, `data-model.md`), matching
`demo/fixtures/meridian-week.json`'s timestamps.

```bash
# Run again — must be a no-op
docker compose exec api python scripts/run_collector.py --source simulated
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT duplicates_skipped FROM collector_runs ORDER BY started_at DESC LIMIT 1;"
```

**Expected**: `duplicates_skipped = 6`, zero new `events` rows (`REQ-M1-03`,
`REQ-NFR-27`).

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT source_identifier, resolved_by FROM identity_map;"
```

**Expected**: Ana's Gmail address resolves (`exact_match`); the Zendesk reporter address
does not (`unresolved`) — matching `examples/01` §4.3.

## 4. Absence detection (User Story 4)

```bash
docker compose exec api pytest tests/unit/test_absence_collector.py -v
```

**Expected**: a commitment with an unmet cadence produces an `absence` event; one with a
just-satisfied cadence produces none.

## Automated coverage

```bash
docker compose exec api pytest tests/unit/ -v
docker compose exec api lint-imports --config ../.importlinter
```
