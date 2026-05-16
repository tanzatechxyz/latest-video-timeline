import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
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
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedVideoId = searchParams.get('video')
  const [videos, setVideos] = useState<VideoSummary[]>([])
  const [activeIndex, setActiveIndex] = useState(0)
  const [scanStatus, setScanStatus] = useState<ScanStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [rescanning, setRescanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const activeVideo = videos[activeIndex] ?? null
  const activeDate = activeVideo ? videoDate(activeVideo) : null
  const streamUrl = activeVideo ? '/api/videos/' + activeVideo.id + '/stream' : ''

  async function loadLatest() {
    setError(null)
    const params = new URLSearchParams({ view: 'all', sort: 'newest', page: '1', page_size: String(PAGE_SIZE) })
    const [videoResponse, statusResponse] = await Promise.all([api.listVideos(params), api.getScanStatus()])
    setVideos(videoResponse.items)
    setScanStatus(statusResponse)
    setActiveIndex((current) => {
      const requestedIndex = requestedVideoId ? videoResponse.items.findIndex((video) => video.id === requestedVideoId) : -1
      if (requestedIndex >= 0) return requestedIndex
      return Math.min(current, Math.max(videoResponse.items.length - 1, 0))
    })
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
  }, [requestedVideoId])

  const playAt = (index: number) => {
    const target = videos[index]
    if (!target) return
    setActiveIndex(index)
    setSearchParams({ video: target.id }, { replace: true })
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

  return <div className="player-page">
    <section className="player-panel player-panel-wide">
      <div className="player-toolbar">
        <div>
          <h2>{activeVideo?.filename ?? 'Latest videos'}</h2>
          <p className="muted">{activeVideo ? formatDate(activeDate) + ' · ' + formatDuration(activeVideo.duration_seconds) : 'Point Docker at a video folder and scan to populate the timeline.'}</p>
        </div>
        <div className="hero-actions">
          <Link className="action-link" to="/timeline">Timeline</Link>
          <ActionButton label="Rescan" tone="primary" onClick={() => void rescan()} disabled={rescanning || Boolean(scanStatus?.is_running)} />
          <ActionButton label="Refresh" onClick={() => void loadLatest().catch((err) => setError(err instanceof Error ? err.message : 'Failed to refresh'))} />
        </div>
      </div>
      {loading ? <div className="card">Loading latest videos...</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}
      {activeVideo ? <div className="video-stage video-stage-large">
        <video key={activeVideo.id} ref={videoRef} src={streamUrl} controls playsInline autoPlay preload="metadata" onEnded={playNext} />
      </div> : !loading ? <div className="empty-state">No videos found. Check the mounted folder and run a scan.</div> : null}
      <div className="transport-row">
        <ActionButton label="Previous" onClick={playPrevious} disabled={activeIndex <= 0} />
        <div className="transport-count">{videos.length ? String(activeIndex + 1) + ' of ' + String(videos.length) : '0 videos'}</div>
        <ActionButton label="Next" onClick={playNext} disabled={activeIndex >= videos.length - 1} />
      </div>
      <div className="scan-line">
        Scan: {scanStatus?.is_running ? 'running' : scanStatus?.status ?? 'idle'}
        {scanStatus?.finished_at ? ' · last finished ' + formatShortDate(scanStatus.finished_at) : ''}
        {scanStatus?.total_files ? ' · ' + String(scanStatus.total_files) + ' files' : ''}
      </div>
    </section>
  </div>
}
