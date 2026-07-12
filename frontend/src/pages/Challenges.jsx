import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Empty, Pill, Spinner, StatusPill } from '../components/ui'

const STATUSES = ['Draft', 'Active', 'Under Review', 'Completed', 'Archived']
const DIFF_COLOR = { Easy: 'green', Medium: 'amber', Hard: 'red' }

export default function Challenges() {
  const { isManager } = useAuth()
  const [challenges, setChallenges] = useState(null)
  const [parts, setParts] = useState([])
  const [board, setBoard] = useState([])
  const [badges, setBadges] = useState([])
  const [users, setUsers] = useState([])

  const load = () => {
    api.get('/challenges').then(setChallenges)
    api.get('/challenges/participations').then(setParts)
    api.get('/leaderboard').then(setBoard)
    api.get('/my-badges').then(setBadges).catch(() => {})
    api.get('/users').then(setUsers).catch(() => {})
  }
  useEffect(load, [])

  const userName = (id) => users.find((u) => u.id === id)?.full_name || `#${id}`
  const chTitle = (id) => challenges?.find((c) => c.id === id)?.title || `#${id}`

  const setStatus = async (id, status) => {
    try { await api.post(`/challenges/${id}/status`, { status }); load() } catch (e) { alert(e.message) }
  }
  const join = (id) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.onchange = async () => {
      const fd = new FormData()
      if (input.files[0]) fd.append('proof', input.files[0])
      try { await api.postForm(`/challenges/${id}/join`, fd); load() } catch (e) { alert(e.message) }
    }
    input.click()
  }
  const decide = async (id, action) => {
    try { await api.post(`/challenges/participations/${id}/${action}`); load() } catch (e) { alert(e.message) }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Sustainability Challenges</h1>
        <p className="text-sm text-slate-400">Complete challenges to earn XP and unlock badges — approvals award XP instantly.</p>
      </div>

      {/* Challenge cards */}
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
        {!challenges ? <Spinner /> : challenges.map((c) => (
          <div key={c.id} className="card">
            <div className="flex items-start justify-between">
              <h3 className="font-semibold text-slate-800">{c.title}</h3>
              <Pill color="violet">⭐ {c.xp} XP</Pill>
            </div>
            <p className="text-sm text-slate-500 mt-1 mb-3">{c.description}</p>
            <div className="flex items-center gap-2 mb-3">
              <Pill color={DIFF_COLOR[c.difficulty]}>{c.difficulty}</Pill>
              <StatusPill status={c.status} />
              {c.evidence_required && <Pill color="slate">📎 proof</Pill>}
            </div>
            <div className="flex gap-2">
              {c.status === 'Active' && <button className="btn-primary flex-1" onClick={() => join(c.id)}>Join</button>}
              {isManager && (
                <select className="input !w-auto text-xs" value={c.status}
                  onChange={(e) => setStatus(c.id, e.target.value)}>
                  {STATUSES.map((s) => <option key={s}>{s}</option>)}
                </select>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Participations */}
        <div className="card">
          <h3 className="font-semibold text-slate-700 mb-3">Submissions</h3>
          {parts.length === 0 ? <Empty /> : (
            <table className="w-full">
              <thead><tr>
                <th className="th">Employee</th><th className="th">Challenge</th><th className="th">Status</th>
                <th className="th">XP</th><th className="th"></th>
              </tr></thead>
              <tbody>
                {parts.map((p) => (
                  <tr key={p.id}>
                    <td className="td font-semibold">{userName(p.user_id)}</td>
                    <td className="td">{chTitle(p.challenge_id)}</td>
                    <td className="td"><StatusPill status={p.approval_status} /></td>
                    <td className="td">{p.xp_awarded || '—'}</td>
                    <td className="td text-right">
                      {isManager && p.approval_status === 'Pending' && (
                        <div className="flex gap-2 justify-end">
                          <button className="btn-primary py-1 px-3 text-xs" onClick={() => decide(p.id, 'approve')}>Approve</button>
                          <button className="btn-danger py-1 px-3 text-xs" onClick={() => decide(p.id, 'reject')}>Reject</button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Leaderboard + my badges */}
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-3">🏆 Leaderboard</h3>
            {board.map((u, i) => (
              <div key={u.user_id} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
                <div className="flex items-center gap-3">
                  <span className="w-6 text-center font-bold text-slate-400">{i + 1}</span>
                  <div>
                    <div className="font-semibold text-sm text-slate-700">{u.full_name}</div>
                    <div className="text-xs text-slate-400">{u.department}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <span>⭐ {u.xp}</span><span>{u.badge_count} 🏅</span>
                </div>
              </div>
            ))}
          </div>
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-3">My Badges</h3>
            {badges.length === 0 ? <Empty>No badges yet — complete a challenge!</Empty> : (
              <div className="flex flex-wrap gap-3">
                {badges.map((b) => (
                  <div key={b.badge.id} className="flex flex-col items-center w-20 text-center">
                    <div className="text-3xl">{b.badge.icon || '🏅'}</div>
                    <div className="text-xs font-semibold text-slate-600">{b.badge.name}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
