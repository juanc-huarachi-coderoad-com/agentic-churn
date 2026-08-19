# Phase 0 Research: Sidebar Logout, Nav Tooltips & Breadcrumb Trail

All items below were resolvable from the existing codebase and constitution — no
`NEEDS CLARIFICATION` markers remain in the Technical Context.

## Decision 1: Tooltip primitive

**Decision**: Add `@radix-ui/react-tooltip` and wrap it in `components/ui/tooltip.tsx`,
matching `components/ui/dialog.tsx`'s existing wrapper shape (a thin, typed pass-through
around the Radix primitive with the project's own styling classes).

**Rationale**: The constitution (Full-Stack §2 "UI & Styling") closes icon/component-library
choices to Radix-based shadcn/ui; `@radix-ui/react-dialog` is already a direct dependency
using exactly this wrapper pattern, so Tooltip should follow the same precedent rather than a
hand-rolled `onMouseEnter`/`setTimeout` implementation (which would also have to
re-implement keyboard-focus visibility, positioning-away-from-viewport-edge, and
Escape-dismiss by hand — Radix Tooltip provides all three).

**Alternatives considered**:
- Native `title` attribute — rejected: no styling control ("elegant tooltip" per the
  request), inconsistent cross-browser delay/positioning, not keyboard-focus-visible in all
  browsers.
- Hand-rolled `useState` + `onMouseEnter`/`onFocus` tooltip — rejected: reinvents
  positioning/collision/Escape/focus behavior that Radix already provides, against P10
  (don't build what you'd otherwise buy for free) and against the closed component-library
  rule.

## Decision 2: Account menu primitive

**Decision**: Add `@radix-ui/react-dropdown-menu` and wrap it in
`components/ui/dropdown-menu.tsx`, same pattern as Decision 1.

**Rationale**: FR-005 requires the menu to close on outside-click or Escape without ending
the session — this is Radix DropdownMenu's default behavior, not something to reimplement.
It also gets a focus trap and correct ARIA roles (`menu`/`menuitem`) for free, satisfying
constitution P11's accessibility bullet.

**Alternatives considered**:
- Reusing the existing `Dialog` primitive styled as a small popover — rejected: Dialog is a
  centered, backdrop-modal pattern (`dialog.tsx`'s own comment: "centered layout,
  backdrop-dismissible"); an anchored corner menu needs Popper-based positioning relative to
  the trigger button, which is `DropdownMenu`'s (and `Popover`'s) job, not `Dialog`'s.
- `@radix-ui/react-popover` + hand-built menu semantics — rejected: `DropdownMenu` already
  layers correct menu/menuitem ARIA roles and keyboard nav (arrow keys, typeahead) on top of
  the same positioning primitive Popover uses, so it is the closer-fitting primitive for "a
  menu of options," not a generic floating panel.

## Decision 3: What the "Log out" action actually does

**Decision**: The intentional "Log out" click performs a best-effort
`POST /auth/logout` (the existing, already-implemented and already-tested backend endpoint,
`backend/app/auth/adapters/router.py` + `LogoutUseCase`) using the current bearer token,
*then* clears local state via the existing `useAuthStore.logout()`, then navigates to
`/login`. The network call is best-effort: if it fails (offline, timeout), the UI still
clears local state and navigates — the client-side clear is what actually removes the user's
access to protected screens (FR-004), so it must never be blocked on the network call
succeeding.

**Rationale**: The backend already implements real server-side token revocation
(`backend/tests/unit/test_auth.py`'s
`test_logout_revokes_token_and_get_current_user_rejects_it_on_next_use`) and the constitution
requires "Zero Trust Validation" (Full-Stack §5) — a token that's merely forgotten
client-side but never revoked server-side would still be a valid bearer token if it leaked
(e.g., through a proxy log) before its natural expiry. An intentional "Log out" click is the
one moment the product can cheaply close that window, and the endpoint to do it already
exists and is already covered by tests — using it is not new backend scope, just wiring an
existing capability into a UI that never called it before.

**Alternatives considered**:
- Local-only clear (what the existing 401-interceptor path in `api-client.ts` already does)
  — rejected as the *only* behavior for the intentional action: appropriate for "token
  already invalid" (nothing to revoke), wrong for "user chose to end a valid session" (token
  is still live and should be revoked, not just forgotten).
- Blocking the redirect until the network call resolves — rejected: makes logout hang or
  fail on a flaky/offline connection for a purely client-side, already-reversible (re-login)
  action; contradicts the spec's Assumption that logout is treated as low-risk/reversible.

## Decision 4: Distinguishing the active main-menu item without color alone

