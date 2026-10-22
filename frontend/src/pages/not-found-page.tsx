import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

export function NotFoundPage() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-4 py-20 sm:px-6">
      <Card className="w-full">
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <span className="flex size-12 items-center justify-center rounded-xl border border-border bg-secondary/70 text-muted-foreground">
            <Compass className="size-5" />
          </span>
          <div>
            <p className="text-lg font-semibold tracking-tight">Page not found</p>
            <p className="mt-1.5 text-pretty text-sm text-muted-foreground">
              The page you were looking for does not exist.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link to="/">Back to dashboard</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
