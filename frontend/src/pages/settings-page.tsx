import { Database, Palette, RefreshCw, Server } from 'lucide-react'

import { ThemeSegmentedControl } from '@/components/theme/theme-segmented-control'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { StatusDot, type StatusTone } from '@/components/ui/status-dot'
import { useHealth } from '@/hooks/use-health'
import { API_BASE_URL } from '@/lib/api'

function Row({ label, value, tone }: { label: string; value: string; tone?: StatusTone }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <span className="text-[0.8125rem] text-muted-foreground">{label}</span>
      <span className="flex items-center gap-2 text-[0.8125rem] font-medium">
        {tone && <StatusDot tone={tone} />}
        {value}
      </span>
    </div>
  )
}

export function SettingsPage() {
  const { health, isLoading, error, refresh } = useHealth()

  const databaseTone: StatusTone =
    health?.database === 'connected' ? 'success' : health ? 'danger' : 'neutral'
  const llmTone: StatusTone =
    health?.llm === 'ready' ? 'success' : health ? 'warning' : 'neutral'

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2.5">
              <span className="flex size-8 items-center justify-center rounded-lg border border-border bg-secondary/70 text-muted-foreground">
                <Palette className="size-4" />
              </span>
              <div className="flex flex-col gap-1">
                <CardTitle>Appearance</CardTitle>
                <CardDescription>
                  Choose how StudyMate looks. “System” follows your operating system.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ThemeSegmentedControl />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2.5">
              <span className="flex size-8 items-center justify-center rounded-lg border border-border bg-secondary/70 text-muted-foreground">
                <Server className="size-4" />
              </span>
              <div className="flex flex-col gap-1">
                <CardTitle>Backend</CardTitle>
                <CardDescription>Live status reported by the FastAPI service.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {error ? (
              <div className="rounded-lg border border-destructive/25 bg-destructive/[0.06] p-4">
                <p className="text-sm font-medium text-destructive">API unreachable</p>
                <p className="mt-1 text-pretty text-[0.8125rem] text-destructive/90">{error}</p>
              </div>
            ) : (
              <div className="divide-y divide-border/70">
                <Row label="API base URL" value={API_BASE_URL} />
                <Row label="Version" value={health?.version ?? '—'} />
                <Row label="Environment" value={health?.environment ?? '—'} />
                <Row
                  label="Database"
                  value={isLoading ? 'Checking…' : (health?.database ?? 'unavailable')}
                  tone={databaseTone}
                />
                <Row
                  label="LLM engine"
                  value={
                    isLoading
                      ? 'Checking…'
                      : health?.llm === 'ready'
                        ? 'Ollama ready'
                        : 'Ollama unreachable'
                  }
                  tone={llmTone}
                />
              </div>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button variant="outline" size="sm" onClick={() => void refresh()}>
                <RefreshCw className="size-4" />
                Refresh status
              </Button>
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Database className="size-3.5" />
                Documents are stored in a local SQLite database.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
