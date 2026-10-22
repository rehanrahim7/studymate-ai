import { Cpu, RefreshCw } from 'lucide-react'

import { StatusDot, type StatusTone } from '@/components/ui/status-dot'
import { useHealth } from '@/hooks/use-health'
import { cn } from '@/lib/utils'

/**
 * Live status of the local LLM engine.
 *
 * Everything shown here comes from the real `/health` endpoint — nothing is
 * simulated.
 */
export function EngineStatusCard() {
  const { health, isLoading, error, refresh } = useHealth()

  let tone: StatusTone = 'neutral'
  let title = 'Checking engine…'
  let detail = 'Contacting the local API'

  if (error) {
    tone = 'danger'
    title = 'API offline'
    detail = 'Start the FastAPI backend'
  } else if (health) {
    if (health.llm === 'ready') {
      tone = 'success'
      title = 'Engine ready'
      detail = 'Local model available'
    } else {
      tone = 'warning'
      title = 'Model not running'
      detail = 'Start Ollama to enable AI'
    }
  } else if (!isLoading) {
    tone = 'warning'
    title = 'Engine unknown'
    detail = 'No response from the API'
  }

  return (
    <button
      type="button"
      onClick={() => void refresh()}
      className={cn(
        'group flex w-full items-center gap-3 rounded-lg border border-sidebar-border bg-sidebar-accent/40 p-3 text-left transition-colors hover:bg-sidebar-accent/70',
      )}
    >
      <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-sidebar-border bg-sidebar text-sidebar-muted">
        <Cpu className="size-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5 text-xs font-semibold text-sidebar-foreground">
          <StatusDot tone={tone} pulse={tone === 'success'} />
          {title}
        </span>
        <span className="mt-0.5 block truncate text-[0.6875rem] text-sidebar-muted">
          {detail}
        </span>
      </span>
      <RefreshCw
        className="size-3.5 shrink-0 text-sidebar-muted opacity-0 transition-opacity group-hover:opacity-100"
        aria-hidden
      />
    </button>
  )
}
