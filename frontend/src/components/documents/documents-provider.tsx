import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { deleteDocument, listDocuments, uploadDocument } from '@/lib/api'
import {
  DocumentsContext,
  type DocumentsContextValue,
  type UploadState,
} from '@/hooks/use-documents'
import type { DocumentSummary } from '@/types'

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024

/**
 * Owns the document library: loading, uploading and deleting PDFs.
 *
 * A single hidden file input is shared by the whole app so the top bar, the
 * dashboard drop zone and the documents page all trigger the same flow.
 */
export function DocumentsProvider({ children }: { children: React.ReactNode }) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [upload, setUpload] = useState<UploadState | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const refresh = useCallback(async () => {
    try {
      const response = await listDocuments()
      setDocuments(response.documents)
      setError(null)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load documents.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    // Initial load on mount — the state update happens after the request resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh()
  }, [refresh])

  const reload = useCallback(async () => {
    setIsLoading(true)
    await refresh()
  }, [refresh])

  const openPicker = useCallback(() => {
    inputRef.current?.click()
  }, [])

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const file = Array.from(files)[0]
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.')
      return
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setError('That file is larger than the 25 MB limit.')
      return
    }

    setError(null)
    setUpload({ fileName: file.name, progress: 0 })

    try {
      const created = await uploadDocument(file, (progress) =>
        setUpload({ fileName: file.name, progress }),
      )
      setDocuments((current) => [created, ...current])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The upload failed.')
    } finally {
      setUpload(null)
    }
  }, [])

  const remove = useCallback(
    async (id: number) => {
      const previous = documents
      setDocuments((current) => current.filter((document) => document.id !== id))
      try {
        await deleteDocument(id)
        setError(null)
      } catch (cause) {
        setDocuments(previous)
        setError(cause instanceof Error ? cause.message : 'Could not delete the document.')
        throw cause
      }
    },
    [documents],
  )

  const clearError = useCallback(() => setError(null), [])

  const value = useMemo<DocumentsContextValue>(
    () => ({
      documents,
      isLoading,
      error,
      upload,
      isUploading: upload !== null,
      openPicker,
      handleFiles,
      remove,
      refresh: reload,
      clearError,
    }),
    [documents, isLoading, error, upload, openPicker, handleFiles, remove, reload, clearError],
  )

  return (
    <DocumentsContext.Provider value={value}>
      {children}
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        aria-hidden
        tabIndex={-1}
        onChange={(event) => {
          if (event.target.files?.length) {
            void handleFiles(event.target.files)
          }
          // Allow re-selecting the same file straight away.
          event.target.value = ''
        }}
      />
    </DocumentsContext.Provider>
  )
}
