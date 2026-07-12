import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { Pill } from './ui'

const NAV = [
  { to: '/', label: 'Dashboard', icon: '📊', end: true },
  { to: '/carbon', label: 'Carbon', icon: '🏭' },
  { to: '/csr', label: 'CSR Activities', icon: '🤝' },
  { to: '/challenges', label: 'Challenges', icon: '🎯' },
  { to: '/governance', label: 'Governance', icon: '⚖️' },
  { to: '/copilot', label: 'Ask EcoPilot', icon: '🤖' },
  { to: '/report', label: 'ESG Report', icon: '📄' },
  { to: '/companies', label: 'Company Ranking', icon: '🏢' },
  { to: '/admin', label: 'Data Management', icon: '🗂️', managerOnly: true },
]

function Notifications() {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState([])
  const load = () => api.get('/notifications').then(setItems).catch(() => {})
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t) }, [])
  const unread = items.filter((n) => !n.is_read).length

  const markAll = async () => { await api.post('/notifications/read-all'); load() }

  return (
    <div className="relative">
      <button className="relative text-xl" onClick={() => setOpen((o) => !o)}>
        🔔
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] font-bold
                           h-4 w-4 rounded-full flex items-center justify-center">{unread}</span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 card p-0 overflow-hidden z-50">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
            <span className="font-semibold text-sm">Notifications</span>
            <button className="text-xs text-brand-600 font-semibold" onClick={markAll}>Mark all read</button>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 && <div className="p-4 text-sm text-slate-400">No notifications</div>}
            {items.map((n) => (
              <div key={n.id} className={`px-4 py-3 border-b border-slate-50 ${n.is_read ? 'opacity-60' : ''}`}>
                <div className="text-sm font-semibold text-slate-800">{n.title}</div>
                {n.message && <div className="text-xs text-slate-500">{n.message}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Layout({ children }) {
  const { user, logout, isManager } = useAuth()
  const nav = NAV.filter((n) => !n.managerOnly || isManager)
  const location = useLocation()
  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-60 bg-gradient-to-b from-brand-800 via-brand-800 to-brand-900 text-white flex flex-col fixed inset-y-0 shadow-2xl z-30">
        <div className="px-5 py-5 flex items-center gap-2 border-b border-white/10">
          <span className="text-2xl">🌱</span>
          <div>
            <div className="font-extrabold text-lg leading-none">EcoPilot</div>
            <div className="text-[10px] text-brand-200 uppercase tracking-wider truncate max-w-[140px]">
              {user?.company?.name || 'ESG Platform'}
            </div>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-white/15 text-white ring-1 ring-white/20 shadow-[0_4px_16px_-6px_rgba(0,0,0,.4)]'
                    : 'text-brand-100 hover:bg-white/10 hover:translate-x-0.5'
                }`}>
              <span className="text-base">{n.icon}</span>{n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 text-[11px] text-brand-300 border-t border-brand-700">
          Odoo Hackathon 2026
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 ml-60">
        <header className="h-16 bg-white/60 backdrop-blur-xl border-b border-white/50 flex items-center justify-between px-6 sticky top-0 z-40">
          <div className="text-sm text-slate-400">Welcome back, <span className="font-semibold text-slate-700">{user?.full_name}</span></div>
          <div className="flex items-center gap-5">
            <Notifications />
            <div className="flex items-center gap-2">
              <div className="text-right">
                <div className="text-sm font-semibold text-slate-700">{user?.full_name}</div>
                <div className="text-xs text-slate-400">{user?.role}</div>
              </div>
              <Pill color="green">⭐ {user?.xp ?? 0} XP</Pill>
              <Pill color="blue">🪙 {user?.points_balance ?? 0}</Pill>
            </div>
            <button className="btn-ghost" onClick={logout}>Logout</button>
          </div>
        </header>
        <main key={location.pathname} className="p-6 max-w-7xl mx-auto animate-float-in">{children}</main>
      </div>
    </div>
  )
}
