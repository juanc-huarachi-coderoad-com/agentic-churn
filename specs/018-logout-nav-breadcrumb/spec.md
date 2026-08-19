# Feature Specification: Sidebar Logout, Nav Tooltips & Breadcrumb Trail

**Feature Branch**: `018-logout-nav-breadcrumb`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Adicionar la funcionalidad de cerrar sesion el boton deberia estar en la parte inferior izquierda como se define el @base/mockup-mainPage-v2.jpg, al hacer click sobre el icono-boton abre un menu de opciones comun, y la opcion cerrar sesion. Para la navegabilidad Adicionar un tooltip elegante en las tres opciones del menu principal, y se debe poder disinguir la opción seleccionada en el menu principal. Adicionar el componente de navegabilidad en cada vista, usa el estilo definido en @base/mockup-client-profile.jpg, este componente muestra el home > Client profile, guiate en el mockup, el estilo y el icono , y en cada vista el icono de acuerdo a la pagina, aplicar este componente en cada vista."

## Clarifications

### Session 2026-08-19

- Q: What should the account menu (opened from the bottom-left icon-button) contain besides "Log out"? → A: "Log out" only — no other options, since no other account-level action exists in the product yet.
- Q: What should the account icon-button itself look like, given the mockup shows a photo avatar with an online-status dot but the app has no user-identity data (name/photo) today? → A: A generic account/user icon (e.g., a person silhouette) — no photo, no online-status dot.
- Q: What should the breadcrumb trail show when the user is on the Home/default screen itself? → A: Show only "Home" (with its icon), not a link, since the user is already there — no second, duplicate segment.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign out from the account menu (Priority: P1)

A signed-in user wants to end their session. They locate an account icon-button anchored at the bottom-left of the main sidebar, click it, and see a small menu of common account options that includes "Log out." Selecting it ends their session and returns them to the login screen.

**Why this priority**: Logging out is a basic account-control expectation and a security requirement (users must be able to end a session on a shared or public device). It is currently entirely absent from the product, so it is the highest-value, highest-risk gap being closed by this feature.

**Independent Test**: Can be fully tested by clicking the account icon-button in the bottom-left of the sidebar from any authenticated screen, choosing "Log out" from the menu that appears, and verifying the session ends and the user lands on the login screen.

**Acceptance Scenarios**:

1. **Given** a user is signed in and viewing any screen, **When** they click the account icon-button at the bottom-left of the sidebar, **Then** a menu opens, anchored near the button, containing exactly one option: "Log out."
2. **Given** the account menu is open, **When** the user clicks "Log out," **Then** their session ends and they are taken to the login screen.
3. **Given** the account menu is open, **When** the user clicks anywhere outside the menu (or presses Escape), **Then** the menu closes without ending the session.
4. **Given** a user has just logged out, **When** they use the browser's back button, **Then** they are not able to view previously authenticated screens without signing in again.

---

### User Story 2 - Recognize the current section in the main menu (Priority: P2)

A user scanning the sidebar's three main navigation icons wants to know what each one leads to before clicking, and wants to be able to tell at a glance which section they are currently viewing.

**Why this priority**: The main navigation is icon-only today with no visible labels, so first-time or infrequent users cannot identify destinations without trial and error, and no icon is visually marked as "current," making orientation harder. This is a usability gap on every screen but does not block any workflow outright, so it ranks below logout.

**Independent Test**: Can be fully tested by hovering each of the three main menu icons and confirming a label tooltip appears for each, then navigating to each destination and confirming its icon is visually distinguished as selected while the others are not.

**Acceptance Scenarios**:

1. **Given** a user rests their pointer over any of the three main menu icons, **When** the pointer stays for a brief moment, **Then** a tooltip appears showing that destination's name, positioned so it doesn't obscure the icon, and it disappears when the pointer moves away.
2. **Given** a user is on one of the three main destinations, **When** they look at the sidebar, **Then** the icon for the current destination is visually distinguished (e.g., highlighted) from the other two, and this cannot be told by color alone.
3. **Given** a user navigates from one main destination to another, **When** the new screen finishes loading, **Then** the "selected" styling moves to the new destination's icon and no longer appears on the previous one.
4. **Given** a keyboard-only user tabs to a main menu icon, **When** the icon receives focus, **Then** the same label information available in the hover tooltip is available to them (not hover-only).

---

### User Story 3 - See a consistent location trail on every screen (Priority: P3)

A user on any screen of the application wants a small, consistent trail near the top of the content area showing where they are — starting with Home and ending with the current screen's name — matching the pattern already used on the Client Profile screen, so they always have a consistent orientation cue and, on nested screens, a way back to Home.

**Why this priority**: This is a consistency and orientation improvement that applies to every screen but is lower-impact than logout or main-menu clarity, since users can already navigate via the sidebar; the breadcrumb is a supporting cue, not the only path.

**Independent Test**: Can be fully tested by opening each screen in the application and verifying it shows a breadcrumb trail starting with a Home icon/link, followed by the current screen's name preceded by an icon appropriate to that screen, styled consistently with the existing Client Profile screen's trail.

**Acceptance Scenarios**:

