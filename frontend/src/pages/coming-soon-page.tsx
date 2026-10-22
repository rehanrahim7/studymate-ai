import { useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, Construction } from 'lucide-react'

import { allNavItems } from '@/components/layout/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

/**
 * Placeholder route for the study tools that are still being built.
 *
 * It states plainly what is missing instead of showing invented results.
 */
export function ComingSoonPage() {
  const { pathname } = useLocation()
  const navigate = useNavigate()

  const item =
    allNavItems.find((candidate) => candidate.to === pathname) ??
    allNavItems.find((candidate) => pathname.startsWith(candidate.to))

  const title = item?.label ?? 'Feature'
  const description =
    item?.description ?? 'This part of StudyMate is still being built.'

  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center px-4 py-16 sm:px-6">
      <Card className="w-full overflow-hidden">
        <div className="relative border-b border-border bg-gradient-to-br from-primary-soft/70 to-transparent px-6 py-10 text-center dark:from-primary-soft/40">
          <div className="hero-glow" aria-hidden />
          <span className="relative mx-auto flex size-12 items-center justify-center rounded-xl border border-primary/20 bg-card text-primary shadow-subtle">
            <Construction className="size-5" />
          </span>
          <h2 className="relative mt-4 text-xl font-semibold tracking-tight">{title}</h2>
          <p className="relative mx-auto mt-2 max-w-md text-pretty text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        </div>

        <CardContent className="p-6">
          <p className="text-sm font-medium">Not wired up yet</p>
          <p className="mt-2 text-pretty text-[0.8125rem] leading-relaxed text-muted-foreground">
            This feature depends on the retrieval pipeline — embeddings, vector search and
            the local Ollama model. Until those are connected, StudyMate will not pretend to
            produce answers, summaries or quizzes. Everything you upload is still extracted
            and indexed, so the work is already done.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Button onClick={() => navigate('/')}>
              <ArrowLeft className="size-4" />
              Back to dashboard
            </Button>
            <Button variant="outline" onClick={() => navigate('/documents')}>
              Open my library
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
