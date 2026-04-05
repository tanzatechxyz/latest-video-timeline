import { NavLink } from 'react-router-dom'

export function Layout({ children }: { children: React.ReactNode }) {
  return <div className="app-shell"><header className="topbar"><div><h1>Latest Review Queue</h1><p className="muted">Review the newest added items first, without losing your queue.</p></div><nav className="nav-tabs"><NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>Home</NavLink><NavLink to="/timeline" className={({ isActive }) => (isActive ? 'active' : '')}>Timeline</NavLink><NavLink to="/settings" className={({ isActive }) => (isActive ? 'active' : '')}>Settings</NavLink></nav></header><main className="content">{children}</main></div>
}
