import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { cn } from '@/lib/utils'

interface AnswerMarkdownProps {
  text: string
  className?: string
}

/** Safely render assistant answers as Markdown (no raw HTML). */
export function AnswerMarkdown({ text, className }: AnswerMarkdownProps) {
  return (
    <div
      className={cn(
        'prose prose-sm max-w-none dark:prose-invert',
        'prose-headings:mt-4 prose-headings:first:mt-0 prose-headings:scroll-m-20 prose-headings:tracking-tight',
        'prose-h2:text-base prose-h3:text-[0.9375rem]',
        'prose-p:my-2 prose-p:first:mt-0 prose-p:last:mb-0 prose-p:leading-relaxed',
        'prose-ul:my-2 prose-ol:my-2',
        'prose-li:my-0.5',
        'prose-code:rounded prose-code:bg-secondary prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:text-[0.8125em]',
        'prose-pre:my-3 prose-pre:overflow-x-auto prose-pre:rounded-lg prose-pre:bg-secondary/70 prose-pre:p-3',
        'prose-a:text-primary prose-a:no-underline hover:prose-a:underline',
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        disallowedElements={['script', 'iframe', 'object', 'embed']}
        unwrapDisallowed
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}
