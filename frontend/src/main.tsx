import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { App } from '@/App'
import { HealthProvider } from '@/components/health/health-provider'
import { DocumentsProvider } from '@/components/documents/documents-provider'
import { ThemeProvider } from '@/components/theme/theme-provider'
import { TooltipProvider } from '@/components/ui/tooltip'
import '@/index.css'

const container = document.getElementById('root')
if (!container) {
  throw new Error('Root element #root was not found in index.html')
}

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <HealthProvider>
          <DocumentsProvider>
            <TooltipProvider delayDuration={150}>
              <App />
            </TooltipProvider>
          </DocumentsProvider>
        </HealthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
)
