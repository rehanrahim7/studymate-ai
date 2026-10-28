import { useRef, useState, type KeyboardEvent } from 'react'
import { Loader2, SendHorizontal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ComposerProps {
  onSend: (question: string) => void
  isAsking: boolean
  disabled?: boolean
  disabledHint?: string
}

const MAX_LENGTH = 2000

/** Question input. Enter sends, Shift+Enter inserts a newline. */
export function Composer({ onSend, isAsking, disabled, disabledHint }: ComposerProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const trimmed = value.trim()
  const canSend = !disabled && !isAsking && trimmed.length > 0 && trimmed.length <= MAX_LENGTH

  const submit = () => {
    if (!canSend) return
    onSend(trimmed)
    setValue('')
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.focus()
    }
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  return (
    <div className="space-y-2">
      <div
        className={cn(
          'relative flex items-end gap-2 rounded-xl border border-input bg-card p-2 shadow-subtle transition-colors focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-ring/30',
          (disabled || isAsking) && 'opacity-70',
        )}
      >
        <textarea
          ref={textareaRef}
          value={value}
          rows={1}
          maxLength={MAX_LENGTH}
          disabled={disabled}
          onChange={(event) => setValue(event.target.value)}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? (disabledHint ?? 'Unavailable') : 'Ask a question about your documents…'}
          aria-label="Your question"
          className="scrollbar-subtle max-h-40 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-foreground outline-none placeholder:text-muted-foreground/70 disabled:cursor-not-allowed"
        />
        <Button
          type="button"
          size="icon"
          onClick={submit}
          disabled={!canSend}
          aria-label="Send question"
          className="mb-0.5 shrink-0"
        >
          {isAsking ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <SendHorizontal className="size-4" />
          )}
        </Button>
      </div>

      <div className="flex items-center justify-between px-1 text-[0.6875rem] text-muted-foreground">
        <span className="hidden items-center gap-1.5 sm:flex">
          <kbd className="rounded border border-border bg-secondary px-1.5 py-0.5 font-sans text-[0.625rem] font-medium">
            Enter
          </kbd>
          to send
          <span className="text-muted-foreground/50">·</span>
          <kbd className="rounded border border-border bg-secondary px-1.5 py-0.5 font-sans text-[0.625rem] font-medium">
            Shift + Enter
          </kbd>
          for a new line
        </span>
        {value.length > MAX_LENGTH * 0.8 && (
          <span className={cn('tabular-nums', value.length >= MAX_LENGTH && 'text-destructive')}>
            {value.length}/{MAX_LENGTH}
          </span>
        )}
      </div>
    </div>
  )
}
