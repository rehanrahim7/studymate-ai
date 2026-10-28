import { useCallback, useRef, useState } from 'react'

import { nextMessageId, type ChatMessage } from '@/components/chat/types'
import { askQuestion, ApiError } from '@/lib/api'
import type { ChatSource } from '@/types'

export interface SendOptions {
  question: string
  documentIds: number[]
  conversationId?: number
}

export interface UseChatResult {
  messages: ChatMessage[]
  isAsking: boolean
  error: string | null
  /** `true` when the last failure is worth retrying (connectivity / engine). */
  canRetry: boolean
  conversationId: number | null
  ask: (options: SendOptions) => Promise<void>
  retry: () => Promise<void>
  clearError: () => void
  reset: () => void
  setMessages: (messages: ChatMessage[]) => void
  setConversationId: (id: number | null) => void
}

/** Deterministic id for the optimistic user turn so retry can drop it cleanly. */
function userMessageId(question: string): string {
  return `user:${question}:${Date.now()}`
}

/**
 * Owns the chat transcript and the in-flight request.
 */
export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isAsking, setIsAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [canRetry, setCanRetry] = useState(false)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const lastRequest = useRef<SendOptions | null>(null)

  const run = useCallback(async (options: SendOptions) => {
    setIsAsking(true)
    setError(null)
    setCanRetry(false)

    try {
      const response = await askQuestion({
        question: options.question,
        document_ids: options.documentIds,
        conversation_id: options.conversationId || conversationId || undefined,
      })

      if (response.conversation_id && !conversationId) {
        setConversationId(response.conversation_id)
      }

      const sources: ChatSource[] = response.sources
      setMessages((current) => [
        ...current,
        {
          id: nextMessageId(),
          role: 'assistant',
          text: response.answer,
          sources,
          model: response.model,
          isRefusal: !response.llm_used && sources.length === 0,
        },
      ])
    } catch (cause) {
      const message =
        cause instanceof ApiError
          ? cause.message
          : cause instanceof Error
            ? cause.message
            : 'Something went wrong while answering.'
      setError(message)
      setCanRetry(true)
    } finally {
      setIsAsking(false)
    }
  }, [conversationId])

  const ask = useCallback(
    async (options: SendOptions) => {
      const question = options.question.trim()
      if (!question || isAsking) return

      setMessages((current) => [
        ...current,
        {
          id: userMessageId(question),
          role: 'user',
          text: question,
          sources: [],
          model: null,
          isRefusal: false,
        },
      ])

      lastRequest.current = { ...options, question }
      await run({ ...options, question })
    },
    [isAsking, run],
  )

  const retry = useCallback(async () => {
    if (!lastRequest.current || isAsking) return
    await run(lastRequest.current)
  }, [isAsking, run])

  const clearError = useCallback(() => setError(null), [])

  const reset = useCallback(() => {
    setMessages([])
    setError(null)
    setCanRetry(false)
    lastRequest.current = null
    setConversationId(null)
  }, [])

  return { messages, isAsking, error, canRetry, conversationId, ask, retry, clearError, reset, setMessages, setConversationId }
}
