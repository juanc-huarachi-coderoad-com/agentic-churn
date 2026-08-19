# Quickstart: Sidebar Logout, Nav Tooltips & Breadcrumb Trail

## Prerequisites

- Backend and frontend running per the repo's existing dev setup (`docker compose up`, or
  `backend/` + `frontend/` run separately per their own READMEs).
- A valid login (whatever seed/demo user the local environment already uses to reach
  `/dashboard` today).

## Automated checks

```bash
cd frontend
pnpm test          # Vitest — AccountMenu, Sidebar (tooltip/active-state), Breadcrumb, AppShell, use-logout
pnpm typecheck
pnpm lint
pnpm test:e2e       # Playwright — includes the new end-to-end logout scenario
```

## Manual validation scenarios

These map directly to `spec.md`'s Acceptance Scenarios.

### 1. Logout (User Story 1)

1. Log in and land on `/dashboard`.
2. Click the account icon-button at the bottom-left of the sidebar.
   - **Expect**: a menu opens near the button containing exactly one item, "Log out."
3. Click outside the open menu.
   - **Expect**: the menu closes; you're still logged in (still on `/dashboard`).
4. Re-open the menu and press `Escape`.
   - **Expect**: same as above — closes, session unaffected.
5. Re-open the menu and click "Log out."
   - **Expect**: you land on `/login`. (Check the network tab: a `POST /auth/logout` request
     fired before the redirect.)
6. Press the browser's back button.
   - **Expect**: you are not shown `/dashboard`, `/coverage`, or `/profile` content — you're
     redirected back to `/login` (via `ProtectedRoute`).

### 2. Main-menu tooltips and active state (User Story 2)

1. From `/dashboard`, hover each of the three sidebar icons in turn (without clicking).
   - **Expect**: each shows a tooltip with its destination name (Dashboard/Coverage/Profile)
     after a brief pause, and the tooltip disappears when you move the pointer away.
2. Tab through the sidebar with the keyboard only (no mouse).
   - **Expect**: the same label information appears on focus, not just on hover.
3. Note which icon is visually marked as "current" on `/dashboard`. Click "Coverage."
   - **Expect**: the "current" marking moves to the Coverage icon and leaves the Dashboard
     icon; the marking is visible as more than just a color swap (e.g., an accent bar), and
     inspecting the DOM shows `aria-current="page"` on the active link.

### 3. Breadcrumb trail (User Story 3)

1. On `/dashboard` (Home), look at the top of the content area.
   - **Expect**: the breadcrumb shows only "Home" (with its house icon), not a link, and no
     second segment.
2. Navigate to `/coverage`.
   - **Expect**: breadcrumb reads "Home > Coverage" with Coverage's own icon (matching its
     sidebar icon); clicking "Home" returns you to `/dashboard`.
3. Navigate to `/profile` (the Client Profile screen).
   - **Expect**: breadcrumb reads "Home > Profile" (or the exact label used in
     `destinations.ts`), styled consistently with `base/mockup-client-profile.jpg` — same
     typography/spacing/separator treatment as Coverage's breadcrumb, just a different icon
     and label.
4. Resize the browser window narrow.
   - **Expect**: the breadcrumb truncates or wraps without overlapping other page content.

## Success criteria cross-check

- SC-001: step "1.5" above completes logout in 2 clicks (icon + "Log out").
- SC-002: repeat step "3.1"–"3.3" on all three screens — every one shows both the account
  icon-button and a breadcrumb.
- SC-003: an unmoderated peer can name each destination from its tooltip and identify the
  active one without being told.
- SC-004: Dashboard/Coverage/Profile each show a visually distinct breadcrumb icon.
- SC-005: step "1.6" — back navigation after logout never reveals protected content.
