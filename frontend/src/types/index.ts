/** Shared API types, mirroring the FastAPI Pydantic schemas. */

export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'

export interface DocumentSummary {
  id: number
  filename: string
  original_filename: string
  file_size: number
  status: DocumentStatus
  page_count: number
  character_count: number
  chunk_count: number
  created_at: string
}

export interface DocumentDetail extends DocumentSummary {
  error_message: string | null
  updated_at: string
}

export interface DocumentListResponse {
  documents: DocumentSummary[]
  total: number
}

/** A retrieved passage backing an answer — always real chunks, never invented. */
export interface ChatSource {
  document_id: number
  document_name: string
  chunk_id: number
  page_number: number
  ordinal: number
  score: number
  text: string
}

export interface ChatRequest {
  question: string
  document_ids: number[]
  top_k?: number
  conversation_id?: number
}

export interface ChatResponse {
  answer: string
  sources: ChatSource[]
  model: string | null
  llm_used: boolean
  prompt_tokens: number
  completion_tokens: number
  conversation_id?: number
  message_id?: number
}

export interface HealthResponse {
  status: string
  app: string
  version: string
  environment: string
  database: 'connected' | 'unavailable' | string
  llm: 'ready' | 'unreachable' | string
}

export interface Conversation {
  id: number
  title: string
  document_ids: number[]
  created_at: string
  updated_at: string
  message_count: number
}

export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant'
  content: string
  sources: ChatSource[] | null
  model: string | null
  llm_used: boolean
  created_at: string
}

export interface ConversationDetail {
  id: number
  title: string
  document_ids: number[]
  created_at: string
  updated_at: string
  messages: Message[]
}

export interface Flashcard {
  question: string
  answer: string
}

export interface StudySourceState {
  source_document_id: number | null
  source_label: string
  source_hash: string
  source_available: boolean
  source_status: string
  source_changed: boolean
}

export interface FlashcardDeckSummary extends StudySourceState {
  id: number
  title: string
  card_count: number
  created_at: string
}

export interface FlashcardDeck extends FlashcardDeckSummary {
  flashcards: Flashcard[]
}

export interface FlashcardDeckListResponse {
  decks: FlashcardDeckSummary[]
  total: number
}

export interface QuizQuestion {
  question: string
  options: string[]
  selected_answer: string | null
  correct_answer: string | null
  explanation: string | null
  is_correct: boolean | null
}

export type QuizStatus = 'open' | 'completed'

export interface QuizSummary extends StudySourceState {
  id: number
  title: string
  question_count: number
  status: QuizStatus
  score: number | null
  completed_at: string | null
  created_at: string
}

export interface QuizDetail extends QuizSummary {
  questions: QuizQuestion[]
}

export interface QuizListResponse {
  quizzes: QuizSummary[]
  total: number
}
