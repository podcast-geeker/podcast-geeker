'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Download, Pause, Play } from 'lucide-react'
import { useTheme } from 'next-themes'
import WaveSurfer from 'wavesurfer.js'

import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'
import { cn } from '@/lib/utils'

function formatTime(seconds: number): string {
  const s = Math.floor(seconds % 60)
  const m = Math.floor(seconds / 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function safeFileName(name: string): string {
  const trimmed = name.replace(/[/\\?%*:|"<>]/g, '_').trim()
  return trimmed || 'episode'
}

/** WaveSurfer.destroy() aborts in-flight fetch; that must not be shown as a load failure. */
function isBenignWaveSurferAbort(err: unknown): boolean {
  if (err instanceof DOMException && err.name === 'AbortError') return true
  if (err instanceof Error && err.name === 'AbortError') return true
  if (typeof err === 'object' && err !== null && 'name' in err) {
    const n = (err as { name?: string }).name
    if (n === 'AbortError') return true
  }
  if (err instanceof Error && /aborted|abort/i.test(err.message)) return true
  return false
}

export interface WaveformPlayerProps {
  audioSrc: string
  /** Used for download filename; optional visible heading when `showTitle` is true */
  title?: string
  showTitle?: boolean
  variant?: 'default' | 'compact'
  className?: string
}

export function WaveformPlayer({
  audioSrc,
  title,
  showTitle = false,
  variant = 'default',
  className,
}: WaveformPlayerProps) {
  const { t } = useTranslation()
  const { resolvedTheme } = useTheme()
  const containerRef = useRef<HTMLDivElement>(null)
  const wavesurferRef = useRef<WaveSurfer | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState('0:00')
  const [duration, setDuration] = useState('0:00')
  const [isReady, setIsReady] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const height = variant === 'compact' ? 80 : 112

  const colors = useMemo(() => {
    const dark = resolvedTheme === 'dark'
    return {
      waveColor: dark ? '#a855f7' : '#9333ea',
      progressColor: dark ? '#7c3aed' : '#6b21a8',
      cursorColor: dark ? '#fafafa' : '#171717',
    }
  }, [resolvedTheme])

  const colorsRef = useRef(colors)
  colorsRef.current = colors
  const tRef = useRef(t)
  tRef.current = t

  useEffect(() => {
    if (typeof window === 'undefined') return
    const container = containerRef.current
    if (!container) return

    setIsReady(false)
    setLoadError(null)
    setCurrentTime('0:00')
    setDuration('0:00')
    setIsPlaying(false)

    const c = colorsRef.current
    const wavesurfer = WaveSurfer.create({
      container,
      waveColor: c.waveColor,
      progressColor: c.progressColor,
      cursorColor: c.cursorColor,
      barWidth: 3,
      barGap: 2,
      barRadius: 4,
      height,
      url: audioSrc,
      backend: 'MediaElement',
      normalize: true,
    })

    wavesurferRef.current = wavesurfer

    wavesurfer.on('ready', (dur) => {
      setIsReady(true)
      setDuration(formatTime(dur))
    })

    wavesurfer.on('timeupdate', (current) => {
      setCurrentTime(formatTime(current))
    })

    wavesurfer.on('play', () => setIsPlaying(true))
    wavesurfer.on('pause', () => setIsPlaying(false))
    wavesurfer.on('finish', () => setIsPlaying(false))

    wavesurfer.on('error', (err) => {
      if (isBenignWaveSurferAbort(err)) {
        return
      }
      console.error('WaveformPlayer load error', err)
      setLoadError(tRef.current.podcasts.audioUnavailable)
      setIsReady(false)
    })

    return () => {
      wavesurfer.destroy()
      wavesurferRef.current = null
    }
  }, [audioSrc, height])

  useEffect(() => {
    const ws = wavesurferRef.current
    if (!ws || !isReady) return
    ws.setOptions({
      waveColor: colors.waveColor,
      progressColor: colors.progressColor,
      cursorColor: colors.cursorColor,
    })
  }, [colors.waveColor, colors.progressColor, colors.cursorColor, isReady])

  const togglePlay = () => {
    if (!wavesurferRef.current || !isReady) return
    void wavesurferRef.current.playPause()
  }

  const handleDownload = () => {
    const link = document.createElement('a')
    link.href = audioSrc
    link.download = `${safeFileName(title ?? 'episode')}.mp3`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div
      className={cn(
        'w-full rounded-lg border border-border bg-muted/30 p-3 shadow-sm',
        className
      )}
    >
      {showTitle && title ? (
        <p className="mb-2 truncate text-sm font-medium text-foreground">{title}</p>
      ) : null}

      <div ref={containerRef} className="w-full overflow-hidden rounded-md" />

      {loadError ? (
        <p className="mt-2 text-sm text-destructive">{loadError}</p>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button
          type="button"
          size="icon"
          variant="default"
          disabled={!isReady}
          aria-label={isPlaying ? t.podcasts.pauseAudio : t.podcasts.playAudio}
          onClick={togglePlay}
        >
          {isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4 ml-0.5" />
          )}
        </Button>

        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {currentTime} / {duration}
        </span>

        <Button
          type="button"
          size="sm"
          variant="outline"
          className="ml-auto"
          disabled={!isReady}
          onClick={handleDownload}
        >
          <Download className="mr-2 h-4 w-4" />
          {t.common.download}
        </Button>
      </div>

      {!isReady && !loadError ? (
        <p className="mt-2 text-center text-xs text-muted-foreground">
          {t.podcasts.waveformLoading}
        </p>
      ) : null}
    </div>
  )
}
