# Contracts: Sidebar Logout, Nav Tooltips & Breadcrumb Trail

This feature adds **no new API surface**. It is frontend-only and consumes one pre-existing,
already-documented, already-tested endpoint:

- **`POST /auth/logout`** — see `specs/002-dashboard-shell/contracts/auth.md` for the full
  contract (bearer-token auth, idempotent revocation, `204` response,
  `backend/app/auth/adapters/router.py` implementation, `backend/tests/unit/test_auth.py`
  coverage). This plan's `research.md` Decision 3 documents *how* the frontend now calls it
  (best-effort, non-blocking); the contract itself is unchanged and out of scope to restate
  here.

No other backend routes are read, written, or modified by this feature — the breadcrumb and
tooltip/active-state work are purely client-side rendering of the existing route table
(`frontend/src/App.tsx`) and the existing `Sidebar` destination list.
