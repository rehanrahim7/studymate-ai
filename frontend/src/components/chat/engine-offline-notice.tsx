import { AlertTriangle, RefreshCw, Server } from 'lucide-react'

import { Button } from '@/components/ui/button'

interface EngineOfflineNoticeProps {
  onRetry: () => void
  isRetrying?: boolean
}

/**
 * Shown when `/health` reports the local LLM engine is unreachable.
 *
 * The app is honest about this: without the model, no answer can be generated,
 * so the chat is disabled and the exact commands to fix it are shown.
 */
export function EngineOfflineNotice({ onRetry, isRetrying }: EngineOfflineNoticeProps) {
  return (
    <div className="flex flex-col items-center gap-5 px-4 py-10 text-center">
      <span className="flex size-12 items-center justify-center rounded-xl border border-warning/25 bg-warning/12 text-warning shadow-subtle">
        <Server className="size-5" />
      </span>

      <div className="max-w-md">
        <p className="text-sm font-medium">The local AI engine is offline</p>
        <p className="mt-1 text-pretty text-[0.8125rem] leading-relaxed text-muted-foreground">
          StudyMate generates answers with a local <strong className="font-medium">Ollama</strong>{' '}
          model — nothing is sent to a third party. Start it to enable chat:
        </p>
      </div>

      <div className="w-full max-w-md space-y-2 rounded-lg border border-border bg-secondary/40 p-4 text-left">
        <div className="flex items-center gap-2 text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">
          <AlertTriangle className="size-3.5" />
          Run these in your terminal
        </div>
        <pre className="scrollbar-subtle overflow-x-auto rounded-md bg-card p-3 font-mono text-xs leading-relaxed text-foreground">
          <code>{'ollama serve\nollama pull llama3.1:8b'}</code>
        </pre>
        <p className="text-[0.6875rem] leading-relaxed text-muted-foreground">
          Then come back and retry. Your documents are already indexed — only answer
          generation needs the model.
        </p>
      </div>

      <Button variant="outline" onClick={onRetry} disabled={isRetrying}>
        <RefreshCw className={isRetrying ? 'animate-spin' : undefined} />
        Check again
      </Button>
    </div>
  )
}
