import { useEffect, useRef } from 'react'
import { Loader2 } from 'lucide-react'

import { MessageBubble } from '@/components/chat/message-bubble'
import type { ChatMessage } from '@/components/chat/types'

interface MessageListProps {
  messages: ChatMessage[]
  isAsking: boolean
}

/** Scrollable transcript with a typing indicator for the in-flight answer. */
export function MessageList({ messages, isAsking }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, isAsking])

  return (
    <div className="space-y-5">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {isAsking && (
        <div className="flex gap-3">
          <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-primary-soft text-primary">
            <Loader2 className="size-3.5 animate-spin" />
          </span>
          <div className="flex items-center rounded-2xl rounded-tl-md border border-border bg-card px-4 py-3 shadow-card">
            <span className="flex items-center gap-2 text-[0.8125rem] text-muted-foreground">
              Searching your documents and writing an answer
              <span className="flex gap-0.5">
                <span className="size-1 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:0ms]" />
                <span className="size-1 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:150ms]" />
                <span className="size-1 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:300ms]" />
              </span>
            </span>
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  )
}
