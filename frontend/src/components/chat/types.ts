import type { ChatSource } from '@/types'

export type ChatRole = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: ChatRole
  text: string
  sources: ChatSource[]
  model: string | null
  /** Set when the answer came back without calling the model (no relevant context). */
  isRefusal: boolean
}

let counter = 0

/** Stable-enough id for locally created messages. */
export function nextMessageId(): string {
  counter += 1
  return `m${counter}-${Date.now().toString(36)}`
}
