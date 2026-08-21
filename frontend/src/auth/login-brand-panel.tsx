import type { CSSProperties } from 'react'

const ORB_COLOR = '#ec7c43'

const orbGradient: CSSProperties = {
  background: `radial-gradient(circle at 38% 32%, color-mix(in srgb, ${ORB_COLOR} 30%, white), ${ORB_COLOR} 58%, color-mix(in srgb, ${ORB_COLOR} 65%, black) 100%)`,
}

interface LoginBrandPanelProps {
  /** Compact orb+wordmark lockup shown above the form on narrow viewports. */
  compact?: boolean
}

// The AURA brand moment for the login screen — same glossy-sphere technique as
// dashboard/aura-risk-orb.tsx (Tailwind classes for shape/layout, inline `style` only for the
// computed gradient/shadow color-mix can't express as static classes), reusing the shared
// `animate-aura-pulse` utility (index.css) rather than a second keyframe definition
// (specs/024-login-page-redesign/research.md Decision 4). Unlike AuraRiskOrb, this orb's
// color is a fixed brand color, not a risk-band signal — a distinct component on purpose.
export function LoginBrandPanel({ compact = false }: LoginBrandPanelProps) {
  if (compact) {
    return (
      <div className="mb-7 flex items-center gap-2.5 lg:hidden">
        <div
          aria-hidden="true"
          className="h-7 w-7 shrink-0 rounded-full"
          style={{ ...orbGradient, boxShadow: `0 0 14px -3px ${ORB_COLOR}` }}
        />
        <span className="text-base font-semibold tracking-wide text-neutral-900">AURA</span>
      </div>
    )
  }

  return (
    <div className="relative hidden shrink-0 items-center justify-center overflow-hidden bg-neutral-950 p-12 lg:flex lg:w-5/12">
      <div
        aria-hidden="true"
        className="absolute inset-0"
        style={{
          backgroundImage: 'radial-gradient(rgba(255,255,255,0.06) 1px, transparent 1px)',
          backgroundSize: '28px 28px',
          maskImage: 'radial-gradient(circle at 50% 42%, black, transparent 72%)',
          WebkitMaskImage: 'radial-gradient(circle at 50% 42%, black, transparent 72%)',
        }}
      />

      <div className="relative flex max-w-sm flex-col items-center gap-7 text-center">
        <div className="relative flex h-40 w-40 items-center justify-center" aria-hidden="true">
          <div
            className="absolute inset-[-20%] rounded-full blur-2xl"
            style={{ background: `radial-gradient(circle, ${ORB_COLOR} 0%, transparent 68%)`, opacity: 0.4 }}
          />
          <div
            className="relative h-full w-full rounded-full motion-safe:animate-aura-pulse"
            style={{ ...orbGradient, boxShadow: `0 0 60px -8px ${ORB_COLOR}` }}
          />
        </div>

        <div className="text-xs font-semibold tracking-[0.16em] text-white/40 uppercase">
          Churn Prediction &amp; Sentiment Agent
        </div>
        <h2 className="-mt-3 text-3xl font-semibold tracking-[0.08em] text-neutral-50">AURA</h2>
        <p className="text-sm leading-relaxed text-white/60 italic">
          &ldquo;The signals were always there, scattered across six systems and six people.
          This is the thing that reads them on Tuesday, instead of at the renewal.&rdquo;
        </p>
      </div>
    </div>
  )
}
