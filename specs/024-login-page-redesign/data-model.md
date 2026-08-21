# Phase 1 Data Model: Login Page Redesign

This feature introduces **no new entities, fields, or database changes**. It is a
presentation- and interaction-layer redesign of an existing page; the data shapes it works
with already exist and are unchanged.

## Existing shapes (unchanged)

- **`LoginFormValues`** (`frontend/src/auth/login-page.tsx`, Zod-inferred): `{ username:
  string; password: string }`. Validation rules unchanged: both fields required
  (`"Username is required"`, `"Password is required"`).
- **`LoginResponse`** (`frontend/src/auth/login-page.tsx`): `{ token: string; expires_at:
  string }`, returned by the existing `POST /auth/login` endpoint
  (`specs/002-dashboard-shell/contracts/auth.md`, unchanged by this feature).

## New local UI state (not persisted, not an entity)

- **`passwordVisible`** — a component-local `boolean` (`useState`) owned by the login page,
  controlling whether the password `<input>`'s `type` is `"password"` or `"text"`. This is
  transient UI state, reset on every mount; it is never sent to the server, never persisted,
  and does not participate in form validation or submission.

## State transitions

None beyond what already exists today: `idle → submitting → (redirect on success | root
error shown)`. This feature adds no new states — only new *visual* representations of the
existing ones (e.g. a styled banner instead of a bare paragraph for the root error), plus the
purely presentational `passwordVisible` toggle described above.
