import type { LucideIcon } from 'lucide-react'

import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  hint?: string
  icon: LucideIcon
  /** Highlights the tile with a soft indigo wash. */
  emphasis?: boolean
}

export function StatCard({ label, value, hint, icon: Icon, emphasis = false }: StatCardProps) {
  return (
    <Card
      className={cn(
        'group relative overflow-hidden p-5 transition-colors hover:border-primary/25',
        emphasis && 'bg-gradient-to-br from-primary-soft to-card dark:from-primary-soft/60',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
          {hint && <p className="mt-1 truncate text-xs text-muted-foreground">{hint}</p>}
        </div>
        <span
          className={cn(
            'flex size-9 shrink-0 items-center justify-center rounded-lg border transition-colors',
            emphasis
              ? 'border-primary/20 bg-primary/10 text-primary'
              : 'border-border bg-secondary/70 text-muted-foreground group-hover:text-foreground',
          )}
        >
          <Icon className="size-4" />
        </span>
      </div>
    </Card>
  )
}
