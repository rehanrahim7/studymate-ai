import { useRef, useState } from 'react'
import { FileUp, Loader2, UploadCloud } from 'lucide-react'

import { Progress } from '@/components/ui/progress'
import { useDocuments } from '@/hooks/use-documents'
import { cn } from '@/lib/utils'

/**
 * Drag-and-drop area for uploading PDFs.
 *
 * The actual file input lives in `DocumentsProvider` so the top bar and this
 * zone share one picker.
 */
export function UploadZone() {
  const { openPicker, handleFiles, upload, isUploading } = useDocuments()
  const [isDragging, setIsDragging] = useState(false)
  const dragDepth = useRef(0)

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload a PDF"
      onClick={() => !isUploading && openPicker()}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          if (!isUploading) openPicker()
        }
      }}
      onDragEnter={(event) => {
        event.preventDefault()
        dragDepth.current += 1
        setIsDragging(true)
      }}
      onDragOver={(event) => {
        event.preventDefault()
      }}
      onDragLeave={(event) => {
        event.preventDefault()
        dragDepth.current -= 1
        if (dragDepth.current <= 0) {
          dragDepth.current = 0
          setIsDragging(false)
        }
      }}
      onDrop={(event) => {
        event.preventDefault()
        dragDepth.current = 0
        setIsDragging(false)
        if (event.dataTransfer.files?.length) {
          void handleFiles(event.dataTransfer.files)
        }
      }}
      className={cn(
        'group relative flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed px-6 py-10 text-center transition-all duration-200',
        isDragging
          ? 'border-primary bg-primary-soft/60 shadow-glow'
          : 'border-border bg-secondary/40 hover:border-primary/45 hover:bg-secondary/70',
        isUploading && 'pointer-events-none opacity-90',
      )}
    >
      {isUploading && upload ? (
        <>
          <span className="flex size-11 items-center justify-center rounded-xl border border-primary/20 bg-primary-soft text-primary">
            <Loader2 className="size-5 animate-spin" />
          </span>
          <div className="w-full max-w-sm">
            <p className="truncate text-sm font-medium">{upload.fileName}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Extracting text and indexing pages… {upload.progress}%
            </p>
            <Progress value={upload.progress} className="mt-3" />
          </div>
        </>
      ) : (
        <>
          <span className="flex size-11 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground shadow-subtle transition-colors group-hover:border-primary/25 group-hover:text-primary">
            <UploadCloud className="size-5" />
          </span>
          <div>
            <p className="text-sm font-medium">Drop your PDF here</p>
            <p className="mt-1 text-xs text-muted-foreground">
              or click to browse — PDF only, up to 25 MB
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 text-[0.6875rem] font-medium uppercase tracking-wider text-muted-foreground/70">
            <FileUp className="size-3.5" />
            Text is extracted locally
          </span>
        </>
      )}
    </div>
  )
}
