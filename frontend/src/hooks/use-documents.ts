import { createContext, useContext } from 'react'

import type { DocumentSummary } from '@/types'

export interface UploadState {
  fileName: string
  progress: number
}

export interface DocumentsContextValue {
  documents: DocumentSummary[]
  isLoading: boolean
  error: string | null
  upload: UploadState | null
  isUploading: boolean
  /** Open the native file picker. */
  openPicker: () => void
  /** Upload the given files (the first one is used). */
  handleFiles: (files: FileList | File[]) => Promise<void>
  remove: (id: number) => Promise<void>
  refresh: () => Promise<void>
  clearError: () => void
}

export const DocumentsContext = createContext<DocumentsContextValue | null>(null)

/** Access shared document state. Must be used inside `<DocumentsProvider>`. */
export function useDocuments(): DocumentsContextValue {
  const context = useContext(DocumentsContext)
  if (!context) {
    throw new Error('useDocuments must be used within a DocumentsProvider')
  }
  return context
}
