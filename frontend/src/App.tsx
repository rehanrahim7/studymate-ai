import { Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/layout/app-shell'
import { ComingSoonPage } from '@/pages/coming-soon-page'
import { DashboardPage } from '@/pages/dashboard-page'
import { DocumentsPage } from '@/pages/documents-page'
import { NotFoundPage } from '@/pages/not-found-page'
import { SettingsPage } from '@/pages/settings-page'

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="chat" element={<ComingSoonPage />} />
        <Route path="summaries" element={<ComingSoonPage />} />
        <Route path="flashcards" element={<ComingSoonPage />} />
        <Route path="quizzes" element={<ComingSoonPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