1. **Given** a user opens any screen in the application, **When** the screen loads, **Then** a breadcrumb trail appears near the top of the content area, starting with a Home icon and ending with the current screen's name and its own icon.
2. **Given** a user is viewing the breadcrumb trail on a screen, **When** they click the "Home" segment, **Then** they are taken to the application's home/default screen.
3. **Given** a user views the breadcrumb trail on two different screens, **When** they compare the icon shown next to the current screen's name, **Then** each screen shows an icon specific to that screen (not a generic or repeated icon across unrelated screens).
4. **Given** a user is already on the home/default screen, **When** they view the breadcrumb trail, **Then** it shows only "Home" (with its icon) as a non-clickable label — no second segment repeating the same destination.

### Edge Cases

- What happens if the user clicks "Log out" while a form on the current screen has unsaved changes? (Assumption: no unsaved-change guard exists elsewhere in the app today, so logout proceeds without a confirmation prompt — see Assumptions.)
- What happens if the account menu is opened and the user resizes the window or the sidebar is very short (menu has no room to open upward)? The menu must reposition so it stays fully visible rather than being clipped off-screen.
- What happens if a screen's name is long and would visually crowd the breadcrumb trail on narrow window widths? The trail must truncate or wrap gracefully rather than overlapping other content.
- On the Home/default screen itself, the breadcrumb shows only "Home" as a non-clickable label — never a second, duplicate segment (Clarification, 2026-08-19).
- What happens if a user is mid-session and their authentication expires — does clicking the account icon or "Log out" behave the same as an intentional logout? Yes, it should still safely land them on the login screen.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display an account icon-button anchored at the bottom-left of the main sidebar on every authenticated screen, using a generic account/user icon (no user photo and no online-status indicator, since the product does not hold that data today).
- **FR-002**: Clicking the account icon-button MUST open a menu whose only option is "Log out."
- **FR-003**: Selecting "Log out" MUST end the user's session and navigate them to the login screen.
- **FR-004**: After logging out, the system MUST prevent access to previously authenticated screens (e.g., via browser back navigation) without re-authenticating.
- **FR-005**: The account menu MUST close without ending the session when the user clicks outside it or presses Escape.
- **FR-006**: The main sidebar's three navigation destinations MUST each show a tooltip with that destination's name on hover and on keyboard focus.
- **FR-007**: The tooltip MUST appear after a brief, consistent delay and disappear when the pointer/focus moves away, without obstructing the icon it describes.
- **FR-008**: The main sidebar MUST visually distinguish the icon for the destination currently being viewed from the other destinations, using a cue that does not rely on color alone.
- **FR-009**: The "selected" indicator in the main sidebar MUST update immediately whenever the user navigates to a different main destination.
- **FR-010**: Every screen in the application MUST display a breadcrumb trail near the top of its content area, starting with a Home icon/link and ending with the current screen's name — except the Home/default screen itself, whose breadcrumb trail MUST show only "Home" as a single, non-clickable label.
- **FR-011**: The current-screen segment of the breadcrumb trail MUST be preceded by an icon specific to that screen; different screens MUST NOT share a generic, identical icon.
- **FR-012**: The breadcrumb trail's Home segment MUST navigate to the application's home/default screen when clicked, except when the user is already on that screen, where it MUST render as a non-clickable label instead.
- **FR-013**: The breadcrumb trail's visual style (typography, spacing, separators, icon treatment) MUST be consistent with the pattern already established on the Client Profile screen across all other screens.
- **FR-014**: The breadcrumb trail MUST degrade gracefully (truncate or wrap) on narrow window widths without overlapping other page content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A signed-in user can locate and complete logout (icon click through session end) in 2 clicks or fewer, from any screen in the application.
- **SC-002**: 100% of the application's authenticated screens display both the bottom-left account icon-button and a breadcrumb trail.
- **SC-003**: In an unmoderated usability check, users correctly identify the destination of each of the three main menu icons (via tooltip) and correctly identify which one is currently active, without prior explanation, on their first attempt.
- **SC-004**: Every screen's breadcrumb trail displays a screen-specific icon that a user can distinguish from every other screen's icon (no two distinct screens show the same icon next to their name).
- **SC-005**: After logging out, 0% of attempts to view a previously authenticated screen via back navigation succeed without re-authentication.

## Assumptions

- The "three options in the main menu" referenced by the request are the application's existing three primary destinations (Dashboard, Coverage, and Profile); no new destination is being added by this feature.
- "Home" in the breadcrumb trail refers to the application's default landing screen (currently Dashboard), matching how "Home" is used in the Client Profile mockup's trail.
- The account menu contains only "Log out" (Clarification, 2026-08-19) — no other account-level action exists in the product today, and none is introduced by this feature.
- No confirmation dialog is required before logging out; ending the session is treated as a low-risk, easily-reversible (re-login) action, consistent with common product patterns.
- Session termination on logout is a front-end/session-scope concern (clearing the active session so protected screens are inaccessible); this feature does not define new backend session-invalidation infrastructure beyond what the application's existing authentication already provides.
- Tooltip and "selected" styling apply to the three main sidebar destinations; they do not extend to the bottom-left account icon-button, which has its own click-to-open menu instead of a navigation tooltip.
