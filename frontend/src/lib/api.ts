/**
 * Typed client for the StudyMate API.
 *
 * All network access lives in this module so that UI components stay purely
 * presentational. No secrets are ever placed here — the backend is reached
 * through a public base URL only.
 */

import type {
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationDetail,
  DocumentDetail,
  DocumentListResponse,
  FlashcardDeck,
  FlashcardDeckListResponse,
  HealthResponse,
  QuizDetail,
  QuizListResponse,
} from '@/types'

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000/api/v1'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL
).replace(/\/+$/, '')

/** Error carrying the HTTP status and a message extracted from the API. */
export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const first = body.detail[0] as { msg?: string }
      if (first?.msg) return first.msg
    }
  } catch {
    /* response body was not JSON — fall through to the status text */
  }
  return response.statusText || `Request failed with status ${response.status}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...init.headers,
      },
    })
  } catch {
    throw new ApiError(
      `Cannot reach the StudyMate API at ${API_BASE_URL}. Is the backend running?`,
      0,
    )
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

/** `GET /health` — service, database and LLM status. */
export function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

/** `GET /documents` — all uploaded documents, newest first. */
export function listDocuments(): Promise<DocumentListResponse> {
  return request<DocumentListResponse>('/documents')
}

/** `GET /documents/{id}` — a single document. */
export function getDocument(id: number): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/documents/${id}`)
}

/** `DELETE /documents/{id}` — remove a document and its stored file. */
export function deleteDocument(id: number): Promise<void> {
  return request<void>(`/documents/${id}`, { method: 'DELETE' })
}

/**
 * `POST /chat` — ask a question grounded in the selected documents.
 *
 * The response always carries the real retrieved passages in `sources`; the
 * backend never lets the model invent citations.
 */
export function askQuestion(payload: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

/**
 * `POST /documents` — upload a PDF.
 *
 * Uses XMLHttpRequest because the Fetch API cannot report upload progress.
 */
export function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<DocumentDetail> {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    form.append('file', file)

    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE_URL}/documents`)

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as DocumentDetail)
        } catch {
          reject(new ApiError('The server returned an unreadable response.', xhr.status))
        }
        return
      }

      let message = `Upload failed with status ${xhr.status}`
      try {
        const body = JSON.parse(xhr.responseText) as { detail?: string }
        if (body.detail) message = body.detail
      } catch {
        /* keep the default message */
      }
      reject(new ApiError(message, xhr.status))
    })

    xhr.addEventListener('error', () => {
      reject(
        new ApiError(
          `Cannot reach the StudyMate API at ${API_BASE_URL}. Is the backend running?`,
          0,
        ),
      )
    })

    xhr.addEventListener('abort', () => {
      reject(new ApiError('Upload cancelled.', 0))
    })

    xhr.send(form)
  })
}

// Conversations
export function listConversations(): Promise<Conversation[]> {
  return request<Conversation[]>('/conversations')
}

export function createConversation(title?: string, documentIds: number[] = []): Promise<Conversation> {
  return request<Conversation>('/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, document_ids: documentIds }),
  })
}

export function getConversation(id: number): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/conversations/${id}`)
}

export function updateConversation(id: number, title: string): Promise<Conversation> {
  return request<Conversation>(`/conversations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
}

export function deleteConversation(id: number): Promise<void> {
  return request<void>(`/conversations/${id}`, { method: 'DELETE' })
}

// Study tools
export function generateSummary(documentId: number): Promise<{ summary: string }> {
  return request<{ summary: string }>('/study/summary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId }),
  })
}

export function generateFlashcards(
  documentId: number,
  count = 10,
): Promise<FlashcardDeck> {
  return request<FlashcardDeck>('/study/flashcards', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, count }),
  })
}

export function generateQuiz(documentId: number, count = 5): Promise<QuizDetail> {
  return request<QuizDetail>('/study/quiz', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, count }),
  })
}

export function listFlashcardDecks(
  limit = 20,
  offset = 0,
  signal?: AbortSignal,
): Promise<FlashcardDeckListResponse> {
  return request<FlashcardDeckListResponse>(
    `/study/flashcards?limit=${limit}&offset=${offset}`,
    { signal },
  )
}

export function getFlashcardDeck(id: number, signal?: AbortSignal): Promise<FlashcardDeck> {
  return request<FlashcardDeck>(`/study/flashcards/${id}`, { signal })
}

export function deleteFlashcardDeck(id: number): Promise<void> {
  return request<void>(`/study/flashcards/${id}`, { method: 'DELETE' })
}

export function listQuizzes(
  limit = 20,
  offset = 0,
  signal?: AbortSignal,
): Promise<QuizListResponse> {
  return request<QuizListResponse>(`/study/quizzes?limit=${limit}&offset=${offset}`, {
    signal,
  })
}

export function getQuiz(id: number, signal?: AbortSignal): Promise<QuizDetail> {
  return request<QuizDetail>(`/study/quizzes/${id}`, { signal })
}

export function submitQuiz(id: number, answers: string[]): Promise<QuizDetail> {
  return request<QuizDetail>(`/study/quizzes/${id}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  })
}

export function deleteQuiz(id: number): Promise<void> {
  return request<void>(`/study/quizzes/${id}`, { method: 'DELETE' })
}
