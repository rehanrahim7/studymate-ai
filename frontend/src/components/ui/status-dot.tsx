import { cn } from '@/lib/utils'

export type StatusTone = 'success' | 'warning' | 'danger' | 'neutral'

const TONE_CLASSES: Record<StatusTone, string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-destructive',
  neutral: 'bg-muted-foreground/50',
}

interface StatusDotProps {
  tone: StatusTone
  /** Adds a soft pulsing halo — used for live/connected states. */
  pulse?: boolean
  className?: string
}

/** A small coloured dot used to communicate service status. */
export function StatusDot({ tone, pulse = false, className }: StatusDotProps) {
  return (
    <span className={cn('relative flex size-2', className)}>
      {pulse && (
        <span
          className={cn(
            'absolute inline-flex size-full animate-ping rounded-full opacity-60',
            TONE_CLASSES[tone],
          )}
        />
      )}
      <span
        className={cn('relative inline-flex size-2 rounded-full', TONE_CLASSES[tone])}
      />
    </span>
  )
}
