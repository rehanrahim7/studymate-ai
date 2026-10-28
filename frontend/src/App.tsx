import { Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/layout/app-shell'
import { ChatPage } from '@/pages/chat-page'
import { DashboardPage } from '@/pages/dashboard-page'
import { DocumentsPage } from '@/pages/documents-page'
import { FlashcardsPage } from '@/pages/flashcards-page'
import { NotFoundPage } from '@/pages/not-found-page'
import { QuizzesPage } from '@/pages/quizzes-page'
import { SettingsPage } from '@/pages/settings-page'
import { StudyHistoryPage } from '@/pages/study-history-page'
import { SummariesPage } from '@/pages/summaries-page'

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="summaries" element={<SummariesPage />} />
        <Route path="flashcards" element={<FlashcardsPage />} />
        <Route path="quizzes" element={<QuizzesPage />} />
        <Route path="history" element={<StudyHistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
