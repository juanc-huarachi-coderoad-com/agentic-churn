# Feature Specification: Login Page Redesign

**Feature Branch**: `024-login-page-redesign`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "the design is perfect now could you apply it in my application in the login page, please."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A branded, professional first impression (Priority: P1)

A CS lead opens the app for the first time in a session and lands on the login page. Instead of a bare, unstyled form, they see a polished screen that clearly identifies the product (AURA) and its purpose, giving the same level of visual polish as the dashboard they are about to use.

**Why this priority**: The login page is the first screen every user sees. Today it is a plain, unstyled form with no product identity — it undersells a product whose dashboard is highly polished. This is the core of the request.

**Independent Test**: Load the login route with no session token. Confirm the page shows the AURA brand treatment (orb, wordmark, tagline) alongside the sign-in form, and that the visual language (colors, borders, radii, button styles) matches the rest of the app (sidebar, cards, buttons).

**Acceptance Scenarios**:

1. **Given** a signed-out visitor on a desktop-width viewport, **When** they load the login route, **Then** they see a two-panel layout: a branded panel (AURA orb, product name, tagline) and a form panel with username/password fields.
2. **Given** a signed-out visitor on a narrow (mobile-width) viewport, **When** they load the login route, **Then** the branded panel is replaced by a compact logo lockup above the form, and the form remains fully usable without horizontal scrolling.

---

### User Story 2 - Familiar, working sign-in behavior (Priority: P1)

A user who already knows their username and password logs in exactly as before — same fields, same validation, same failure message — just presented with more polish.

**Why this priority**: The redesign must not change or break the existing, already-working authentication flow (client-side validation, API contract, error messaging, redirect on success). Regressing login would block every other feature in the app.

**Independent Test**: Attempt to log in with (a) empty fields, (b) a wrong username/password combination, and (c) valid credentials, using only the visible UI. Confirm each path behaves exactly as the current login page does today, just restyled.

**Acceptance Scenarios**:

1. **Given** the login form, **When** the user submits with both fields empty, **Then** inline errors "Username is required" and "Password is required" appear under the respective fields, and no request is sent.
2. **Given** the login form, **When** the user submits a username/password pair the backend rejects, **Then** a single error message "Invalid username or password." is shown, without revealing which field was wrong.
3. **Given** the login form, **When** the user submits valid credentials, **Then** the submit button shows a loading state ("Logging in…") until the request resolves, and the user is redirected to the dashboard on success.

---

### User Story 3 - Comfortable, accessible interaction (Priority: P2)

A user filling in the form gets clear visual feedback as they interact with it — focus states on fields, a way to reveal a mistyped password, and error states that are easy to notice — without needing perfect eyesight or a mouse.

**Why this priority**: Nice-to-have polish that improves usability but doesn't block the core login flow if delayed.

**Independent Test**: Tab through the form using only the keyboard, toggle password visibility, and confirm focus rings and error states are clearly visible and announced to assistive tech (via `aria-invalid` / `role="alert"`).

**Acceptance Scenarios**:

1. **Given** the password field, **When** the user clicks the visibility toggle, **Then** the password text is shown or hidden accordingly, with an accessible label reflecting the current action ("Show password" / "Hide password").
2. **Given** a field with a validation error, **When** the error is present, **Then** the field is marked `aria-invalid` and the error text is programmatically associated with it.

---

### Edge Cases

- What happens if the viewport is resized between desktop and mobile widths while the form has partially-entered data? The entered values MUST be preserved; only the layout changes.
- What happens if the user retries after a failed login? The previous error message MUST clear as soon as they start editing either field.
- What happens on very small viewports (e.g. 320px wide)? The form MUST remain fully visible and usable without horizontal scrolling or clipped controls.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The login page MUST present a two-panel layout on wide viewports: a branded panel (AURA orb graphic, product eyebrow label, "AURA" wordmark, and product tagline) and a form panel containing the sign-in form.
- **FR-002**: Below a defined width threshold, the branded panel MUST be replaced by a compact logo lockup (small orb + wordmark) shown above the form, and the form MUST take the full available width.
- **FR-003**: The form MUST continue to collect exactly the same fields as today (username, password) and submit them to the existing authentication endpoint, with no new fields (no email, SSO, "remember me", or "forgot password" affordances).
- **FR-004**: Client-side validation MUST use the same rules and messages as today ("Username is required", "Password is required"), shown inline beneath each field when triggered.
- **FR-005**: An authentication failure MUST show the existing single, generic error message ("Invalid username or password.") without indicating which field was incorrect.
- **FR-006**: The submit button MUST show a distinct loading state (disabled, "Logging in…") while the request is in flight, matching current behavior.
- **FR-007**: A successful login MUST continue to store the session token and redirect to the dashboard exactly as it does today.
- **FR-008**: The password field MUST offer a show/hide toggle that switches the field between masked and plain text.
- **FR-009**: Visual styling (colors, spacing, border radii, button and input treatments, icon style) MUST be drawn from the application's existing shared visual conventions (the same neutral color palette, control shapes, and component styling already used across the dashboard), not a new, unrelated design system.
- **FR-010**: Interactive elements MUST expose accessible state: invalid fields marked `aria-invalid`, error/status banners exposed via an appropriate live region role, and the password-visibility toggle exposing an accessible label describing its current action.
- **FR-011**: Any previously shown authentication error MUST clear as soon as the user edits either field.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On first load, users can identify the product name and purpose from the login screen alone (brand element and product name visible above the fold) without scrolling.
- **SC-002**: All three existing authentication outcomes (validation error, rejected credentials, successful login) behave identically to the pre-redesign page in 100% of manual test passes — no regression in the sign-in flow.
- **SC-003**: The login page renders without clipped, overlapping, or horizontally-scrolling content across viewport widths from 320px to 1920px.
- **SC-004**: Every interactive element on the page (both fields, the visibility toggle, the submit button) is reachable and operable using keyboard-only navigation.

## Assumptions

- The approved reference for this redesign is the "AURA Login" design canvas already reviewed and approved by the user in this project; this feature applies that visual design to the real, existing login page component rather than designing something new.
- The existing authentication contract (`POST /auth/login` with `username`/`password`, and the generic invalid-credentials message) is unchanged — this is a visual and interaction-polish redesign of the existing page, not a change to auth behavior or the API.
- No new account-recovery, SSO, or "remember me" functionality is in scope, since none exists in the current product today.
- The two-panel desktop layout collapses to a single-column layout below approximately 880px width, consistent with the approved design reference.
- Reduced-motion preferences are respected for any decorative animation (e.g. the orb's pulse), consistent with existing conventions elsewhere in the app.
