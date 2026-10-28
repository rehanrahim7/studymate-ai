import { MessagesSquare } from 'lucide-react'

import { cn } from '@/lib/utils'

interface StarterQuestionsProps {
  onSelect: (question: string) => void
  disabled?: boolean
}

const STARTERS = [
  'What are the main topics covered in this document?',
  'Explain the key definitions I should memorise.',
  'Summarise the most important arguments or findings.',
  'What does the document say about the conclusion?',
]

/** Prompt suggestions shown before the first question, grounded in the user's own file. */
export function StarterQuestions({ onSelect, disabled }: StarterQuestionsProps) {
  return (
    <div className="flex flex-col items-center gap-5 px-4 py-10 text-center">
      <span className="flex size-12 items-center justify-center rounded-xl border border-primary/20 bg-primary-soft text-primary shadow-subtle">
        <MessagesSquare className="size-5" />
      </span>
      <div className="max-w-md">
        <p className="text-sm font-medium">Ask about anything in your documents</p>
        <p className="mt-1 text-pretty text-[0.8125rem] leading-relaxed text-muted-foreground">
          Answers are generated only from the pages you selected. Every answer lists the
          passages it used, so you can check the source yourself.
        </p>
      </div>

      <div className="grid w-full max-w-xl gap-2 sm:grid-cols-2">
        {STARTERS.map((question) => (
          <button
            key={question}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(question)}
            className={cn(
              'rounded-lg border border-border bg-card px-3.5 py-3 text-left text-[0.8125rem] leading-snug text-muted-foreground shadow-subtle transition-colors',
              disabled
                ? 'cursor-not-allowed opacity-55'
                : 'hover:border-primary/30 hover:bg-primary-soft/50 hover:text-foreground',
            )}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  )
}
