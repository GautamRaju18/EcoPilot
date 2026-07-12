import { useState } from 'react'
import { api } from '../api'
import { usePolling } from '../hooks'
import { useAuth } from '../auth'
import { Empty, Field, Pill, Spinner, StatusPill } from '../components/ui'

const SEV_COLOR = { Low: 'slate', Medium: 'amber', High: 'red', Critical: 'red' }

export default function Governance() {
  const { isManager } = useAuth()
  const [issues, setIssues] = useState(null)
  const [audits, setAudits] = useState([])
  const [form, setForm] = useState({ severity: 'Medium', description: '', owner: '', due_date: '', audit_id: '' })

  const load = () => {
    api.get('/governance/issues').then(setIssues)
    api.get('/governance/audits').then(setAudits)
  }
  usePolling(load, 6000)

  const create = async (e) => {
    e.preventDefault()
    if (!form.owner || !form.due_date) return alert('Owner and Due Date are required')
    try {
      await api.post('/governance/issues', {
        severity: form.severity, description: form.description, owner: form.owner,
        due_date: form.due_date, audit_id: form.audit_id ? Number(form.audit_id) : null,
      })
      setForm({ ...form, description: '', owner: '', due_date: '' })
      load()
    } catch (e) { alert(e.message) }
  }
  const setStatus = async (id, status) => {
    try { await api.post(`/governance/issues/${id}/status`, { status }); load() } catch (e) { alert(e.message) }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Governance & Compliance</h1>
        <p className="text-sm text-slate-400">Audits and compliance issues — every issue needs an owner and due date; overdue items are flagged.</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Audits */}
        <div className="card">
          <h3 className="font-semibold text-slate-700 mb-3">Audits</h3>
          {audits.length === 0 ? <Empty /> : audits.map((a) => (
            <div key={a.id} className="py-2 border-b border-slate-50 last:border-0">
              <div className="font-semibold text-sm text-slate-700">{a.scope}</div>
              <div className="text-xs text-slate-400">{a.auditor} · {a.date}</div>
              {a.findings && <div className="text-xs text-slate-500 mt-1">{a.findings}</div>}
            </div>
          ))}
        </div>

        {/* Issues */}
        <div className="card lg:col-span-2">
          <h3 className="font-semibold text-slate-700 mb-3">Compliance Issues</h3>
          {!issues ? <Spinner /> : issues.length === 0 ? <Empty /> : (
            <table className="w-full">
              <thead><tr>
                <th className="th">Severity</th><th className="th">Description</th><th className="th">Owner</th>
                <th className="th">Due</th><th className="th">Status</th>
              </tr></thead>
              <tbody>
                {issues.map((i) => (
                  <tr key={i.id}>
                    <td className="td"><Pill color={SEV_COLOR[i.severity]}>{i.severity}</Pill></td>
                    <td className="td max-w-xs">{i.description}</td>
                    <td className="td">{i.owner}</td>
                    <td className="td">
                      <span className={i.overdue ? 'text-rose-600 font-semibold' : ''}>{i.due_date}</span>
                      {i.overdue && <span className="ml-1 pill bg-rose-100 text-rose-700">OVERDUE</span>}
                    </td>
                    <td className="td">
                      {isManager ? (
                        <select className="input !py-1 text-xs" value={i.status}
                          onChange={(e) => setStatus(i.id, e.target.value)}>
                          {['Open', 'In Progress', 'Resolved'].map((s) => <option key={s}>{s}</option>)}
                        </select>
                      ) : <StatusPill status={i.status} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Create issue (managers) */}
      {isManager && (
        <form onSubmit={create} className="card grid md:grid-cols-5 gap-3 items-end">
          <Field label="Severity">
            <select className="input" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
              {['Low', 'Medium', 'High', 'Critical'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </Field>
          <div className="md:col-span-2">
            <Field label="Description">
              <input className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
            </Field>
          </div>
          <Field label="Owner *">
            <input className="input" value={form.owner} onChange={(e) => setForm({ ...form, owner: e.target.value })} required />
          </Field>
          <Field label="Due date *">
            <input className="input" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} required />
          </Field>
          <button className="btn-primary md:col-span-5">Add compliance issue</button>
        </form>
      )}
    </div>
  )
}
