import { createContext, useContext } from 'react'

import type { HealthResponse } from '@/types'

export interface HealthContextValue {
  health: HealthResponse | null
  isLoading: boolean
  error: string | null
  refresh: () => Promise<void>
}

export const HealthContext = createContext<HealthContextValue | null>(null)

/** Access the shared API health state. Must be used inside `<HealthProvider>`. */
export function useHealth(): HealthContextValue {
  const context = useContext(HealthContext)
  if (!context) {
    throw new Error('useHealth must be used within a HealthProvider')
  }
  return context
}
