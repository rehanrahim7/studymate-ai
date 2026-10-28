import { useMemo } from 'react'

import { cn } from '@/lib/utils'

type Block =
  | { kind: 'paragraph'; text: string }
  | { kind: 'list'; ordered: boolean; items: string[] }

/**
 * Split a plain-text answer into lightweight blocks.
 *
 * Answers come from a local LLM as plain text with occasional Markdown cues
 * (bullet lists, numbered lists, headings, `code`). We render a small, safe
 * subset as real React nodes instead of injecting HTML, so no answer can ever
 * smuggle markup into the page.
 */
function parseBlocks(source: string): Block[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const blocks: Block[] = []
  let paragraph: string[] = []
  let list: { ordered: boolean; items: string[] } | null = null

  const flushParagraph = () => {
    if (paragraph.length > 0) {
      const text = paragraph.join(' ').trim()
      if (text) blocks.push({ kind: 'paragraph', text })
      paragraph = []
    }
  }

  const flushList = () => {
    if (list) {
      blocks.push({ kind: 'list', ordered: list.ordered, items: list.items })
      list = null
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd()
    const bullet = /^\s*[-*•]\s+(.*)$/.exec(line)
    const numbered = /^\s*\d+[.)]\s+(.*)$/.exec(line)
    const heading = /^\s*#{1,6}\s+(.*)$/.exec(line)

    if (!line.trim()) {
      flushParagraph()
      flushList()
      continue
    }

    if (bullet || numbered) {
      flushParagraph()
      const ordered = Boolean(numbered)
      const item = (numbered?.[1] ?? bullet?.[1] ?? '').trim()
      if (!list || list.ordered !== ordered) {
        flushList()
        list = { ordered, items: [] }
      }
      list.items.push(item)
      continue
    }

    flushList()
    paragraph.push(heading ? heading[1].trim() : line.trim())
  }

  flushParagraph()
  flushList()
  return blocks
}

/** Render inline `code`, **bold** and *italic* spans as React nodes. */
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*\n]+\*)/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index))
    }
    const token = match[0]
    const id = `${keyPrefix}-${key++}`
    if (token.startsWith('`')) {
      nodes.push(
        <code
          key={id}
          className="rounded bg-secondary px-1 py-0.5 font-mono text-[0.8125em] text-foreground"
        >
          {token.slice(1, -1)}
        </code>,
      )
    } else if (token.startsWith('**')) {
      nodes.push(
        <strong key={id} className="font-semibold">
          {token.slice(2, -2)}
        </strong>,
      )
    } else {
      nodes.push(
        <em key={id} className="italic">
          {token.slice(1, -1)}
        </em>,
      )
    }
    lastIndex = pattern.lastIndex
  }

  if (lastIndex < text.length) nodes.push(text.slice(lastIndex))
  return nodes
}

interface AnswerTextProps {
  text: string
  className?: string
}

/** Renders an answer as readable, safely-escaped prose. */
export function AnswerText({ text, className }: AnswerTextProps) {
  const blocks = useMemo(() => parseBlocks(text), [text])

  return (
    <div className={cn('space-y-3 text-[0.9375rem] leading-relaxed', className)}>
      {blocks.map((block, index) => {
        if (block.kind === 'paragraph') {
          return <p key={index}>{renderInline(block.text, `p${index}`)}</p>
        }
        const ListTag = block.ordered ? 'ol' : 'ul'
        return (
          <ListTag
            key={index}
            className={cn(
              'ml-1 space-y-1.5 pl-4',
              block.ordered ? 'list-decimal' : 'list-disc',
            )}
          >
            {block.items.map((item, itemIndex) => (
              <li key={itemIndex} className="pl-0.5 marker:text-muted-foreground">
                {renderInline(item, `l${index}-${itemIndex}`)}
              </li>
            ))}
          </ListTag>
        )
      })}
    </div>
  )
}
