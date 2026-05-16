import { useEffect, useState } from 'react'
import { ActionButton } from '../components/ActionButton'
import { api } from '../lib/api'
import type { ScanStatusResponse, SettingsResponse } from '../types'

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [scan, setScan] = useState<ScanStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const [settingsResponse, scanResponse] = await Promise.all([api.getSettings(), api.getScanStatus()])
        if (active) { setSettings(settingsResponse); setScan(scanResponse) }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load settings')
      }
    }
    void load()
    const timer = window.setInterval(load, 5000)
    return () => { active = false; window.clearInterval(timer) }
  }, [])

  const saveSettings = async () => {
    if (!settings) return
    setSaving(true)
    setError(null)
    try {
      const response = await api.updateSettings(settings)
      setSettings(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const triggerScan = async () => {
    try {
      await api.startScan()
      setScan({ ...(await api.getScanStatus()), is_running: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scan')
    }
  }

  return <div className="stack-gap">
    {error ? <div className="error-banner">{error}</div> : null}
    {settings ? <section className="card settings-form">
      <h2>Settings</h2>
      <label><span>Root folder</span><input value={settings.root_folder} onChange={(e) => setSettings({ ...settings, root_folder: e.target.value })} /></label>
      <label><span>Supported extensions</span><input value={settings.supported_extensions.join(',')} onChange={(e) => setSettings({ ...settings, supported_extensions: e.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} /></label>
      <label><span>Sort priority</span><input value={settings.sort_priority.join(',')} onChange={(e) => setSettings({ ...settings, sort_priority: e.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} /></label>
      <label className="toggle-row"><input type="checkbox" checked={settings.generate_thumbnails} onChange={(e) => setSettings({ ...settings, generate_thumbnails: e.target.checked })} /><span>Generate thumbnails</span></label>
      <div className="two-column">
        <label><span>Thumbnail second</span><input type="number" min="1" value={settings.thumbnail_interval_seconds} onChange={(e) => setSettings({ ...settings, thumbnail_interval_seconds: Number(e.target.value) })} /></label>
        <label><span>Thumbnail width</span><input type="number" min="64" value={settings.thumbnail_width} onChange={(e) => setSettings({ ...settings, thumbnail_width: Number(e.target.value) })} /></label>
      </div>
      <div className="hero-actions"><ActionButton label={saving ? 'Saving...' : 'Save settings'} tone="primary" onClick={() => void saveSettings()} disabled={saving} /><ActionButton label="Trigger rescan" onClick={() => void triggerScan()} /></div>
    </section> : null}
    {scan ? <section className="card info-grid two-column">
      <div><div className="meta-label">Scan status</div><div className="meta-value">{scan.status}{scan.is_running ? ' (running)' : ''}</div></div>
      <div><div className="meta-label">Progress</div><div className="meta-value">{scan.scanned_files} / {scan.total_files}</div></div>
      <div><div className="meta-label">Added / updated / renamed</div><div className="meta-value">{scan.added_files} / {scan.updated_files} / {scan.renamed_files}</div></div>
      <div><div className="meta-label">Removed / errors</div><div className="meta-value">{scan.removed_files} / {scan.error_count}</div></div>
      <div><div className="meta-label">Message</div><div className="meta-value">{scan.message ?? '-'}</div></div>
      <div><div className="meta-label">Error details</div><div className="meta-value pre-wrap">{scan.error_details ?? '-'}</div></div>
    </section> : null}
  </div>
}
