import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ActionButton } from '../components/ActionButton'
import { api } from '../lib/api'
import { formatDuration } from '../lib/format'
import type { VideoSummary } from '../types'

const PAGE_SIZE = 240

function videoDate(video: VideoSummary): string | null {
  return video.derived_sort_date ?? video.modified_time ?? video.discovered_at
}

export function TimelinePage() {
  const [videos, setVideos] = useState<VideoSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadTimeline() {
    setError(null)
    const params = new URLSearchParams({ view: 'all', sort: 'newest', page: '1', page_size: String(PAGE_SIZE) })
    const response = await api.listVideos(params)
    setVideos(response.items)
  }

  useEffect(() => {
    let active = true
    async function load() {
      setLoading(true)
      try {
        await loadTimeline()
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load timeline')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => { active = false }
  }, [])

  const grouped = useMemo(() => {
    const groups = new Map<string, VideoSummary[]>()
    for (const video of videos) {
      const value = videoDate(video)
      const label = value ? new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : 'Unknown date'
      const group = groups.get(label) ?? []
      group.push(video)
      groups.set(label, group)
    }
    return Array.from(groups.entries())
  }, [videos])

  return <div className="timeline-page">
    <section className="timeline-panel timeline-panel-full">
      <div className="timeline-header">
        <div>
          <h2>Timeline</h2>
          <p className="muted">Newest videos first. Open an item to play it full-width.</p>
        </div>
        <div className="hero-actions">
          <Link className="action-link primary" to="/">Player</Link>
          <ActionButton label="Refresh" onClick={() => void loadTimeline().catch((err) => setError(err instanceof Error ? err.message : 'Failed to refresh'))} />
        </div>
      </div>
      {loading ? <div className="card">Loading timeline...</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}
      <div className="timeline-list timeline-list-full">
        {grouped.map(([label, items]) => <section key={label} className="timeline-group">
          <h3>{label}</h3>
          {items.map((video) => <Link key={video.id} className="timeline-item" to={'/?video=' + encodeURIComponent(video.id)}>
            <span className="timeline-thumb">{video.thumbnail_url ? <img src={video.thumbnail_url} alt="" loading="lazy" /> : video.extension.replace('.', '').toUpperCase()}</span>
            <span>
              <strong>{video.filename}</strong>
              <small>{formatDuration(video.duration_seconds)}</small>
            </span>
          </Link>)}
        </section>)}
      </div>
    </section>
  </div>
}
