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

export interface HealthResponse {
  status: string
  app: string
  version: string
  environment: string
  database: 'connected' | 'unavailable' | string
  llm: 'ready' | 'unreachable' | string
}
