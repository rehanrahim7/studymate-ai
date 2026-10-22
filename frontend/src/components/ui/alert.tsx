import { AlertCircle, X } from 'lucide-react'

import { cn } from '@/lib/utils'

interface AlertProps {
  title?: string
  description?: string
  onDismiss?: () => void
  className?: string
}

/** Inline error / information banner. */
export function Alert({ title, description, onDismiss, className }: AlertProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-3 rounded-lg border border-destructive/25 bg-destructive/[0.06] px-4 py-3 text-sm',
        className,
      )}
    >
      <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-medium text-destructive">{title}</p>}
        {description && (
          <p className="text-pretty text-[0.8125rem] text-destructive/90">{description}</p>
        )}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded-md p-1 text-destructive/70 transition-colors hover:bg-destructive/10 hover:text-destructive"
          aria-label="Dismiss"
        >
          <X className="size-3.5" />
        </button>
      )}
    </div>
  )
}
