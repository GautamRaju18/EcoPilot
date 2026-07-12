import { useState } from 'react'
import { api } from '../api'
import { usePolling } from '../hooks'
import { useAuth } from '../auth'
import { Bar, Empty, Spinner } from '../components/ui'

export default function Companies() {
  const { user } = useAuth()
  const [rows, setRows] = useState(null)
  usePolling(() => api.get('/companies/leaderboard').then(setRows).catch(() => setRows([])), 8000)

  if (!rows) return <Spinner />
  const medal = (i) => ['🥇', '🥈', '🥉'][i] || `#${i + 1}`

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Cross-Company ESG Ranking</h1>
        <p className="text-sm text-slate-400">How every organisation on EcoPilot compares — weighted 40 / 30 / 30.</p>
      </div>

      {rows.length === 0 ? <Empty /> : (
        <div className="grid lg:grid-cols-2 gap-4">
          {rows.map((c, i) => {
            const mine = c.company_id === user?.company_id
            return (
              <div key={c.company_id} className={`card ${mine ? 'ring-2 ring-brand-400' : ''}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{medal(i)}</span>
                    <div>
                      <div className="font-bold text-slate-800">
                        {c.name} {mine && <span className="pill bg-brand-100 text-brand-700 ml-1">You</span>}
                      </div>
                      <div className="text-xs text-slate-400">{c.industry || '—'} · {c.employees} employees</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-extrabold text-brand-600">{c.overall}</div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-400">Overall</div>
                  </div>
                </div>
                <div className="space-y-2">
                  <Bar label="🌍 Environmental" value={c.environmental} />
                  <Bar label="🤝 Social" value={c.social} />
                  <Bar label="⚖️ Governance" value={c.governance} />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
