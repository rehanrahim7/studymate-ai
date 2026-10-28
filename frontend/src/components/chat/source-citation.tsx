import { useState } from 'react'
import { ChevronDown, FileText } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { ChatSource } from '@/types'

interface SourceCitationProps {
  source: ChatSource
  index: number
}

/** A single retrieved passage: the real page text the model was allowed to use. */
export function SourceCitation({ source, index }: SourceCitationProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left transition-colors hover:bg-secondary/50"
      >
        <span className="flex size-6 shrink-0 items-center justify-center rounded-md border border-border bg-secondary text-[0.6875rem] font-semibold tabular-nums text-muted-foreground">
          {index + 1}
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-xs font-medium" title={source.document_name}>
            {source.document_name}
          </span>
          <span className="truncate text-[0.6875rem] text-muted-foreground">
            Page {source.page_number} · passage {source.ordinal + 1}
          </span>
        </span>
        <Badge variant="muted" className="hidden shrink-0 tabular-nums sm:inline-flex">
          {source.score >= 0.999 ? 'Overview' : `${Math.round(source.score * 100)}% match`}
        </Badge>
        <ChevronDown
          className={cn(
            'size-4 shrink-0 text-muted-foreground transition-transform',
            isOpen && 'rotate-180',
          )}
        />
      </button>

      {isOpen && (
        <div className="border-t border-border/70 bg-secondary/25 px-3 py-3">
          <div className="mb-2 flex items-center gap-1.5 text-[0.6875rem] font-medium uppercase tracking-wider text-muted-foreground">
            <FileText className="size-3" />
            Retrieved text
          </div>
          <p className="scrollbar-subtle max-h-56 overflow-y-auto whitespace-pre-wrap text-pretty text-xs leading-relaxed text-foreground/90">
            {source.text}
          </p>
        </div>
      )}
    </div>
  )
}
