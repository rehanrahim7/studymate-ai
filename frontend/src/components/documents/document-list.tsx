import { FileText, MoreHorizontal, Trash2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { useDocuments } from '@/hooks/use-documents'
import { formatBytes, formatRelativeTime } from '@/lib/format'
import type { DocumentStatus } from '@/types'

const STATUS_BADGE: Record<
  DocumentStatus,
  { label: string; variant: 'success' | 'default' | 'muted' | 'destructive' }
> = {
  ready: { label: 'Indexed', variant: 'success' },
  processing: { label: 'Processing', variant: 'default' },
  pending: { label: 'Pending', variant: 'muted' },
  failed: { label: 'Failed', variant: 'destructive' },
}

export function DocumentList() {
  const { documents, isLoading, remove } = useDocuments()

  if (isLoading) {
    return (
      <ul className="divide-y divide-border/70">
        {[0, 1, 2].map((index) => (
          <li key={index} className="flex items-center gap-3 py-3.5">
            <Skeleton className="size-9 shrink-0 rounded-lg" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-3.5 w-2/5" />
              <Skeleton className="h-3 w-1/4" />
            </div>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <ul className="divide-y divide-border/70">
      {documents.map((document) => {
        const badge = STATUS_BADGE[document.status] ?? STATUS_BADGE.pending
        return (
          <li
            key={document.id}
            className="group flex items-center gap-3 py-3.5 transition-colors"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-secondary/70 text-muted-foreground">
              <FileText className="size-4" />
            </span>

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium" title={document.original_filename}>
                {document.original_filename}
              </p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {document.page_count} page{document.page_count === 1 ? '' : 's'} ·{' '}
                {document.chunk_count} chunks · {formatBytes(document.file_size)} ·{' '}
                {formatRelativeTime(document.created_at)}
              </p>
            </div>

            <Badge variant={badge.variant} className="hidden shrink-0 sm:inline-flex">
              {badge.label}
            </Badge>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="shrink-0 text-muted-foreground opacity-60 transition-opacity group-hover:opacity-100"
                  aria-label={`Actions for ${document.original_filename}`}
                >
                  <MoreHorizontal className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel className="truncate normal-case tracking-normal">
                  {document.original_filename}
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onSelect={() => {
                    void remove(document.id).catch(() => undefined)
                  }}
                  className="text-destructive focus:bg-destructive/10 focus:text-destructive [&_svg]:text-destructive"
                >
                  <Trash2 className="size-4" />
                  Delete document
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </li>
        )
      })}
    </ul>
  )
}
