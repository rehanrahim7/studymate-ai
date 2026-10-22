import { useCallback, useEffect, useMemo, useState } from 'react'

import { checkHealth } from '@/lib/api'
import { HealthContext, type HealthContextValue } from '@/hooks/use-health'
import type { HealthResponse } from '@/types'

/**
 * Fetches `/health` once and shares the result with every consumer.
 *
 * Components read the state through `useHealth()` instead of calling the API.
 */
export function HealthProvider({ children }: { children: React.ReactNode }) {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setHealth(await checkHealth())
      setError(null)
    } catch (cause) {
      setHealth(null)
      setError(cause instanceof Error ? cause.message : 'Health check failed.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    // Initial load on mount — the state update happens after the request resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh()
  }, [refresh])

  const reload = useCallback(async () => {
    setIsLoading(true)
    await refresh()
  }, [refresh])

  const value = useMemo<HealthContextValue>(
    () => ({ health, isLoading, error, refresh: reload }),
    [health, isLoading, error, reload],
  )

  return <HealthContext.Provider value={value}>{children}</HealthContext.Provider>
}
