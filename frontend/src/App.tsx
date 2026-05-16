import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { LoginScreen } from './components/LoginScreen'
import { api } from './lib/api'
import { HomePage } from './pages/HomePage'
import { SettingsPage } from './pages/SettingsPage'
import { TimelinePage } from './pages/TimelinePage'

export default function App() {
  const [authEnabled, setAuthEnabled] = useState<boolean | null>(null)
  const [authenticated, setAuthenticated] = useState(false)
  useEffect(() => { let active = true; api.getPublicConfig().then((response) => { if (!active) return; setAuthEnabled(response.auth_enabled); if (!response.auth_enabled) setAuthenticated(true); else setAuthenticated(Boolean(localStorage.getItem('reviewQueueToken'))) }).catch(() => { if (!active) return; setAuthEnabled(false); setAuthenticated(true) }); return () => { active = false } }, [])
  if (authEnabled === null) return <div className="login-shell"><div className="card">Loading…</div></div>
  if (authEnabled && !authenticated) return <LoginScreen onSuccess={() => setAuthenticated(true)} />
  return <Layout><Routes><Route path="/" element={<HomePage />} /><Route path="/timeline" element={<TimelinePage />} /><Route path="/settings" element={<SettingsPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></Layout>
}
