import { AlertTriangle, FileText } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { StudySourceState } from '@/types'

interface StudySourceStatusProps {
  source: StudySourceState
  className?: string
}

/** Shows which document produced a saved study set and whether it still matches. */
export function StudySourceStatus({ source, className }: StudySourceStatusProps) {
  const unavailable = !source.source_available
  const warning = unavailable || source.source_changed
  const deleted = source.source_status === 'deleted'

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <Badge variant="muted" className="max-w-full">
        <FileText className="size-3.5 shrink-0" />
        <span className="truncate">{source.source_label}</span>
      </Badge>
      {warning && (
        <Badge
          variant="warning"
          title={
            deleted
              ? 'The source document was removed. This saved set is still available.'
              : unavailable
                ? 'The source document is not currently available.'
                : 'The source document changed after this set was generated.'
          }
        >
          <AlertTriangle className="size-3.5 shrink-0" />
          {deleted
            ? 'Source deleted'
            : source.source_changed
              ? 'Source changed'
              : `Source ${source.source_status}`}
        </Badge>
      )}
    </div>
  )
}
