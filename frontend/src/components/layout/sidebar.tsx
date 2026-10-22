import { NavLink } from 'react-router-dom'
import { Sparkles } from 'lucide-react'

import { navSections } from '@/components/layout/navigation'
import { Badge } from '@/components/ui/badge'
import { EngineStatusCard } from '@/components/layout/engine-status-card'
import { cn } from '@/lib/utils'

interface SidebarProps {
  /** Called after a navigation event — used to close the mobile drawer. */
  onNavigate?: () => void
}

/** Primary application navigation. Rendered inline on desktop, in a sheet on mobile. */
export function Sidebar({ onNavigate }: SidebarProps) {
  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex h-16 shrink-0 items-center gap-2.5 px-5">
        <span className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 via-indigo-600 to-violet-600 shadow-sm ring-1 ring-inset ring-white/20">
          <Sparkles className="size-4 text-white" strokeWidth={2.25} />
        </span>
        <span className="text-[0.9375rem] font-semibold tracking-tight">StudyMate</span>
        <Badge variant="muted" className="px-1.5 py-0 text-[0.625rem] uppercase tracking-wider">
          AI
        </Badge>
      </div>

      <nav className="scrollbar-subtle flex-1 overflow-y-auto px-3 pb-4 pt-2">
        {navSections.map((section) => (
          <div key={section.title} className="mb-6">
            <p className="px-3 pb-2 text-[0.6875rem] font-semibold uppercase tracking-wider text-sidebar-muted/80">
              {section.title}
            </p>
            <ul className="space-y-0.5">
              {section.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.to === '/'}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      cn(
                        'group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-sidebar-accent text-primary'
                          : 'text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground',
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <span
                          className={cn(
                            'absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r-full bg-primary transition-opacity',
                            isActive ? 'opacity-100' : 'opacity-0',
                          )}
                        />
                        <item.icon className="size-4 shrink-0" strokeWidth={isActive ? 2.2 : 1.9} />
                        <span className="flex-1 truncate">{item.label}</span>
                        {item.badge && (
                          <span className="rounded-full border border-border px-1.5 py-px text-[0.625rem] font-medium uppercase tracking-wide text-muted-foreground">
                            {item.badge}
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-sidebar-border p-3">
        <EngineStatusCard />
      </div>
    </div>
  )
}
