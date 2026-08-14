# Quickstart: Validating Dashboard Shell

Prerequisites: the stack from feature 001 running (`docker compose up --build`, then
seeded — see `specs/001-project-foundation/quickstart.md`). Demo credentials for this
feature: username `marta`, password `agentic-demo-2026` (a local/demo-only credential,
never treated as a secret — `research.md` §Decision: Regenerating the seeded demo
password hash).

## 1. Login and logout (User Story 1)

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "$TOKEN"
```

**Expected**: a non-empty token string.

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"wrong"}'
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"nobody","password":"wrong"}'
```

**Expected**: identical `401` bodies for both (`contracts/auth.md`).

```bash
for i in 1 2 3; do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" -d '{"username":"marta","password":"wrong"}'
done
```

**Expected**: the third response is `429`, not `401` (`REQ-AUTH-09`).

```bash
curl -s -X POST http://localhost:8000/auth/logout -H "Authorization: Bearer $TOKEN"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/dashboard \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**: logout returns `204`; the same token immediately returns `401` on the next
request (`REQ-AUTH-06`).

## 2. Dashboard shell (User Story 2)

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/dashboard
```

**Expected**: `401` — no token, no data (`contracts/auth.md`).

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s http://localhost:8000/api/dashboard -H "Authorization: Bearer $TOKEN"
```

**Expected**: `{"client_header":{"client_name":"Meridian Logistics"},"state":"learning","learning_message":"Still learning — 0 of 6 signal types available."}`
(`contracts/dashboard.md`) — no score, no contribution bars, no fabricated data anywhere.

## 3. Frontend, end to end

```bash
open http://localhost:5173   # or your browser of choice
```

**Expected**: a login form; on success, redirected to `/dashboard` showing "Meridian
Logistics" and the Learning-state message; closing and reopening the tab keeps you
logged in (token persisted in `localStorage`); an expired/revoked token bounces you back
to `/login`.

## Automated coverage

```bash
docker compose exec api pytest tests/unit/test_auth.py tests/unit/test_dashboard_route.py -v
docker compose exec web pnpm test        # Vitest — login form, protected-route redirect
docker compose exec web pnpm test:e2e    # Playwright — login-to-dashboard.spec.ts
```
