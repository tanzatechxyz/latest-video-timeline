import { useEffect, useMemo, useRef, useState } from 'react'
import { ActionButton } from '../components/ActionButton'
import { api } from '../lib/api'
import { formatDate, formatDuration, formatShortDate } from '../lib/format'
import type { ScanStatusResponse, VideoSummary } from '../types'

const PAGE_SIZE = 120

function videoDate(video: VideoSummary): string | null {
  return video.derived_sort_date ?? video.modified_time ?? video.discovered_at
}

export function HomePage() {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [videos, setVideos] = useState<VideoSummary[]>([])
  const [activeIndex, setActiveIndex] = useState(0)
  const [scanStatus, setScanStatus] = useState<ScanStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [rescanning, setRescanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const activeVideo = videos[activeIndex] ?? null
  const activeDate = activeVideo ? videoDate(activeVideo) : null
  const streamUrl = activeVideo ? `/api/videos/${activeVideo.id}/stream` : ''

  async function loadLatest() {
    setError(null)
    const params = new URLSearchParams({ view: 'all', sort: 'newest', page: '1', page_size: String(PAGE_SIZE) })
    const [videoResponse, statusResponse] = await Promise.all([api.listVideos(params), api.getScanStatus()])
    setVideos(videoResponse.items)
    setScanStatus(statusResponse)
    setActiveIndex((current) => Math.min(current, Math.max(videoResponse.items.length - 1, 0)))
  }

  useEffect(() => {
    let active = true
    async function load() {
      setLoading(true)
      try {
        await loadLatest()
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load latest videos')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    const timer = window.setInterval(() => { void loadLatest().catch(() => undefined) }, 30000)
    return () => { active = false; window.clearInterval(timer) }
  }, [])

  const grouped = useMemo(() => {
    const groups = new Map<string, VideoSummary[]>()
    for (const video of videos) {
      const label = videoDate(video) ? new Date(videoDate(video) as string).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : 'Unknown date'
      const group = groups.get(label) ?? []
      group.push(video)
      groups.set(label, group)
    }
    return Array.from(groups.entries())
  }, [videos])

  const playAt = (index: number) => {
    setActiveIndex(index)
    window.requestAnimationFrame(() => videoRef.current?.play().catch(() => undefined))
  }

  const playNext = () => {
    if (activeIndex < videos.length - 1) playAt(activeIndex + 1)
  }

  const playPrevious = () => {
    if (activeIndex > 0) playAt(activeIndex - 1)
  }

  const rescan = async () => {
    setRescanning(true)
    setError(null)
    try {
      await api.startScan()
      const status = await api.getScanStatus()
      setScanStatus({ ...status, is_running: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scan')
    } finally {
      setRescanning(false)
    }
  }

  return <div className="timeline-player">
    <section className="player-panel">
      <div className="player-toolbar">
        <div>
          <h2>{activeVideo?.filename ?? 'Latest videos'}</h2>
          <p className="muted">{activeVideo ? `${formatDate(activeDate)} · ${formatDuration(activeVideo.duration_seconds)}` : 'Point Docker at a video folder and scan to populate the timeline.'}</p>
        </div>
        <div className="hero-actions">
          <ActionButton label="Rescan" tone="primary" onClick={() => void rescan()} disabled={rescanning || Boolean(scanStatus?.is_running)} />
          <ActionButton label="Refresh" onClick={() => void loadLatest().catch((err) => setError(err instanceof Error ? err.message : 'Failed to refresh'))} />
        </div>
      </div>
      {loading ? <div className="card">Loading latest videos...</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}
      {activeVideo ? <div className="video-stage">
        <video key={activeVideo.id} ref={videoRef} src={streamUrl} controls playsInline autoPlay preload="metadata" onEnded={playNext} />
      </div> : !loading ? <div className="empty-state">No videos found. Check the mounted folder and run a scan.</div> : null}
      <div className="transport-row">
        <ActionButton label="Previous" onClick={playPrevious} disabled={activeIndex <= 0} />
        <div className="transport-count">{videos.length ? `${activeIndex + 1} of ${videos.length}` : '0 videos'}</div>
        <ActionButton label="Next" onClick={playNext} disabled={activeIndex >= videos.length - 1} />
      </div>
      <div className="scan-line">
        Scan: {scanStatus?.is_running ? 'running' : scanStatus?.status ?? 'idle'}
        {scanStatus?.finished_at ? ` · last finished ${formatShortDate(scanStatus.finished_at)}` : ''}
        {scanStatus?.total_files ? ` · ${scanStatus.total_files} files` : ''}
      </div>
    </section>

    <aside className="timeline-panel">
      <div className="timeline-header">
        <h2>Timeline</h2>
        <span className="badge">newest first</span>
      </div>
      <div className="timeline-list">
        {grouped.map(([label, items]) => <section key={label} className="timeline-group">
          <h3>{label}</h3>
          {items.map((video) => {
            const index = videos.findIndex((item) => item.id === video.id)
            return <button key={video.id} className={`timeline-item ${index === activeIndex ? 'active' : ''}`} onClick={() => playAt(index)}>
              <span className="timeline-thumb">{video.thumbnail_url ? <img src={video.thumbnail_url} alt="" loading="lazy" /> : video.extension.replace('.', '').toUpperCase()}</span>
              <span>
                <strong>{video.filename}</strong>
                <small>{formatDuration(video.duration_seconds)}</small>
              </span>
            </button>
          })}
        </section>)}
      </div>
    </aside>
  </div>
}
