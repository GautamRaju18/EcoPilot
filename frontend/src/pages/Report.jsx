import { useEffect, useState } from 'react'
import { api } from '../api'
import { Spinner } from '../components/ui'

export default function Report() {
  const [depts, setDepts] = useState([])
  const [deptId, setDeptId] = useState('')
  const [report, setReport] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.get('/departments').then(setDepts).catch(() => {}) }, [])

  const generate = async () => {
    setBusy(true); setReport(null)
    try {
      const res = await api.post('/ai/report', { department_id: deptId ? Number(deptId) : null })
      setReport(res)
    } catch (e) { alert(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">📄 ESG Summary Report</h1>
        <p className="text-sm text-slate-400">Auto-generated narrative from live scores via the LangGraph pipeline.</p>
      </div>

      <div className="card flex items-end gap-3">
        <div className="flex-1">
          <label className="label">Scope</label>
          <select className="input" value={deptId} onChange={(e) => setDeptId(e.target.value)}>
            <option value="">Organisation-wide</option>
            {depts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        <button className="btn-primary" onClick={generate} disabled={busy}>
          {busy ? 'Generating…' : 'Generate Report'}
        </button>
      </div>

      {busy && <div className="card"><Spinner label="Running LangGraph pipeline: gather → retrieve → draft → finalize…" /></div>}

      {report && (
        <div className="card">
          <div className="flex items-start justify-between mb-4 pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-xl font-bold text-slate-800">{report.title}</h2>
              <div className="text-xs text-slate-400 mt-1">
                Generated {new Date(report.generated_at).toLocaleString()} · via <b>{report.provider}</b>
              </div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-extrabold text-brand-600">{report.overall_score}</div>
              <div className="text-[10px] uppercase tracking-wide text-slate-400">Overall</div>
            </div>
          </div>
          <div className="prose prose-sm max-w-none whitespace-pre-wrap text-slate-700 leading-relaxed">
            {report.narrative}
          </div>
        </div>
      )}
    </div>
  )
}
