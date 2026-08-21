# Phase 0 Research: Login Page Redesign

No `[NEEDS CLARIFICATION]` markers remain in `spec.md`; the research below resolves the
translation decisions needed to take the approved design reference (a `.dc.html` design-canvas
prototype, necessarily built with plain CSS and hand-drawn SVGs since that tool has no access
to this app's real stack) into code that complies with this repository's constitution.

## Decision 1: Treat the design canvas as a visual reference to translate, not markup to port

**Decision**: Re-implement the approved design's visual result (two-panel layout, AURA orb hero,
icon-led inputs, banners, spacing, color palette) directly in `login-page.tsx` using this app's
real primitives. Do not copy the canvas's `<style>` block or inline SVGs into the codebase.

**Rationale**: The design-canvas tool (`design` skill) runs each artboard as a sandboxed,
dependency-free HTML fragment — it cannot import Tailwind, React components, or
`lucide-react`, so its CSS and icons were necessarily hand-rolled. Full-Stack Engineering §2
("UI & Styling") explicitly prohibits standard CSS and non-`lucide-react` icon libraries in
this codebase without approval. Porting the prototype's raw markup verbatim would violate
that rule; translating its visual result does not.

**Alternatives considered**: Copy the `.dc.html` file's CSS/SVGs as-is and wrap them in a
React component — rejected, directly violates the closed UI/icon-library rule and creates a
second, parallel styling system alongside Tailwind.

## Decision 2: Keep React Hook Form + Zod; add only local UI state for password visibility

**Decision**: The existing `loginSchema` (Zod) and the `useForm` call already in
`login-page.tsx` are unchanged. The only new client state is a component-local
`useState<boolean>` for whether the password field is masked.

**Rationale**: P11 and Full-Stack Engineering §2 mandate React Hook Form + Zod for all forms.
The canvas prototype used a hand-rolled class-based state object (`state.username`,
`state.password`, …) only because the design-canvas sandbox has no npm ecosystem to run RHF
in. The real page must keep using `register`/`handleSubmit`/`setError`, not reintroduce manual
controlled-input state that would duplicate what RHF already does correctly.

**Alternatives considered**: Mirror the canvas's manual state object in the real component —
rejected, duplicates RHF's job and violates P11's forms-and-validation rule.

## Decision 3: Icons via `lucide-react` through the existing `Icon` wrapper

**Decision**: Use `lucide-react`'s `User`, `Lock`, `Eye`, `EyeOff`, `TriangleAlert`, and
`CircleCheck` (or the closest equivalents already available in the installed `lucide-react`
version), rendered through the existing `components/ui/icon.tsx` wrapper — the same one
already used by the sidebar, account menu, and dashboard.

**Rationale**: Icons are a closed choice in this constitution (`lucide-react` only); the
`Icon` wrapper already fixes `strokeWidth={1.75}` and default sizing so every icon in the app
looks consistent. The canvas prototype drew inline stroke-based SVGs by hand only because
`lucide-react` isn't available inside a `.dc.html` sandbox.

**Alternatives considered**: Keep the canvas's hand-drawn inline SVGs — rejected, introduces a
second icon system the constitution explicitly disallows without approval.

## Decision 4: Recreate the AURA orb using the existing `AuraRiskOrb` pattern and animation

**Decision**: Build the brand panel's orb using the same technique as
`frontend/src/dashboard/aura-risk-orb.tsx` — Tailwind utility classes for shape/layout, an
inline `style` prop only for the computed radial-gradient/box-shadow (which cannot be
expressed as static Tailwind classes since the color is a variable), and the existing
`motion-safe:animate-aura-pulse` Tailwind utility (already defined once, in
`frontend/src/index.css`, per `specs/020-aura-orb-heartbeat`) for the pulse — no new
`@keyframes` block.

**Rationale**: This is the exact precedent already established in this codebase for "a
glossy, glowing orb that pulses slowly." Reusing it keeps the pulse animation defined in
exactly one place and keeps the login page visually and technically consistent with the
dashboard's own orb, rather than inventing a second, slightly different implementation.

**Alternatives considered**: A new `<style>` block with its own `@keyframes aura-pulse` (what
the canvas prototype did, necessarily, since it can't reference `index.css`) — rejected once
inside the real codebase, since it would duplicate the single source of truth
`specs/020-aura-orb-heartbeat` already established.

## Decision 5: Use the codebase's existing `lg:` breakpoint for the panel collapse

**Decision**: The two-panel-to-single-column collapse happens at Tailwind's standard `lg`
breakpoint (1024px, e.g. `hidden lg:flex` / `lg:hidden`), not the canvas prototype's ad-hoc
880px custom media query.

**Rationale**: `AppShell` (`frontend/src/nav/app-shell.tsx`) already switches its own layout
(sidebar beside vs. above content) at exactly this breakpoint (`flex-col lg:flex-row`). Using
the same breakpoint keeps the one other layout-collapse decision in this app consistent,
rather than introducing a second, differently-tuned breakpoint for the same kind of decision.
The visual difference between 880px and 1024px is not meaningful to the design's intent (which
was simply "collapse before the two panels get cramped").

**Alternatives considered**: Keep the canvas's exact 880px breakpoint via an arbitrary Tailwind
value (`max-[880px]:hidden`) — rejected, no functional benefit over the existing convention,
and introduces a one-off breakpoint value nowhere else in the app.

## Decision 6: Update the one e2e assertion whose expected copy intentionally changes

**Decision**: `frontend/e2e/login-to-dashboard.spec.ts`'s first test currently asserts
`page.getByRole('heading', { name: 'Log in' })`. The approved design's heading copy is
"Welcome back" (with "Log in" preserved as the submit button's label). This test's heading
assertion is updated to `'Welcome back'` as part of this feature; every other assertion in
that file — `getByLabel('Username')`, `getByLabel('Password')`, `getByRole('button', { name:
'Log in' })`, and the exact error text `'Invalid username or password.'` — is preserved
unchanged, because the redesign keeps those labels and that copy identical.

**Rationale**: Full-Stack Engineering §4 requires e2e coverage of business-critical flows to
keep passing; an intentional, user-approved copy change to page-level heading text is a
legitimate, in-scope reason to update the one assertion that pins that exact text, not a
regression to work around. Silently changing the heading text back to "Log in" just to dodge
a test edit would undercut the approved design without being asked to.

**Alternatives considered**: Keep the literal string "Log in" as the `<h1>` instead of
"Welcome back" so no test changes are needed — rejected; the user explicitly approved the
design as published, and the heading copy is part of that approval, not an incidental detail.

## Decision 7: Add component-level tests for the login page

**Decision**: Add `frontend/src/auth/login-page.test.tsx` (new file) covering: empty-field
validation errors, the invalid-credentials error banner, the success path, the password
show/hide toggle, and `aria-invalid`/error-association wiring — using Testing Library, in the
style of the existing `protected-route.test.tsx` in the same folder.

**Rationale**: Full-Stack Engineering §4 requires component-level tests for rendering/
interaction logic, distinct from e2e coverage of the full user journey. The login page
currently has zero test coverage of any kind below the e2e layer; this feature is the natural
point to close that gap for the logic it's adding (the visibility toggle, the richer error/
success states).

**Alternatives considered**: Rely solely on the existing e2e suite — rejected; e2e tests are
slower and more expensive to run for interaction-level assertions like a visibility toggle,
and the constitution's testing hierarchy calls for both layers.
