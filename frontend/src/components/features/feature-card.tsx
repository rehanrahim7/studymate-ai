import type { LucideIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface FeatureCardProps {
  title: string
  description: string
  icon: LucideIcon
  /** `planned` features are rendered as disabled with an honest badge. */
  status: 'available' | 'planned'
  footnote?: string
  onClick?: () => void
}

export function FeatureCard({
  title,
  description,
  icon: Icon,
  status,
  footnote,
  onClick,
}: FeatureCardProps) {
  const isPlanned = status === 'planned'

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      aria-disabled={!onClick}
      className={cn(
        'group relative flex w-full flex-col items-start gap-3 rounded-xl border border-border bg-card p-5 text-left shadow-card transition-all duration-200',
        onClick && 'hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-glow',
        isPlanned && 'opacity-80',
      )}
    >
      <div className="flex w-full items-start justify-between gap-3">
        <span
          className={cn(
            'flex size-10 items-center justify-center rounded-lg border transition-colors',
            isPlanned
              ? 'border-border bg-secondary/70 text-muted-foreground'
              : 'border-primary/20 bg-primary-soft text-primary',
          )}
        >
          <Icon className="size-[18px]" strokeWidth={1.9} />
        </span>
        {isPlanned ? (
          <Badge variant="muted" className="shrink-0 text-[0.625rem] uppercase tracking-wider">
            In development
          </Badge>
        ) : (
          <Badge variant="success" className="shrink-0 text-[0.625rem] uppercase tracking-wider">
            Ready
          </Badge>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
        <p className="mt-1 text-pretty text-[0.8125rem] leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>

      {footnote && (
        <p className="mt-auto pt-1 text-[0.6875rem] text-muted-foreground/80">{footnote}</p>
      )}
    </button>
  )
}