**Decision**: Keep the existing `NavLink`/`isActive` mechanism in `sidebar.tsx`, and add (a)
`aria-current="page"` on the active link and (b) a visual cue that isn't purely a background
color swap — a left-edge accent bar (a filled rectangle, `border-l-2` equivalent) alongside
the existing background/text color change.

**Rationale**: FR-008 explicitly requires a cue that "does not rely on color alone"
(constitution P11 "Accessibility... Color MUST NOT be the only indicator of state"). A shape
change (bar presence/absence) plus `aria-current` covers both sighted users with color-vision
deficiency and screen-reader users, using only Tailwind classes already in the project's
vocabulary — no new dependency.

**Alternatives considered**:
- Background-color change only (today's actual behavior, `isActive && 'bg-neutral-100
  text-neutral-900'`) — rejected: this is exactly the color-only signal FR-008/P11
  prohibit.
- An animated underline/motion cue — rejected as unnecessary complexity (P10) for a static
  3-item sidebar; a static shape cue is sufficient and simpler to test.

## Decision 5: Shared navigation chrome across screens (AppShell)

**Decision**: Introduce one `AppShell` component in `frontend/src/nav/` that renders
`Sidebar` + `Breadcrumb` around its `children`, and have `DashboardPage`, `CoveragePage`, and
`ProfileEditorForm` each render through it instead of `DashboardPage` privately owning
`<Sidebar />` while the other two render bare `<main>` with no navigation chrome at all.

**Rationale**: FR-001 and FR-010 both say "every authenticated screen" — today that's false
for two of the three screens (`grep` confirmed only `dashboard-page.tsx` imports `Sidebar`;
`coverage-page.tsx` and `profile-editor-form.tsx` render a bare `<main>`). Without a shared
composition point, the bottom-left account menu and the breadcrumb would each need to be
copy-pasted into three page components, which is exactly the drift P10/P11 warn against
("shared code only for genuinely reusable logic"). An `AppShell` used inside each page
(rather than lifted to the `App.tsx` route table) is because each page already owns its own
loading/error early-returns (`if (isLoading) return <p>...`) — folding those into a
route-level wrapper would either lose the sidebar during a page's own loading/error state
(a regression: the account menu should stay reachable even while a page's data is loading) or
require every page's loading/error branch to duplicate the AppShell wrapper anyway, which is
the same amount of code as having each page call it directly.

**Alternatives considered**:
- Route-level wrapper in `App.tsx` (`<ProtectedRoute><AppShell><DashboardPage/></AppShell>
  </ProtectedRoute>`) — considered viable but rejected in favor of in-page composition,
  specifically so a page's own `isLoading`/`isError` early return still renders inside
  `AppShell` (sidebar/breadcrumb visible during loading, not just after data arrives) without
  every page needing to duplicate that early-return-wrapping logic.
- Copy the `<Sidebar />` + new `<Breadcrumb />` JSX into each of the three page components
  individually — rejected: the exact duplication P11 says shared code exists to avoid, and
  the mechanism by which Dashboard/Coverage/Profile's sidebars would silently drift apart
  over time.

## Decision 6: Single source of truth for destination icon/label

**Decision**: Extract the existing inline `DESTINATIONS` array out of `sidebar.tsx` into
`frontend/src/nav/destinations.ts`, and have both `Sidebar` (tooltips + active state) and
`Breadcrumb` (current-screen icon + name) import it.

**Rationale**: FR-011 requires each screen's breadcrumb icon to be specific to that screen
and never duplicated across screens; `Sidebar` already has exactly this
`{to, label, icon}` mapping for its three destinations (`LayoutGrid`/`Dashboard`,
`Radar`/`Coverage`, `UserRound`/`Profile`). Defining it once and importing it in both places
makes "different screens never share an icon" true by construction instead of by convention
that two files could quietly drift out of sync.

**Alternatives considered**:
- A second, breadcrumb-specific icon map — rejected: the exact drift risk FR-011 exists to
  prevent, and against P10 (don't build a second thing that already exists once, correctly).

## Decision 7: "Home" segment vs. the Dashboard destination

**Decision**: The breadcrumb's "Home" segment is a fixed concept (label "Home", `lucide-react`
`Home` icon, links to `/dashboard`) distinct from the trailing per-page segment. When the
current route *is* `/dashboard`, the breadcrumb renders only that fixed "Home" segment as a
non-clickable label (FR-010/FR-012, per the 2026-08-19 clarification) — it does not also
render a second "Dashboard" segment using the `LayoutGrid` icon from Decision 6's registry.

**Rationale**: The Client Profile mockup shows "Home > Client profile" using a house icon for
Home, not the grid icon used elsewhere for the Dashboard destination — confirming Home is
its own fixed concept, not simply "the Dashboard destination's own icon/label reused."

**Alternatives considered**: None material — this follows directly from the mockup and the
already-resolved clarification.
