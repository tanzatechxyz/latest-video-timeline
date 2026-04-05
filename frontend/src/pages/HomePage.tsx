import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ActionButton } from '../components/ActionButton'
import { StatCard } from '../components/StatCard'
import { usePolling } from '../hooks/usePolling'
import { api } from '../lib/api'
import { formatDuration, formatShortDate } from '../lib/format'

export function HomePage() {
  const navigate = useNavigate()
  const { data, loading, error, refresh } = usePolling(api.getDashboard, 8000, [])
  const latest = usePolling(async () => {
    const params = new URLSearchParams({ view: 'all', sort: 'latest_added', page: '1', page_size: '6' })
    return api.listVideos(params)
  }, 8000, [])
  const latestItems = useMemo(() => latest.data?.items ?? [], [latest.data])

  return <div className="stack-gap"><section className="hero card"><div><h2>Continue where you left off</h2><p className="muted">The queue favors oldest unfinished items and stores progress in the app database.</p></div><div className="hero-actions"><ActionButton label="Continue" tone="primary" onClick={() => navigate('/review')} disabled={!data?.continue_video_id} /><ActionButton label="Timeline" onClick={() => navigate('/timeline')} /><ActionButton label="Refresh" onClick={() => { void refresh(); void latest.refresh() }} /></div></section>{loading && !data ? <div className="card">Loading dashboard…</div> : null}{error ? <div className="error-banner">{error}</div> : null}{data ? <><section className="stats-grid"><StatCard label="Total videos" value={data.total_videos} /><StatCard label="Unfinished" value={data.unfinished_count} /><StatCard label="Watched" value={data.watched_count} /><StatCard label="Skipped" value={data.skipped_count} /><StatCard label="Bookmarked" value={data.bookmarked_count} /><StatCard label="Current position" value={data.current_queue_position ?? '—'} hint={data.queue_total ? `of ${data.queue_total}` : undefined} /></section><section className="card info-grid two-column"><div><div className="meta-label">Current item</div><div className="meta-value">{data.current_video_filename ?? 'None selected'}</div></div><div><div className="meta-label">Continue target</div><div className="meta-value">{data.continue_video_filename ?? 'Queue complete'}</div></div></section></> : null}<section className="card stack-gap"><div className="hero"><div><h2>Latest review</h2><p className="muted">Newest items added to the project, ready to open right away.</p></div><div className="hero-actions"><ActionButton label="See all in timeline" onClick={() => navigate('/timeline?sort=latest_added&view=all')} /></div></div>{latest.loading && !latest.data ? <div>Loading latest items…</div> : null}{latest.error ? <div className="error-banner">{latest.error}</div> : null}{latestItems.length ? <div className="grid-list">{latestItems.map((item) => <button key={item.id} className="card video-card" onClick={() => navigate(`/review/${item.id}?view=all`)}><div className="thumb-shell">{item.thumbnail_url ? <img src={item.thumbnail_url} alt="thumbnail" loading="lazy" /> : <div className="thumb-placeholder">No thumb</div>}</div><div className="video-card-body"><div className="video-title">{item.filename}</div><div className="video-meta">Added {formatShortDate(item.discovered_at)} · {formatDuration(item.duration_seconds)}</div><div className="video-badges"><span className="badge">{item.review_state}</span>{item.bookmarked ? <span className="badge">bookmarked</span> : null}{item.derived_sort_source ? <span className="badge">{item.derived_sort_source}</span> : null}</div></div></button>)}</div> : !latest.loading ? <div className="muted">No items found yet.</div> : null}</section></div>
}
