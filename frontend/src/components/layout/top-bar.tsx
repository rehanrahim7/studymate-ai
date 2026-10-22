import { useState } from 'react'
import { Menu, Upload } from 'lucide-react'
import { useLocation } from 'react-router-dom'

import { allNavItems } from '@/components/layout/navigation'
import { Sidebar } from '@/components/layout/sidebar'
import { ThemeToggle } from '@/components/theme/theme-toggle'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { useDocuments } from '@/hooks/use-documents'

export function TopBar() {
  const { pathname } = useLocation()
  const { openPicker } = useDocuments()
  const [isNavOpen, setIsNavOpen] = useState(false)

  const current =
    allNavItems.find((item) => item.to === pathname) ??
    allNavItems.find((item) => item.to !== '/' && pathname.startsWith(item.to))

  const title = current?.label ?? 'StudyMate'
  const description = current?.description ?? 'Learn from your own course material.'

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-xl sm:px-6">
      <Sheet open={isNavOpen} onOpenChange={setIsNavOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="-ml-1 lg:hidden" aria-label="Open navigation">
            <Menu className="size-5" />
          </Button>
        </SheetTrigger>
        <SheetContent>
          <Sidebar onNavigate={() => setIsNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-sm font-semibold tracking-tight">{title}</h1>
        <p className="hidden truncate text-xs text-muted-foreground sm:block">{description}</p>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <ThemeToggle />
        <Button size="sm" onClick={openPicker} className="shadow-subtle">
          <Upload className="size-4" />
          <span className="hidden sm:inline">Upload PDF</span>
        </Button>
      </div>
    </header>
  )
}
