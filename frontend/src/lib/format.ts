/** Small formatting helpers shared across the UI. */

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB'] as const

/** Format a byte count for display, e.g. `1.4 MB`. */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), BYTE_UNITS.length - 1)
  const value = bytes / 1024 ** exponent
  const digits = exponent === 0 ? 0 : value < 10 ? 1 : 0
  return `${value.toFixed(digits)} ${BYTE_UNITS[exponent]}`
}

/** Format an ISO timestamp as `12 Mar 2025`. */
export function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

/** Format an ISO timestamp relative to now, e.g. `3 minutes ago`. */
export function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'

  const seconds = Math.round((Date.now() - date.getTime()) / 1000)
  if (seconds < 45) return 'just now'

  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['minute', 60],
    ['hour', 3600],
    ['day', 86400],
    ['week', 604800],
    ['month', 2592000],
    ['year', 31536000],
  ]

  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  let chosen: [Intl.RelativeTimeFormatUnit, number] = units[0]

  for (const unit of units) {
    if (Math.abs(seconds) >= unit[1]) chosen = unit
  }

  return formatter.format(-Math.round(seconds / chosen[1]), chosen[0])
}

/** Compact a large number for stat tiles, e.g. `12.4k`. */
export function formatCompact(value: number): string {
  if (!Number.isFinite(value)) return '0'
  if (Math.abs(value) < 1000) return String(value)
  return new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(
    value,
  )
}

/** Format a saved study-set timestamp with both date and time. */
export function formatStudyDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}
