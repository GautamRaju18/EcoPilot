import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Empty, Spinner, StatusPill } from '../components/ui'

export default function CSR() {
  const { user, isManager } = useAuth()
  const [activities, setActivities] = useState(null)
  const [parts, setParts] = useState([])
  const [users, setUsers] = useState([])

  const load = () => {
    api.get('/csr/activities').then(setActivities)
    api.get('/csr/participations').then(setParts)
    api.get('/users').then(setUsers).catch(() => {})
  }
  useEffect(load, [])

  const userName = (id) => users.find((u) => u.id === id)?.full_name || `#${id}`
  const actTitle = (id) => activities?.find((a) => a.id === id)?.title || `#${id}`

  const participate = async (activityId) => {
    // Optional proof upload via a file picker
    const input = document.createElement('input')
    input.type = 'file'
    input.onchange = async () => {
      const fd = new FormData()
      if (input.files[0]) fd.append('proof', input.files[0])
      try { await api.postForm(`/csr/activities/${activityId}/participate`, fd); load() }
      catch (e) { alert(e.message) }
    }
    input.click()
  }

  const decide = async (id, action) => {
    try { await api.post(`/csr/participations/${id}/${action}`); load() }
    catch (e) { alert(e.message) }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">CSR Activities</h1>
        <p className="text-sm text-slate-400">Join activities, upload proof, and earn points on approval (evidence required).</p>
      </div>

      {/* Activities */}
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
        {!activities ? <Spinner /> : activities.map((a) => (
          <div key={a.id} className="card">
            <div className="flex items-start justify-between">
              <h3 className="font-semibold text-slate-800">{a.title}</h3>
              <span className="pill bg-brand-100 text-brand-700">+{a.points} pts</span>
            </div>
            <p className="text-sm text-slate-500 mt-1 mb-3">{a.description}</p>
            <div className="text-xs text-slate-400 mb-3">📅 {a.date}</div>
            <button className="btn-primary w-full" onClick={() => participate(a.id)}>Participate + upload proof</button>
          </div>
        ))}
      </div>

      {/* Participations */}
      <div className="card">
        <h3 className="font-semibold text-slate-700 mb-3">
          Participations {isManager && <span className="text-xs font-normal text-slate-400">(approve/reject as manager)</span>}
        </h3>
        {parts.length === 0 ? <Empty>No participations yet.</Empty> : (
          <table className="w-full">
            <thead><tr>
              <th className="th">Employee</th><th className="th">Activity</th><th className="th">Proof</th>
              <th className="th">Status</th><th className="th">Points</th><th className="th"></th>
            </tr></thead>
            <tbody>
              {parts.map((p) => (
                <tr key={p.id}>
                  <td className="td font-semibold">{userName(p.user_id)}</td>
                  <td className="td">{actTitle(p.activity_id)}</td>
                  <td className="td">{p.proof_file ? <a className="text-brand-600 underline" href={`/uploads/${p.proof_file}`} target="_blank">view</a> : <span className="text-rose-500">none</span>}</td>
                  <td className="td"><StatusPill status={p.approval_status} /></td>
                  <td className="td">{p.points_earned || '—'}</td>
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
    </div>
  )
}
