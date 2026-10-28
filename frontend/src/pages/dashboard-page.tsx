import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CircleHelp,
  FileStack,
  FileText,
  Layers,
  MessagesSquare,
  ScrollText,
  Sparkles,
  UploadCloud,
} from 'lucide-react'

import { EmptyState } from '@/components/dashboard/empty-state'
import { StatCard } from '@/components/dashboard/stat-card'
import { DocumentList } from '@/components/documents/document-list'
import { UploadZone } from '@/components/documents/upload-zone'
import { FeatureCard } from '@/components/features/feature-card'
import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useDocuments } from '@/hooks/use-documents'
import { useHealth } from '@/hooks/use-health'

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

const STUDY_TOOLS = [
  {
    title: 'Chat with your document',
    description: 'Ask a question and get an answer grounded in the pages you uploaded.',
    icon: MessagesSquare,
    to: '/chat',
    footnote: 'Grounded answers with page citations.',
  },
  {
    title: 'Summaries',
    description: 'Condense a chapter into a structured, readable overview.',
    icon: ScrollText,
    to: '/summaries',
    footnote: 'Structured overview with key concepts.',
  },
  {
    title: 'Flashcards',
    description: 'Convert key definitions into flashcards you can actually revise with.',
    icon: Layers,
    to: '/flashcards',
    footnote: 'Flip through a generated revision deck.',
  },
  {
    title: 'Quizzes',
    description: 'Generate multiple-choice questions to test what you have learned.',
    icon: CircleHelp,
    to: '/quizzes',
    footnote: 'Score your answers with explanations.',
  },
]

export function DashboardPage() {
  const navigate = useNavigate()
  const { documents, error, openPicker, clearError } = useDocuments()
  const { health } = useHealth()

  const totals = useMemo(
    () => ({
      documents: documents.length,
      pages: documents.reduce((sum, document) => sum + document.page_count, 0),
      chunks: documents.reduce((sum, document) => sum + document.chunk_count, 0),
      characters: documents.reduce((sum, document) => sum + document.character_count, 0),
    }),
    [documents],
  )

  const engineReady = health?.llm === 'ready'

  return (
    <div className="relative">
      <div className="hero-glow" aria-hidden />

      <div className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <Alert
            className="mb-6"
            title="Something went wrong"
            description={error}
            onDismiss={clearError}
          />
        )}

        {/* Hero */}
        <section className="mb-8">
          <Badge variant="outline" className="gap-1.5">
            <Sparkles className="size-3" />
            {greeting()}
          </Badge>
          <h2 className="mt-3.5 text-3xl font-semibold tracking-tight sm:text-[2.125rem]">
            Turn your lecture slides into{' '}
            <span className="text-primary">things you actually remember.</span>
          </h2>
          <p className="mt-3 max-w-2xl text-pretty text-[0.9375rem] leading-relaxed text-muted-foreground">
            Upload the PDFs you already study with. StudyMate extracts the text, indexes
            every page, and grounds every answer in the source material.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button onClick={openPicker} size="lg">
              <UploadCloud className="size-4" />
              Upload a PDF
            </Button>
            <Button variant="ghost" size="lg" onClick={() => navigate('/documents')}>
              View library
            </Button>
          </div>
        </section>

        {/* Stats */}
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Documents"
            value={totals.documents}
            hint={totals.documents === 1 ? '1 PDF in your library' : 'PDFs in your library'}
            icon={FileText}
            emphasis
          />
          <StatCard
            label="Pages indexed"
            value={totals.pages}
            hint="Text extracted with PyMuPDF"
            icon={FileStack}
          />
          <StatCard
            label="Retrieval chunks"
            value={totals.chunks}
            hint="Ready for semantic search"
            icon={Sparkles}
          />
          <StatCard
            label="Local engine"
            value={engineReady ? 'Online' : health ? 'Offline' : '—'}
            hint={engineReady ? 'Ollama is responding' : 'Start Ollama to enable AI'}
            icon={Sparkles}
          />
        </section>

        {/* Main grid */}
        <section className="mt-6 grid gap-6 xl:grid-cols-3">
          <div className="space-y-6 xl:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Add a document</CardTitle>
                <CardDescription>
                  Text is extracted on the server with PyMuPDF. Nothing is sent to a third
                  party.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <UploadZone />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
                <div className="flex flex-col gap-1.5">
                  <CardTitle>Your documents</CardTitle>
                  <CardDescription>
                    {totals.documents > 0
                      ? `${totals.documents} document${totals.documents === 1 ? '' : 's'} · ${totals.pages} pages`
                      : 'Uploaded PDFs will appear here.'}
                  </CardDescription>
                </div>
                {totals.documents > 0 && (
                  <Button variant="outline" size="sm" onClick={() => navigate('/documents')}>
                    Manage
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                {totals.documents === 0 ? (
                  <EmptyState
                    icon={FileText}
                    title="No documents yet"
                    description="Upload your first PDF and StudyMate will extract its text, count its pages and index it for retrieval."
                    action={
                      <Button variant="subtle" size="sm" onClick={openPicker}>
                        <UploadCloud className="size-4" />
                        Upload a PDF
                      </Button>
                    }
                  />
                ) : (
                  <DocumentList />
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Study tools</CardTitle>
                <CardDescription>
                  Powered by retrieval over your own documents.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {STUDY_TOOLS.map((tool) => (
                  <FeatureCard
                    key={tool.to}
                    title={tool.title}
                    description={tool.description}
                    icon={tool.icon}
                    status="available"
                    footnote={tool.footnote}
                    onClick={() => navigate(tool.to)}
                  />
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>How it works</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-4">
                  {[
                    {
                      title: 'Upload a PDF',
                      body: 'Text and page numbers are extracted and stored locally.',
                    },
                    {
                      title: 'The text is chunked',
                      body: 'Your material is split into retrieval-sized pieces.',
                    },
                    {
                      title: 'Ask, summarise, revise',
                      body: 'Answers arrive grounded in the pages you uploaded.',
                    },
                  ].map((step, index) => (
                    <li key={step.title} className="flex gap-3">
                      <span className="flex size-6 shrink-0 items-center justify-center rounded-md border border-border bg-secondary text-[0.6875rem] font-semibold text-muted-foreground">
                        {index + 1}
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{step.title}</p>
                        <p className="mt-0.5 text-pretty text-xs leading-relaxed text-muted-foreground">
                          {step.body}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  )
}
