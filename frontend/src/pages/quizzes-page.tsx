import { useEffect, useRef, useState } from 'react'
import { Check, HelpCircle, History, Loader2, X } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'

import { StudySourceStatus } from '@/components/study/source-status'
import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { generateQuiz, getQuiz, submitQuiz } from '@/lib/api'
import { useDocuments } from '@/hooks/use-documents'
import type { QuizDetail } from '@/types'
import { cn } from '@/lib/utils'

export function QuizzesPage() {
  const { documents } = useDocuments()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [quiz, setQuiz] = useState<QuizDetail | null>(null)
  const [answers, setAnswers] = useState<string[]>([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [loadError, setLoadError] = useState<{ id: number; message: string } | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const generationRef = useRef(0)
  const inFlightRef = useRef(false)
  const submittingRef = useRef(false)

  const quizParam = searchParams.get('quiz')
  const quizId = quizParam && /^\d+$/.test(quizParam) ? Number(quizParam) : null
  const readyDocs = documents.filter((document) => document.status === 'ready')
  const activeQuiz = quiz && quiz.id === quizId ? quiz : null
  const submitted = activeQuiz?.status === 'completed'
  const isLoadingQuiz = quizId !== null && !activeQuiz && loadError?.id !== quizId
  const error = actionError ?? (loadError?.id === quizId ? loadError.message : null)

  useEffect(() => {
    if (!quizId) return
    if (quiz?.id === quizId) return

    const controller = new AbortController()

    getQuiz(quizId, controller.signal)
      .then((savedQuiz) => {
        if (controller.signal.aborted) return
        setQuiz(savedQuiz)
        setAnswers(savedQuiz.questions.map((question) => question.selected_answer ?? ''))
      })
      .catch((e: unknown) => {
        if (controller.signal.aborted) return
        setQuiz(null)
        setAnswers([])
        setLoadError({
          id: quizId,
          message: e instanceof Error ? e.message : 'Failed to load saved quiz',
        })
      })

    return () => controller.abort()
  }, [quizId, quiz?.id])

  const handleGenerate = async () => {
    if (!selectedId || inFlightRef.current) return

    const requestToken = generationRef.current + 1
    generationRef.current = requestToken
    inFlightRef.current = true
    setIsGenerating(true)
    setActionError(null)
    setLoadError(null)
    setQuiz(null)
    setAnswers([])
    setSearchParams({}, { replace: true })

    try {
      const result = await generateQuiz(selectedId, 5)
      if (generationRef.current !== requestToken) return
      setQuiz(result)
      setAnswers(new Array(result.questions.length).fill(''))
      setSearchParams({ quiz: String(result.id) }, { replace: true })
    } catch (e) {
      if (generationRef.current === requestToken) {
        setActionError(e instanceof Error ? e.message : 'Failed to generate quiz')
      }
    } finally {
      if (generationRef.current === requestToken) {
        inFlightRef.current = false
        setIsGenerating(false)
      }
    }
  }

  const handleSubmit = async () => {
    if (!activeQuiz || submitted || submittingRef.current) return
    if (
      answers.length !== activeQuiz.questions.length ||
      answers.some((answer) => !answer)
    ) {
      return
    }

    submittingRef.current = true
    setIsSubmitting(true)
    setActionError(null)
    try {
      const result = await submitQuiz(activeQuiz.id, answers)
      setQuiz(result)
      setAnswers(result.questions.map((question) => question.selected_answer ?? ''))
      setSearchParams({ quiz: String(result.id) }, { replace: true })
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to submit quiz')
    } finally {
      submittingRef.current = false
      setIsSubmitting(false)
    }
  }

  const busy = isGenerating || isLoadingQuiz || isSubmitting

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Quizzes</h2>
          <p className="mt-1.5 text-muted-foreground">
            Test your knowledge with source-grounded questions. Scores are saved on the
            backend.
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
                <HelpCircle className="size-4" />
              )}
              {isGenerating ? 'Generating...' : 'Generate Quiz'}
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
              title="Quiz unavailable"
              description={error}
              onDismiss={() => {
                setActionError(null)
                setLoadError(null)
              }}
            />
          )}
        </CardContent>
      </Card>

      {isLoadingQuiz && (
        <Card>
          <CardContent className="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Loading saved quiz...
          </CardContent>
        </Card>
      )}

      {!isLoadingQuiz && activeQuiz && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h3 className="truncate text-sm font-medium">{activeQuiz.title}</h3>
              <StudySourceStatus source={activeQuiz} className="mt-2" />
            </div>
            {submitted && (
              <Badge variant="success" className="shrink-0">
                Score {activeQuiz.score}/{activeQuiz.question_count}
              </Badge>
            )}
          </div>

          {submitted && (
            <Card>
              <CardContent className="p-6 text-center">
                <p className="text-2xl font-semibold">
                  {activeQuiz.score} / {activeQuiz.question_count}
                </p>
                <p className="text-muted-foreground">Score</p>
              </CardContent>
            </Card>
          )}

          {activeQuiz.questions.map((question, questionIndex) => (
            <Card key={`${activeQuiz.id}-${questionIndex}`}>
              <CardHeader>
                <CardTitle className="text-base">Question {questionIndex + 1}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="font-medium">{question.question}</p>
                <div className="space-y-2">
                  {question.options.map((option) => {
                    const selected = submitted
                      ? question.selected_answer === option
                      : answers[questionIndex] === option
                    const correct = submitted && question.correct_answer === option

                    return (
                      <button
                        key={option}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => {
                          if (submitted || isSubmitting) return
                          const nextAnswers = [...answers]
                          nextAnswers[questionIndex] = option
                          setAnswers(nextAnswers)
                        }}
                        disabled={submitted || isSubmitting}
                        className={cn(
                          'flex w-full items-center justify-between gap-3 rounded-lg border p-3 text-left text-sm transition-colors',
                          submitted
                            ? correct
                              ? 'border-green-500 bg-green-50 text-green-900 dark:bg-green-950 dark:text-green-100'
                              : selected
                                ? 'border-red-500 bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-100'
                                : 'border-border'
                            : selected
                              ? 'border-primary bg-primary/5'
                              : 'border-border hover:bg-accent',
                        )}
                      >
                        <span>{option}</span>
                        {submitted && correct && <Check className="size-4 shrink-0" />}
                        {submitted && selected && !correct && (
                          <X className="size-4 shrink-0" />
                        )}
                      </button>
                    )
                  })}
                </div>
                {submitted && (
                  <div className="rounded-lg bg-muted p-3 text-sm">
                    <p>
                      <span className="font-medium">Correct answer:</span>{' '}
                      {question.correct_answer}
                    </p>
                    <p className="mt-1 text-muted-foreground">{question.explanation}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}

          {!submitted && (
            <Button
              onClick={() => void handleSubmit()}
              disabled={
                isSubmitting ||
                answers.length !== activeQuiz.questions.length ||
                answers.some((answer) => !answer)
              }
            >
              {isSubmitting && <Loader2 className="size-4 animate-spin" />}
              {isSubmitting ? 'Submitting...' : 'Submit Quiz'}
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
