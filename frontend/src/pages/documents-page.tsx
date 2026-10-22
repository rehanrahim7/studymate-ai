import { FileText, UploadCloud } from 'lucide-react'

import { EmptyState } from '@/components/dashboard/empty-state'
import { DocumentList } from '@/components/documents/document-list'
import { UploadZone } from '@/components/documents/upload-zone'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useDocuments } from '@/hooks/use-documents'

export function DocumentsPage() {
  const { documents, error, openPicker, clearError } = useDocuments()

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      {error && (
        <Alert className="mb-6" title="Something went wrong" description={error} onDismiss={clearError} />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Upload a PDF</CardTitle>
          <CardDescription>
            Files are parsed on the backend and stored locally in SQLite. Text extraction
            happens with PyMuPDF — no external service is involved.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UploadZone />
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
          <div className="flex flex-col gap-1.5">
            <CardTitle>Library</CardTitle>
            <CardDescription>
              {documents.length === 0
                ? 'No documents yet.'
                : `${documents.length} document${documents.length === 1 ? '' : 's'} stored.`}
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={openPicker}>
            <UploadCloud className="size-4" />
            Add
          </Button>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="Your library is empty"
              description="Upload a PDF to get started. StudyMate records the page count, extracts the text and splits it into chunks you can search and cite."
              action={
                <Button variant="subtle" size="sm" onClick={openPicker}>
                  <UploadCloud className="size-4" />
                  Upload your first PDF
                </Button>
              }
            />
          ) : (
            <DocumentList />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
