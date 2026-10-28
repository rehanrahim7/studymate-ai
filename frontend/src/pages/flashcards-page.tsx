import { useEffect, useRef, useState } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  CreditCard,
  History,
  Loader2,
  RotateCcw,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'

import { StudySourceStatus } from '@/components/study/source-status'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { generateFlashcards, getFlashcardDeck } from '@/lib/api'
import { useDocuments } from '@/hooks/use-documents'
import type { FlashcardDeck } from '@/types'
import { cn } from '@/lib/utils'

export function FlashcardsPage() {
  const { documents } = useDocuments()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [deck, setDeck] = useState<FlashcardDeck | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [loadError, setLoadError] = useState<{ id: number; message: string } | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const generationRef = useRef(0)
  const inFlightRef = useRef(false)

  const deckParam = searchParams.get('deck')
  const deckId = deckParam && /^\d+$/.test(deckParam) ? Number(deckParam) : null
  const readyDocs = documents.filter((document) => document.status === 'ready')
  const activeDeck = deck && deck.id === deckId ? deck : null
  const cards = activeDeck?.flashcards ?? []
  const isLoadingDeck = deckId !== null && !activeDeck && loadError?.id !== deckId
  const error = actionError ?? (loadError?.id === deckId ? loadError.message : null)

  useEffect(() => {
    if (!deckId) return
    if (deck?.id === deckId) return

    const controller = new AbortController()

    getFlashcardDeck(deckId, controller.signal)
      .then((savedDeck) => {
        if (controller.signal.aborted) return
        setDeck(savedDeck)
        setCurrentIndex(0)
        setFlipped(false)
      })
      .catch((e: unknown) => {
        if (controller.signal.aborted) return
        setDeck(null)
        setLoadError({
          id: deckId,
          message: e instanceof Error ? e.message : 'Failed to load saved flashcards',
        })
      })

    return () => controller.abort()
  }, [deckId, deck?.id])

  const handleGenerate = async () => {
    if (!selectedId || inFlightRef.current) return

    const requestToken = generationRef.current + 1
    generationRef.current = requestToken
    inFlightRef.current = true
    setIsGenerating(true)
    setActionError(null)
    setLoadError(null)
    setDeck(null)
    setCurrentIndex(0)
    setFlipped(false)
    setSearchParams({}, { replace: true })

    try {
      const result = await generateFlashcards(selectedId, 10)
      if (generationRef.current !== requestToken) return
      setDeck(result)
      setCurrentIndex(0)
      setFlipped(false)
      setSearchParams({ deck: String(result.id) }, { replace: true })
    } catch (e) {
      if (generationRef.current === requestToken) {
        setActionError(e instanceof Error ? e.message : 'Failed to generate flashcards')
      }
    } finally {
      if (generationRef.current === requestToken) {
        inFlightRef.current = false
        setIsGenerating(false)
      }
    }
  }

  const busy = isGenerating || isLoadingDeck

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Flashcards</h2>
          <p className="mt-1.5 text-muted-foreground">
            Practice with source-grounded flashcards. Every deck is saved automatically.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link to="/history">
            <History className="size-4" />
            Study History
          </Link>
        </Button>
      </header>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Select Document</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <select
            value={selectedId || ''}
            onChange={(event) => setSelectedId(Number(event.target.value))}
            disabled={busy}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
          >
            <option value="">Choose a document...</option>
            {readyDocs.map((document) => (
              <option key={document.id} value={document.id}>
                {document.original_filename}
              </option>
            ))}
          </select>
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => void handleGenerate()} disabled={!selectedId || busy}>
              {isGenerating ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <CreditCard className="size-4" />
              )}
              {isGenerating ? 'Generating...' : 'Generate Flashcards'}
            </Button>
            {isGenerating && (
              <p className="text-xs text-muted-foreground">
                This can take a minute on a local model.
              </p>
            )}
          </div>
          {readyDocs.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Upload and process a PDF before generating study material.
            </p>
          )}
          {error && (
            <Alert
              title="Flashcards unavailable"
              description={error}
              onDismiss={() => {
                setActionError(null)
                setLoadError(null)
              }}
            />
          )}
        </CardContent>
      </Card>

      {isLoadingDeck && (
        <Card>
          <CardContent className="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Loading saved deck...
          </CardContent>
        </Card>
      )}

      {!isLoadingDeck && activeDeck && cards.length > 0 && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h3 className="truncate text-sm font-medium">{activeDeck.title}</h3>
              <StudySourceStatus source={activeDeck} className="mt-2" />
            </div>
            <p className="shrink-0 text-sm text-muted-foreground">
              Card {currentIndex + 1} of {cards.length}
            </p>
          </div>

          <Card
            className={cn('min-h-[200px] cursor-pointer transition-all hover:shadow-md')}
            onClick={() => setFlipped((value) => !value)}
          >
            <CardContent className="flex min-h-[200px] items-center justify-center p-8 text-center">
              <p className="text-lg whitespace-pre-wrap">
                {flipped ? cards[currentIndex].answer : cards[currentIndex].question}
              </p>
            </CardContent>
          </Card>
          <p className="text-center text-sm text-muted-foreground">
            {flipped ? 'Click card to flip back' : 'Click card to flip'}
          </p>

          <div className="flex items-center justify-between gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setCurrentIndex((index) => Math.max(0, index - 1))
                setFlipped(false)
              }}
              disabled={currentIndex === 0}
            >
              <ChevronLeft className="size-4" />
              Previous
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setCurrentIndex(0)
                setFlipped(false)
              }}
            >
              <RotateCcw className="size-4" />
              Restart
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setCurrentIndex((index) => Math.min(cards.length - 1, index + 1))
                setFlipped(false)
              }}
              disabled={currentIndex === cards.length - 1}
            >
              Next
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
