import { BarChart3, Building2, Calendar, ClipboardList, Mail, Ticket, UserX } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { SignalType } from './types'

// specs/016-dashboard-mockup-v2-refinement, data-model.md, research.md
// Decision 1 — the backend passes `event_type` through raw (mirroring how
// `severity` already works); the frontend owns this closed, 7-entry
// type->display map. No fallback branch is needed for an "unknown" 8th
// value since SignalType's union type makes that unrepresentable at compile
// time (P10 — no speculative extensibility for a category the product
// doesn't have).
export const TYPE_LABEL: Record<SignalType, string> = {
  message: 'Message',
  ticket_state_change: 'Ticket',
  usage_measurement: 'Activity',
  survey_response: 'Survey',
  meeting: 'Meeting',
  absence: 'Absence',
  crm_change: 'CRM Update',
}

export const TYPE_ICON: Record<SignalType, LucideIcon> = {
  message: Mail,
  ticket_state_change: Ticket,
  usage_measurement: BarChart3,
  survey_response: ClipboardList,
  meeting: Calendar,
  absence: UserX,
  crm_change: Building2,
}
