import { Outlet } from 'react-router-dom'

import { Sidebar } from '@/components/layout/sidebar'
import { TopBar } from '@/components/layout/top-bar'

/**
 * Responsive application shell: a fixed sidebar on large screens and a
 * drawer on small ones.
 */
export function AppShell() {
  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-[17rem] shrink-0 border-r border-sidebar-border lg:block">
        <div className="sticky top-0 h-screen">
          <Sidebar />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
