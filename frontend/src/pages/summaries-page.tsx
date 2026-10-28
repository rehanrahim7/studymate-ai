import { useState } from 'react'
import { FileText, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { generateSummary } from '@/lib/api'
import { useDocuments } from '@/hooks/use-documents'
import { AnswerMarkdown } from '@/components/chat/answer-markdown'

export function SummariesPage() {
  const { documents } = useDocuments()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [summary, setSummary] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const readyDocs = documents.filter((d) => d.status === 'ready')

  const handleGenerate = async () => {
    if (!selectedId) return
    setIsLoading(true)
    setError(null)
    try {
      const result = await generateSummary(selectedId)
      setSummary(result.summary)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate summary')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight">AI Summaries</h2>
        <p className="mt-1.5 text-muted-foreground">Generate a structured summary from your document</p>
      </header>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Select Document</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <select
            value={selectedId || ''}
            onChange={(e) => setSelectedId(Number(e.target.value))}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">Choose a document...</option>
            {readyDocs.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.original_filename}
              </option>
            ))}
          </select>
          <Button onClick={handleGenerate} disabled={!selectedId || isLoading}>
            {isLoading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <FileText className="mr-2 size-4" />}
            Generate Summary
          </Button>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <AnswerMarkdown text={summary} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
