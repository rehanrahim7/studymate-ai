import { cn } from '@/lib/utils'

/** A neutral placeholder block used while data is loading. */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-secondary/80', className)}
      {...props}
    />
  )
}

export { Skeleton }
