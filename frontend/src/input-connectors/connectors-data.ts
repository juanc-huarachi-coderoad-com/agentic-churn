import { AudioWaveform, CalendarDays, Cloud, FileSignature, Grid, Heart, MessageSquare, Smile, Users, Warehouse as WarehouseIcon } from 'lucide-react'
import type { Connector, ConnectorGroup, ConnectorStatus } from './types'

// data-model.md's fixed catalog: 1 Live + 6 Simulated + 7 Planned = 14 (spec FR-003–FR-005).
// Gmail/Zendesk/Jira/Intercom use real downloaded logos (research.md Decision 1 — the only
// four of the original eight brand names still in Simple Icons' actively-maintained CC0
// index; Slack/Microsoft 365/Teams/Salesforce were found delisted there, likely for a brand/
// trademark reason, so they render as tinted generic icons instead of a reproduced logo).
export const CONNECTORS: Connector[] = [
  {
    id: 'transcripts',
    name: 'Transcripts',
    status: 'live',
    description: 'Meeting audio',
    pipeline: ['local storage', 'OpenAI Whisper', 'pyannote.ai', 'Anthropic'],
    icon: { kind: 'lucide', icon: AudioWaveform, tintClassName: 'text-emerald-600' },
  },
  {
    id: 'gmail',
    name: 'Gmail',
    status: 'simulated',
    description: 'Email threads and client conversations',
    icon: { kind: 'brand', asset: 'gmail.svg', alt: 'Gmail logo' },
  },
  {
    id: 'zendesk',
    name: 'Zendesk',
    status: 'simulated',
    description: 'Support tickets and customer requests',
    icon: { kind: 'brand', asset: 'zendesk.svg', alt: 'Zendesk logo' },
  },
  {
    id: 'warehouse',
    name: 'Warehouse',
    status: 'simulated',
    description: 'Product usage and account activity',
    icon: { kind: 'lucide', icon: WarehouseIcon, tintClassName: 'text-blue-600' },
  },
  {
    id: 'slack',
    name: 'Slack',
    status: 'simulated',
    description: 'Shared Slack channel messages',
    icon: { kind: 'lucide', icon: MessageSquare, tintClassName: 'text-[#4A154B]' },
  },
  {
    id: 'csat',
    name: 'CSAT',
    status: 'simulated',
    description: 'Customer satisfaction survey responses',
    icon: { kind: 'lucide', icon: Smile, tintClassName: 'text-emerald-600' },
  },
  {
    id: 'calendar',
    name: 'Calendar',
    status: 'simulated',
    description: 'Meeting schedule and attendance',
    icon: { kind: 'lucide', icon: CalendarDays, tintClassName: 'text-blue-600' },
  },
  {
    id: 'jira',
    name: 'Jira',
    status: 'planned',
    description: 'Engineering tickets and issue tracking',
    icon: { kind: 'brand', asset: 'jira.svg', alt: 'Jira logo' },
  },
  {
    id: 'intercom',
    name: 'Intercom',
    status: 'planned',
    description: 'In-app messaging and support chat',
    icon: { kind: 'brand', asset: 'intercom.svg', alt: 'Intercom logo' },
  },
  {
    id: 'microsoft365',
    name: 'Microsoft 365',
    status: 'planned',
    description: 'Outlook email and Office document activity',
    icon: { kind: 'lucide', icon: Grid, tintClassName: 'text-[#EA3E23]' },
  },
  {
    id: 'teams',
    name: 'Teams',
    status: 'planned',
    description: 'Microsoft Teams chat and meetings',
    icon: { kind: 'lucide', icon: Users, tintClassName: 'text-[#6264A7]' },
  },
  {
    id: 'nps',
    name: 'NPS',
    status: 'planned',
    description: 'Net Promoter Score survey responses',
    icon: { kind: 'lucide', icon: Heart, tintClassName: 'text-red-500' },
  },
  {
    id: 'salesforce',
    name: 'Salesforce',
    status: 'planned',
    description: 'CRM records and account history',
    icon: { kind: 'lucide', icon: Cloud, tintClassName: 'text-[#00A1E0]' },
  },
  {
    id: 'contracts',
    name: 'Contracts',
    status: 'planned',
    description: 'Signed contracts and renewal terms',
    icon: { kind: 'lucide', icon: FileSignature, tintClassName: 'text-violet-600' },
  },
]

const GROUP_LABEL: Record<ConnectorStatus, string> = {
  live: 'Live',
  simulated: 'Simulated',
  planned: 'Planned',
}

const GROUP_ORDER: ConnectorStatus[] = ['live', 'simulated', 'planned']

// research.md Decision 3: derived from CONNECTORS, never a hand-typed count — a group's
// heading count can't drift from the list rendered beneath it.
export const CONNECTOR_GROUPS: ConnectorGroup[] = GROUP_ORDER.map((status) => ({
  status,
  label: GROUP_LABEL[status],
  connectors: CONNECTORS.filter((connector) => connector.status === status),
}))
