import { useMemo } from 'react'
import { Check, FileText, Lock } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { DocumentSummary } from '@/types'

interface DocumentSelectorProps {
  documents: DocumentSummary[]
  selectedIds: number[]
  onToggle: (id: number) => void
  onSelectAll: () => void
  onClear: () => void
  disabled?: boolean
}

/**
 * Lets the user scope a question to specific documents.
 *
 * Only indexed documents can be selected — anything still processing or failed
 * is shown as unavailable rather than silently ignored.
 */
export function DocumentSelector({
  documents,
  selectedIds,
  onToggle,
  onSelectAll,
  onClear,
  disabled,
}: DocumentSelectorProps) {
  const selectedSet = useMemo(
    () => new Set(selectedIds.map((id) => Number(id))),
    [selectedIds],
  )
  const selectable = useMemo(
    () => documents.filter((document) => document.status === 'ready'),
    [documents],
  )
  const allSelected = selectable.length > 0 && selectedIds.length === selectable.length

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">
            Documents
          </p>
          <Badge variant={selectedIds.length > 0 ? 'default' : 'muted'} className="tabular-nums">
            {selectedIds.length} selected
          </Badge>
        </div>
        <Button
          variant="ghost"
          size="sm"
          disabled={disabled || selectable.length === 0}
          onClick={allSelected ? onClear : onSelectAll}
          className="h-7 px-2 text-xs"
        >
          {allSelected ? 'Clear' : 'Select all'}
        </Button>
      </div>

      <ul className="scrollbar-subtle -mx-1 max-h-64 space-y-1 overflow-y-auto px-1">
        {documents.map((document) => {
          const isReady = document.status === 'ready'
          const docId = Number(document.id)
          const isSelected = selectedSet.has(docId)
          const isDisabled = disabled || !isReady

          return (
            <li key={document.id}>
              <button
                type="button"
                disabled={isDisabled}
                aria-pressed={isSelected}
                onClick={() => onToggle(docId)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors',
                  isSelected
                    ? 'border-primary/40 bg-primary-soft'
                    : 'border-border bg-card hover:bg-secondary/50',
                  isDisabled && 'cursor-not-allowed opacity-55 hover:bg-card',
                )}
              >
                <span
                  className={cn(
                    'flex size-5 shrink-0 items-center justify-center rounded-md border transition-colors',
                    isSelected
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border bg-card',
                  )}
                >
                  {isSelected && <Check className="size-3.5" strokeWidth={3} />}
                </span>

                <span className="flex min-w-0 flex-1 items-center gap-2">
                  <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[0.8125rem] font-medium">
                      {document.original_filename}
                    </span>
                    <span className="block truncate text-[0.6875rem] text-muted-foreground">
                      {isReady
                        ? `${document.page_count} page${document.page_count === 1 ? '' : 's'}`
                        : document.status === 'failed'
                          ? 'Indexing failed'
                          : 'Still processing…'}
                    </span>
                  </span>
                </span>

                {!isReady && (
                  <span className="flex shrink-0 items-center gap-1 text-[0.625rem] font-medium uppercase tracking-wide text-muted-foreground">
                    <Lock className="size-3" />
                    {document.status}
                  </span>
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
