# Phase 1 Data Model: Sidebar Logout, Nav Tooltips & Breadcrumb Trail

This feature introduces no persisted/database entities and no new backend schema — it is a
frontend navigation-chrome feature that reuses the existing token-based session (`users`,
`auth_tokens` — unchanged) via the existing `POST /auth/logout` endpoint. The only "data" is
frontend configuration/UI state, captured below for the components that consume it
(`research.md` Decisions 5–7).

## Destination (config, not persisted)

Source of truth: `frontend/src/nav/destinations.ts` (research.md Decision 6).

| Field | Type | Notes |
|---|---|---|
| `to` | route path string | One of `/dashboard`, `/coverage`, `/profile` — fixed, matches `App.tsx`'s existing routes. |
| `label` | string | Human-readable destination name (`"Dashboard"`, `"Coverage"`, `"Profile"`), shown in the sidebar tooltip and as the breadcrumb's trailing segment text. |
| `icon` | `LucideIcon` | Existing icons — `LayoutGrid`, `Radar`, `UserRound` — one per destination, never shared across two destinations (FR-011). |

This is the same shape as the array already defined inline in `sidebar.tsx` today (see
`frontend/src/nav/sidebar.tsx` lines 16–20) — Decision 6 only moves it to its own module so
`Breadcrumb` can import it too; no field changes.

## Breadcrumb trail (derived UI state, not persisted)

Computed per render from the current route (`useLocation()` from `react-router`) plus the
`Destination` registry above and one fixed constant:

| Segment | Icon | Label | Behavior |
|---|---|---|---|
| Home (fixed) | `lucide-react` `Home` | `"Home"` | Links to `/dashboard` — *unless* the current route already is `/dashboard`, in which case it renders as a non-clickable label and is the **only** segment shown (research.md Decision 7; FR-010/FR-012). |
| Current screen (derived) | The matching `Destination.icon` | The matching `Destination.label` | Rendered only when the current route is not `/dashboard`; never clickable (it's the current screen). |

No new client-side store (Zustand) or server state (TanStack Query) is needed — this is pure
render-time derivation from `useLocation().pathname`, matching P11's "state lives as close to
its owner as possible" (no global state for something computable from the URL on every
render).

## Logout action (no new entity)

The logout flow (research.md Decision 3) touches only the existing `useAuthStore` shape
(`frontend/src/auth/auth-store.ts` — `token`, `isAuthenticated`, `login`, `logout`, unchanged)
and the existing backend `AuthToken` revocation already implemented by `LogoutUseCase`
(`backend/app/auth/application/use_cases.py`). No new fields, no new table, no new frontend
store slice.
