import { useEffect, useState } from 'react'
import { Check, CircleHelp, History, Layers, Loader2, Trash2, X } from 'lucide-react'
import { Link } from 'react-router-dom'

import { StudySourceStatus } from '@/components/study/source-status'
import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/dashboard/empty-state'
import { deleteFlashcardDeck, deleteQuiz, listFlashcardDecks, listQuizzes } from '@/lib/api'
import { formatStudyDate } from '@/lib/format'
import type { FlashcardDeckSummary, QuizSummary } from '@/types'

type DeleteTarget = { kind: 'deck' | 'quiz'; id: number; title: string } | null

export function StudyHistoryPage() {
  const [decks, setDecks] = useState<FlashcardDeckSummary[]>([])
  const [quizzes, setQuizzes] = useState<QuizSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [confirming, setConfirming] = useState<DeleteTarget>(null)
  const [deleting, setDeleting] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadHistory() {
      setIsLoading(true)
      setError(null)
      try {
        const [deckResponse, quizResponse] = await Promise.all([
          listFlashcardDecks(50, 0, controller.signal),
          listQuizzes(50, 0, controller.signal),
        ])
        setDecks(deckResponse.decks)
        setQuizzes(quizResponse.quizzes)
      } catch (e) {
        if (!controller.signal.aborted) {
          setError(e instanceof Error ? e.message : 'Failed to load study history')
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    void loadHistory()
    return () => controller.abort()
  }, [reloadKey])

  const handleDelete = async () => {
    if (!confirming) return
    setDeleting(true)
    setError(null)
    try {
      if (confirming.kind === 'deck') {
        await deleteFlashcardDeck(confirming.id)
      } else {
        await deleteQuiz(confirming.id)
      }
      setConfirming(null)
      setReloadKey((key) => key + 1)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete saved item')
    } finally {
      setDeleting(false)
    }
  }

  const renderDeleteControls = (target: DeleteTarget) => {
    if (!target) return null
    const isConfirming =
      confirming?.kind === target.kind && confirming.id === target.id

    if (!isConfirming) {
      return (
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={`Delete ${target.title}`}
          onClick={() => setConfirming(target)}
        >
          <Trash2 className="size-4" />
        </Button>
      )
    }

    return (
      <div className="flex items-center gap-1">
        <span className="text-[0.6875rem] text-muted-foreground">Delete?</span>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={`Confirm delete ${target.title}`}
          onClick={() => void handleDelete()}
          disabled={deleting}
        >
          {deleting ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Cancel delete"
          onClick={() => setConfirming(null)}
          disabled={deleting}
        >
          <X className="size-4" />
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <History className="size-5 text-muted-foreground" />
            <h2 className="text-2xl font-semibold tracking-tight">Study History</h2>
          </div>
          <p className="mt-1.5 text-muted-foreground">
            Reopen saved flashcard decks and quizzes. Generated sets stay here until you
            delete them.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/flashcards">New deck</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/quizzes">New quiz</Link>
          </Button>
        </div>
      </header>

      {error && (
        <Alert
          className="mb-6"
          title="Something went wrong"
          description={error}
          onDismiss={() => setError(null)}
        />
      )}

      <div className="space-y-6">
        <Card>
          <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
            <div className="flex flex-col gap-1">
              <CardTitle className="text-base">Flashcard decks</CardTitle>
              <CardDescription>
                {decks.length === 0
                  ? 'No saved decks yet.'
                  : `${decks.length} saved deck${decks.length === 1 ? '' : 's'}.`}
              </CardDescription>
            </div>
            <Layers className="size-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-2">
            {isLoading ? (
              <HistorySkeleton />
            ) : decks.length === 0 ? (
              <EmptyState
                icon={Layers}
                title="No flashcard decks yet"
                description="Generate a deck from one of your documents and it will be saved here automatically."
                action={
                  <Button asChild variant="subtle" size="sm">
                    <Link to="/flashcards">Generate flashcards</Link>
                  </Button>
                }
              />
            ) : (
              decks.map((deck) => {
                const target: DeleteTarget = {
                  kind: 'deck',
                  id: deck.id,
                  title: deck.title,
                }
                return (
                  <Card key={deck.id} className="shadow-none">
                    <CardContent className="flex items-start gap-3 p-4">
                      <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary-muted">
                        <Layers className="size-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <Link
                            to={`/flashcards?deck=${deck.id}`}
                            className="min-w-0 text-sm font-medium hover:underline"
                          >
                            <span className="block truncate">{deck.title}</span>
                          </Link>
                          {renderDeleteControls(target)}
                        </div>
                        <StudySourceStatus source={deck} className="mt-2" />
                        <p className="mt-2 text-xs text-muted-foreground">
                          {deck.card_count} card{deck.card_count === 1 ? '' : 's'} ·{' '}
                          {formatStudyDate(deck.created_at)}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                )
              })
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
            <div className="flex flex-col gap-1">
              <CardTitle className="text-base">Quizzes</CardTitle>
              <CardDescription>
                {quizzes.length === 0
                  ? 'No saved quizzes yet.'
                  : `${quizzes.length} saved quiz${quizzes.length === 1 ? '' : 'zes'}.`}
              </CardDescription>
            </div>
            <CircleHelp className="size-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-2">
            {isLoading ? (
              <HistorySkeleton />
            ) : quizzes.length === 0 ? (
              <EmptyState
                icon={CircleHelp}
                title="No quizzes yet"
                description="Generate a quiz and your score will be saved in this history."
                action={
                  <Button asChild variant="subtle" size="sm">
                    <Link to="/quizzes">Generate a quiz</Link>
                  </Button>
                }
              />
            ) : (
              quizzes.map((quiz) => {
                const target: DeleteTarget = {
                  kind: 'quiz',
                  id: quiz.id,
                  title: quiz.title,
                }
                return (
                  <Card key={quiz.id} className="shadow-none">
                    <CardContent className="flex items-start gap-3 p-4">
                      <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary-muted">
                        <CircleHelp className="size-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <Link
                            to={`/quizzes?quiz=${quiz.id}`}
                            className="min-w-0 text-sm font-medium hover:underline"
                          >
                            <span className="block truncate">{quiz.title}</span>
                          </Link>
                          {renderDeleteControls(target)}
                        </div>
                        <StudySourceStatus source={quiz} className="mt-2" />
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          <span>
                            {quiz.question_count} question
                            {quiz.question_count === 1 ? '' : 's'}
                          </span>
                          <span aria-hidden="true">·</span>
                          <span>{formatStudyDate(quiz.created_at)}</span>
                          {quiz.status === 'completed' ? (
                            <Badge variant="success">
                              Score {quiz.score}/{quiz.question_count}
                            </Badge>
                          ) : (
                            <Badge variant="outline">Not completed</Badge>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function HistorySkeleton() {
  return (
    <div className="space-y-2">
      {[0, 1, 2].map((index) => (
        <div key={index} className="h-20 animate-pulse rounded-lg bg-secondary/70" />
      ))}
    </div>
  )
}
