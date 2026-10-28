import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, RefreshCw, RotateCcw, UploadCloud } from 'lucide-react'

import { Composer } from '@/components/chat/composer'
import { ConversationHistory } from '@/components/chat/conversation-history'
import { DocumentSelector } from '@/components/chat/document-selector'
import { EngineOfflineNotice } from '@/components/chat/engine-offline-notice'
import { MessageList } from '@/components/chat/message-list'
import { StarterQuestions } from '@/components/chat/starter-questions'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useChat } from '@/hooks/use-chat'
import { useDocuments } from '@/hooks/use-documents'
import { useHealth } from '@/hooks/use-health'
import {
  ApiError,
  deleteConversation,
  getConversation,
  listConversations,
  updateConversation,
} from '@/lib/api'
import type { Conversation } from '@/types'
import { cn } from '@/lib/utils'

const ACTIVE_CONVERSATION_KEY = 'studymate:activeConversation'

export function ChatPage() {
  const navigate = useNavigate()
  const { documents, isLoading: documentsLoading, openPicker } = useDocuments()
  const { health, isLoading: healthLoading, refresh: refreshHealth } = useHealth()
  const chat = useChat()

  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [userTouched, setUserTouched] = useState(false)
  const [autoKey, setAutoKey] = useState<string>('')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [conversationLoading, setConversationLoading] = useState(false)

  const readyDocuments = useMemo(
    () => documents.filter((document) => document.status === 'ready'),
    [documents],
  )

  const readyKey = useMemo(
    () => readyDocuments.map((document) => document.id).join(','),
    [readyDocuments],
  )

  useEffect(() => {
    // Prune selection to valid ready docs
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelectedIds((current) => {
      const valid = current
        .map((id) => Number(id))
        .filter((id) => readyDocuments.some((doc) => Number(doc.id) === id))
      if (valid.length === current.length && valid.every((v, i) => v === current[i])) {
        return current
      }
      return valid
    })
  }, [readyDocuments])

  useEffect(() => {
    // Auto-select all ready docs once per ready set until user intervenes
    if (userTouched) return
    if (readyKey === '' || autoKey === readyKey) return
    if (readyDocuments.length === 0) return
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAutoKey(readyKey)
    setSelectedIds(readyDocuments.map((document) => Number(document.id)))
  }, [readyKey, autoKey, userTouched, readyDocuments])

  const engineReady = health?.llm === 'ready'
  const hasDocuments = readyDocuments.length > 0
  const canAsk = engineReady && hasDocuments && selectedIds.length > 0 && !chat.isAsking

  const refreshConversations = useCallback(async () => {
    try {
      const items = await listConversations()
      setConversations(items)
    } catch {
      // History is optional; a failure here must not block chatting.
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  const openConversation = useCallback(
    async (id: number) => {
      if (chat.isAsking) return
      setConversationLoading(true)
      try {
        const detail = await getConversation(id)
        chat.setConversationId(detail.id)
        chat.setMessages(
          detail.messages.map((message) => ({
            id: `server-${message.id}`,
            role: message.role,
            text: message.content,
            sources: message.sources ?? [],
            model: message.model,
            isRefusal: !message.llm_used && (message.sources?.length ?? 0) === 0,
          })),
        )
        chat.clearError()
        const validIds = detail.document_ids.filter((documentId) =>
          readyDocuments.some((document) => document.id === documentId),
        )
        setUserTouched(true)
        setSelectedIds(validIds)
        window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, String(detail.id))
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY)
          chat.reset()
        }
        void refreshConversations()
      } finally {
        setConversationLoading(false)
      }
    },
    [chat, readyDocuments, refreshConversations],
  )

  const startNewConversation = useCallback(() => {
    chat.reset()
    window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY)
  }, [chat])

  const handleRenameConversation = useCallback(
    async (id: number, title: string) => {
      try {
        await updateConversation(id, title)
      } finally {
        await refreshConversations()
      }
    },
    [refreshConversations],
  )

  const handleDeleteConversation = useCallback(
    async (id: number) => {
      try {
        await deleteConversation(id)
      } finally {
        if (chat.conversationId === id) startNewConversation()
        await refreshConversations()
      }
    },
    [chat.conversationId, refreshConversations, startNewConversation],
  )

  useEffect(() => {
    // Initial history load; the async fetch only sets state once it resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshConversations()
  }, [refreshConversations])

  const restoredRef = useRef(false)
  useEffect(() => {
    if (documentsLoading || restoredRef.current) return
    restoredRef.current = true
    const stored = window.localStorage.getItem(ACTIVE_CONVERSATION_KEY)
    if (!stored) return
    const id = Number(stored)
    if (!Number.isInteger(id)) {
      window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY)
      return
    }
    // Restore the last conversation once documents are available.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void openConversation(id)
  }, [documentsLoading, openConversation])

  useEffect(() => {
    if (chat.conversationId) {
      window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, String(chat.conversationId))
      // A retry can create the conversation without going through handleSend.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void refreshConversations()
    }
  }, [chat.conversationId, refreshConversations])

  const toggleDocument = useCallback((id: number) => {
    setUserTouched(true)
    setSelectedIds((current) => {
      const normalizedId = Number(id)
      if (current.includes(normalizedId)) {
        return current.filter((value) => Number(value) !== normalizedId)
      }
      return [...current, normalizedId]
    })
  }, [])

  const handleSelectAll = useCallback(() => {
    setUserTouched(true)
    setSelectedIds(readyDocuments.map((doc) => Number(doc.id)))
  }, [readyDocuments])

  const handleClear = useCallback(() => {
    setUserTouched(true)
    setSelectedIds([])
  }, [])

  const handleSend = useCallback(
    (question: string) => {
      if (!canAsk) return
      void chat.ask({ question, documentIds: selectedIds }).then(() => {
        void refreshConversations()
      })
    },
    [canAsk, chat, selectedIds, refreshConversations],
  )

  const disabledHint = !engineReady
    ? 'Start the local AI engine to ask a question'
    : documentsLoading
      ? 'Loading your documents…'
      : !hasDocuments
        ? 'Upload and index a PDF first'
        : selectedIds.length === 0
          ? 'Select at least one document'
          : undefined

  return (
    <div className="relative">
      <div className="hero-glow" aria-hidden />

      <div className="relative mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Ask your documents</h2>
            <p className="mt-1.5 max-w-2xl text-pretty text-[0.9375rem] leading-relaxed text-muted-foreground">
              Pick the documents to draw from, then ask a question. Answers are grounded in
              the retrieved pages and cite every passage used.
            </p>
          </div>
          {chat.messages.length > 0 && (
            <Button variant="outline" size="sm" onClick={startNewConversation}>
              <RotateCcw className="size-4" />
              New conversation
            </Button>
          )}
        </header>

        {chat.error && (
          <div className="mb-5 space-y-2">
            <Alert
              title="Could not get an answer"
              description={chat.error}
              onDismiss={chat.clearError}
            />
            {chat.canRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => void chat.retry()}
                disabled={chat.isAsking}
              >
                <RefreshCw className={cn('size-4', chat.isAsking && 'animate-spin')} />
                Retry
              </Button>
            )}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[19rem_1fr]">
          <aside className="lg:sticky lg:top-20 lg:self-start">
            <div className="space-y-4">
              <Card>
                <CardHeader className="flex-row items-center justify-between gap-2 space-y-0 pb-3">
                  <CardTitle className="text-sm">Scope</CardTitle>
                  <Button variant="ghost" size="sm" onClick={openPicker} className="h-7 px-2 text-xs">
                    <UploadCloud className="size-3.5" />
                    Add
                  </Button>
                </CardHeader>
                <CardContent>
                  {documentsLoading ? (
                    <div className="space-y-2">
                      {[0, 1, 2].map((index) => (
                        <div key={index} className="h-12 animate-pulse rounded-lg bg-secondary/70" />
                      ))}
                    </div>
                  ) : (
                    <DocumentSelector
                      documents={documents}
                      selectedIds={selectedIds}
                      onToggle={toggleDocument}
                      onSelectAll={handleSelectAll}
                      onClear={handleClear}
                      disabled={chat.isAsking}
                    />
                  )}
                </CardContent>
              </Card>

              <ConversationHistory
                conversations={conversations}
                activeId={chat.conversationId}
                isLoading={historyLoading || conversationLoading}
                onSelect={(id) => void openConversation(id)}
                onNew={startNewConversation}
                onRename={(id, title) => void handleRenameConversation(id, title)}
                onDelete={(id) => void handleDeleteConversation(id)}
              />
            </div>
          </aside>

          <div className="flex min-h-[65vh] flex-col gap-4">
            <Card className="flex flex-1 flex-col">
              <CardContent className="flex flex-1 flex-col p-4 pt-4 sm:p-5 sm:pt-5">
                {healthLoading ? (
                  <div className="flex flex-1 items-center justify-center py-16">
                    <RefreshCw className="size-5 animate-spin text-muted-foreground" />
                  </div>
                ) : !engineReady ? (
                  <EngineOfflineNotice
                    onRetry={() => void refreshHealth()}
                    isRetrying={healthLoading}
                  />
                ) : !hasDocuments ? (
                  <NoDocuments onUpload={openPicker} onBrowse={() => navigate('/documents')} />
                ) : chat.messages.length === 0 ? (
                  <StarterQuestions
                    onSelect={handleSend}
                    disabled={selectedIds.length === 0 || chat.isAsking}
                  />
                ) : (
                  <MessageList messages={chat.messages} isAsking={chat.isAsking} />
                )}
              </CardContent>
            </Card>

            <div className={cn('sticky bottom-0')}>
              <Composer
                onSend={handleSend}
                isAsking={chat.isAsking}
                disabled={!engineReady || !hasDocuments}
                disabledHint={disabledHint}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function NoDocuments({ onUpload, onBrowse }: { onUpload: () => void; onBrowse: () => void }) {
  return (
    <div className="flex flex-col items-center gap-5 px-4 py-10 text-center">
      <span className="flex size-12 items-center justify-center rounded-xl border border-border bg-secondary/70 text-muted-foreground shadow-subtle">
        <FileText className="size-5" />
      </span>
      <div className="max-w-md">
        <p className="text-sm font-medium">No indexed documents yet</p>
        <p className="mt-1 text-pretty text-[0.8125rem] leading-relaxed text-muted-foreground">
          Chat answers only from your own material. Upload a PDF and StudyMate will index
          it, then you can ask questions about it here.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-3">
        <Button onClick={onUpload}>
          <UploadCloud className="size-4" />
          Upload a PDF
        </Button>
        <Button variant="outline" onClick={onBrowse}>
          Open my library
        </Button>
      </div>
    </div>
  )
}
