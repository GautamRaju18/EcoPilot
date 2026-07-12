import { useState } from 'react'
import { api } from '../api'
import { usePolling } from '../hooks'
import { useAuth } from '../auth'
import Onboarding from '../components/Onboarding'
import { Bar, ScoreRing, Spinner, StatCard, Empty } from '../components/ui'

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [board, setBoard] = useState([])
  const [ai, setAi] = useState(null)
  const key = `ecopilot_onboarded_${user?.company_id || ''}`
  const [dismissed, setDismissed] = useState(() => !!localStorage.getItem(key))

  const load = () => {
    api.get('/scores/overview').then(setData).catch(() => {})
    api.get('/leaderboard').then(setBoard).catch(() => {})
    api.get('/ai/status').then(setAi).catch(() => {})
  }
  // Live: re-poll every 6s so scores/leaderboard update as data changes elsewhere.
  usePolling(load, 6000)

  if (!data) return <Spinner />
  const o = data.overall
  const isEmpty = Array.isArray(data.departments) && data.departments.length === 0
  const showOnboarding = isEmpty && !dismissed

  return (
    <div className="space-y-6">
      {showOnboarding && (
        <Onboarding
          companyName={user?.company?.name}
          onDone={() => { setDismissed(true); load() }}
          onDismiss={() => { localStorage.setItem(key, '1'); setDismissed(true) }}
        />
      )}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            ESG Dashboard
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600">
              <span className="h-2 w-2 rounded-full bg-brand-500 animate-pulse" /> Live
            </span>
          </h1>
          <p className="text-sm text-slate-400">Organisation-wide sustainability performance · auto-refreshing</p>
        </div>
        {ai && (
          <div className="text-xs text-slate-400">
            AI provider: <span className="font-semibold text-slate-600">{ai.provider}</span> ·
            retrieval: <span className="font-semibold text-slate-600">{ai.retrieval_backend}</span>
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Overall gauge */}
        <div className="card flex flex-col items-center justify-center shadow-[0_10px_44px_-14px_rgba(16,185,129,.4)]">
          <ScoreRing value={o.overall} />
          <div className="text-sm text-slate-500 mt-2">Weighted 40 / 30 / 30</div>
        </div>

        {/* Pillar bars */}
        <div className="card lg:col-span-2 flex flex-col justify-center gap-4">
          <h3 className="font-semibold text-slate-700">ESG Pillars</h3>
          <Bar label="🌍 Environmental (40%)" value={o.environmental} />
          <Bar label="🤝 Social (30%)" value={o.social} />
          <Bar label="⚖️ Governance (30%)" value={o.governance} />
        </div>
      </div>

      {/* Department scores */}
      <div className="card">
        <h3 className="font-semibold text-slate-700 mb-4">Department Scorecards</h3>
        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
          {data.departments.map((d) => (
            <div key={d.department_id} className="glass lift rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="font-semibold text-slate-700">{d.department}</span>
                <span className="text-lg font-extrabold text-brand-600">{d.total}</span>
              </div>
              <div className="space-y-2">
                <Bar label="E" value={d.environmental} />
                <Bar label="S" value={d.social} />
                <Bar label="G" value={d.governance} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Leaderboard preview */}
      <div className="card">
        <h3 className="font-semibold text-slate-700 mb-3">🏆 Sustainability Leaderboard</h3>
        {board.length === 0 ? <Empty /> : (
          <table className="w-full">
            <thead><tr>
              <th className="th">#</th><th className="th">Employee</th><th className="th">Dept</th>
              <th className="th">XP</th><th className="th">Challenges</th><th className="th">Badges</th>
            </tr></thead>
            <tbody>
              {board.slice(0, 6).map((u, i) => (
                <tr key={u.user_id}>
                  <td className="td font-bold text-slate-400">{i + 1}</td>
                  <td className="td font-semibold text-slate-700">{u.full_name}</td>
                  <td className="td text-slate-500">{u.department || '—'}</td>
                  <td className="td">⭐ {u.xp}</td>
                  <td className="td">{u.completed_challenges}</td>
                  <td className="td">{u.badge_count} 🏅</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
