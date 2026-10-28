import { BookOpenText, Sparkles, User } from 'lucide-react'

import { AnswerMarkdown } from '@/components/chat/answer-markdown'
import { SourceCitation } from '@/components/chat/source-citation'
import type { ChatMessage } from '@/components/chat/types'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface MessageBubbleProps {
  message: ChatMessage
}

/** A single conversation turn — user question or grounded assistant answer. */
export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end gap-3">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-[0.9375rem] leading-relaxed text-primary-foreground shadow-subtle">
          <p className="whitespace-pre-wrap text-pretty">{message.text}</p>
        </div>
        <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border border-border bg-secondary text-muted-foreground">
          <User className="size-3.5" />
        </span>
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      <span
        className={cn(
          'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border',
          message.isRefusal
            ? 'border-warning/25 bg-warning/12 text-warning'
            : 'border-primary/20 bg-primary-soft text-primary',
        )}
      >
        {message.isRefusal ? <BookOpenText className="size-3.5" /> : <Sparkles className="size-3.5" />}
      </span>

      <div className="min-w-0 flex-1 space-y-3">
        <div className="rounded-2xl rounded-tl-md border border-border bg-card px-4 py-3 shadow-card">
          <AnswerMarkdown text={message.text} />

          {message.sources.length > 0 && (
            <div className="mt-4 border-t border-border/70 pt-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">
                  Sources
                </p>
                <Badge variant="outline" className="gap-1">
                  <Sparkles className="size-3" />
                  Grounded
                </Badge>
              </div>
              <div className="space-y-2">
                {message.sources.map((source, index) => (
                  <SourceCitation key={source.chunk_id} source={source} index={index} />
                ))}
              </div>
            </div>
          )}
        </div>

        {message.model && (
          <p className="pl-1 text-[0.6875rem] text-muted-foreground/70">
            Answered by {message.model} from your documents
          </p>
        )}
      </div>
    </div>
  )
}

