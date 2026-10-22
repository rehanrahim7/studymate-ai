import { Laptop, Moon, Sun } from 'lucide-react'

import { useTheme, type Theme } from '@/hooks/use-theme'
import { cn } from '@/lib/utils'

const OPTIONS: Array<{ value: Theme; label: string; icon: typeof Sun }> = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Laptop },
]

/** A three-way segmented control for the appearance settings. */
export function ThemeSegmentedControl() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="inline-flex rounded-lg border border-border bg-secondary/60 p-1">
      {OPTIONS.map((option) => {
        const isActive = theme === option.value
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => setTheme(option.value)}
            aria-pressed={isActive}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all',
              isActive
                ? 'bg-card text-foreground shadow-subtle'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <option.icon className="size-4" />
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
