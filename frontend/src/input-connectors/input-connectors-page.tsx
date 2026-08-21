import { Plus } from 'lucide-react'
import { Icon } from '../components/ui/icon'
import { AppShell } from '../nav/app-shell'
import { ConnectorCard } from './connector-card'
import { CONNECTOR_GROUPS } from './connectors-data'

export function InputConnectorsPage() {
  return (
    <AppShell>
      <div className="lg:h-full lg:overflow-y-auto">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-medium text-neutral-900">Input Connectors</h1>
            <p className="mt-1 text-sm text-neutral-500">
              Manage and configure the data sources that power insights and analysis.
            </p>
          </div>
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Icon icon={Plus} size={16} aria-hidden />
            Add Connector
          </button>
        </div>

        <div className="mt-8 space-y-10">
          {CONNECTOR_GROUPS.map((group) => (
            <section key={group.status}>
              <h2 className="text-sm font-medium text-neutral-700">
                {group.label} ({group.connectors.length})
              </h2>

              {group.status === 'live' ? (
                <div className="mt-3 space-y-3">
                  {group.connectors.map((connector) => (
                    <ConnectorCard key={connector.id} connector={connector} variant="row" />
                  ))}
                </div>
              ) : (
                <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
                  {group.connectors.map((connector) => (
                    <ConnectorCard key={connector.id} connector={connector} variant="tile" />
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      </div>
    </AppShell>
  )
}
