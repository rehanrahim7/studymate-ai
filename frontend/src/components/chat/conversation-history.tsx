import { useState } from 'react'
import { Check, MessageSquare, Pencil, Plus, Trash2, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { Conversation } from '@/types'

interface ConversationHistoryProps {
  conversations: Conversation[]
  activeId: number | null
  isLoading: boolean
  onSelect: (id: number) => void
  onNew: () => void
  onRename: (id: number, title: string) => void
  onDelete: (id: number) => void
}

/** Recent conversations: reopen, rename or delete past chats. */
export function ConversationHistory({
  conversations,
  activeId,
  isLoading,
  onSelect,
  onNew,
  onRename,
  onDelete,
}: ConversationHistoryProps) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<number | null>(null)
  const [draft, setDraft] = useState('')

  const startEditing = (conversation: Conversation) => {
    setConfirmingDeleteId(null)
    setEditingId(conversation.id)
    setDraft(conversation.title)
  }

  const cancelEditing = () => {
    setEditingId(null)
    setDraft('')
  }

  const submitRename = (id: number) => {
    const title = draft.trim()
    if (!title) return
    onRename(id, title)
    cancelEditing()
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0 pb-3">
        <CardTitle className="text-sm">History</CardTitle>
        <Button variant="ghost" size="sm" onClick={onNew} className="h-7 px-2 text-xs">
          <Plus className="size-3.5" />
          New
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading && conversations.length === 0 ? (
          <div className="space-y-2">
            {[0, 1, 2].map((index) => (
              <div key={index} className="h-10 animate-pulse rounded-lg bg-secondary/70" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <p className="px-1 py-2 text-xs leading-relaxed text-muted-foreground">
            No conversations yet. Ask a question and it will appear here.
          </p>
        ) : (
          <ul className="space-y-1">
            {conversations.map((conversation) => {
              const isActive = conversation.id === activeId
              const isEditing = conversation.id === editingId
              const isConfirmingDelete = conversation.id === confirmingDeleteId

              return (
                <li key={conversation.id}>
                  {isEditing ? (
                    <div className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-2 py-1.5">
                      <input
                        autoFocus
                        value={draft}
                        onChange={(event) => setDraft(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') submitRename(conversation.id)
                          if (event.key === 'Escape') cancelEditing()
                        }}
                        aria-label="Conversation title"
                        className="min-w-0 flex-1 rounded-md border border-input bg-background px-2 py-1 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      />
                      <button
                        type="button"
                        onClick={() => submitRename(conversation.id)}
                        aria-label="Save title"
                        className="rounded-md p-1 text-primary transition-colors hover:bg-primary-soft"
                      >
                        <Check className="size-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={cancelEditing}
                        aria-label="Cancel rename"
                        className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-secondary"
                      >
                        <X className="size-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div
                      className={cn(
                        'group flex items-center gap-1 rounded-lg border border-transparent transition-colors',
                        isActive ? 'border-primary/20 bg-primary-soft/60' : 'hover:bg-secondary/60',
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => onSelect(conversation.id)}
                        className="flex min-w-0 flex-1 items-start gap-2 px-2 py-2 text-left"
                      >
                        <MessageSquare
                          className={cn(
                            'mt-0.5 size-3.5 shrink-0',
                            isActive ? 'text-primary' : 'text-muted-foreground',
                          )}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-xs font-medium">
                            {conversation.title}
                          </span>
                          <span className="block text-[0.6875rem] text-muted-foreground">
                            {conversation.message_count}{' '}
                            {conversation.message_count === 1 ? 'message' : 'messages'}
                          </span>
                        </span>
                      </button>
                      {isConfirmingDelete ? (
                        <>
                          <span className="text-[0.6875rem] text-muted-foreground">Delete?</span>
                          <button
                            type="button"
                            onClick={() => {
                              onDelete(conversation.id)
                              setConfirmingDeleteId(null)
                            }}
                            aria-label={`Confirm delete ${conversation.title}`}
                            className="rounded-md p-1 text-destructive transition-colors hover:bg-destructive/10"
                          >
                            <Check className="size-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmingDeleteId(null)}
                            aria-label="Cancel delete"
                            className="mr-1 rounded-md p-1 text-muted-foreground transition-colors hover:bg-secondary"
                          >
                            <X className="size-3.5" />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => startEditing(conversation)}
                            aria-label={`Rename ${conversation.title}`}
                            className="rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-secondary focus-visible:opacity-100 group-hover:opacity-100"
                          >
                            <Pencil className="size-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmingDeleteId(conversation.id)}
                            aria-label={`Delete ${conversation.title}`}
                            className="mr-1 rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
                          >
                            <Trash2 className="size-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
