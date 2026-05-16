import { NavLink } from 'react-router-dom'

export function Layout({ children }: { children: React.ReactNode }) {
  return <div className="app-shell"><header className="topbar"><div><h1>Latest Video Timeline</h1><p className="muted">Newest folder videos first, with automatic rescans.</p></div><nav className="nav-tabs"><NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>Timeline</NavLink><NavLink to="/settings" className={({ isActive }) => (isActive ? 'active' : '')}>Settings</NavLink></nav></header><main className="content">{children}</main></div>
}
