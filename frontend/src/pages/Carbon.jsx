import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { Empty, Field, Spinner } from '../components/ui'

export default function Carbon() {
  const [txs, setTxs] = useState(null)
  const [factors, setFactors] = useState([])
  const [depts, setDepts] = useState([])
  const [form, setForm] = useState({ source_ref: '', source_type: 'Manufacturing',
    emission_factor_id: '', quantity: '', department_id: '' })
  const [busy, setBusy] = useState(false)

  const load = () => api.get('/carbon').then(setTxs)
  useEffect(() => {
    load()
    api.get('/emission-factors').then(setFactors)
    api.get('/departments').then(setDepts)
  }, [])

  const factor = useMemo(
    () => factors.find((f) => f.id === Number(form.emission_factor_id)),
    [factors, form.emission_factor_id])
  const preview = factor && form.quantity ? (Number(form.quantity) * factor.co2e_per_unit).toFixed(1) : null

  const submit = async (e) => {
    e.preventDefault(); setBusy(true)
    try {
      await api.post('/carbon', {
        source_ref: form.source_ref || null,
        source_type: form.source_type,
        emission_factor_id: form.emission_factor_id ? Number(form.emission_factor_id) : null,
        quantity: Number(form.quantity) || 0,
        department_id: form.department_id ? Number(form.department_id) : null,
      })
      setForm({ ...form, source_ref: '', quantity: '' })
      load()
    } catch (e) { alert(e.message) } finally { setBusy(false) }
  }

  const deptName = (id) => depts.find((d) => d.id === id)?.name || '—'
  const factorName = (id) => factors.find((f) => f.id === id)?.activity_type || '—'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Carbon Accounting</h1>
        <p className="text-sm text-slate-400">Emissions auto-calculate from the linked factor and update the department's Environmental score.</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Form */}
        <form onSubmit={submit} className="card space-y-3">
          <h3 className="font-semibold text-slate-700">Log Transaction</h3>
          <Field label="Source reference">
            <input className="input" placeholder="e.g. PO-1042" value={form.source_ref}
              onChange={(e) => setForm({ ...form, source_ref: e.target.value })} />
          </Field>
          <Field label="Source type">
            <select className="input" value={form.source_type}
              onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
              {['Manufacturing', 'Purchase', 'Expense', 'Fleet', 'Manual'].map((t) => <option key={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Emission factor">
            <select className="input" value={form.emission_factor_id}
              onChange={(e) => setForm({ ...form, emission_factor_id: e.target.value })}>
              <option value="">— select —</option>
              {factors.map((f) => (
                <option key={f.id} value={f.id}>{f.activity_type} ({f.co2e_per_unit} kg/{f.unit})</option>
              ))}
            </select>
          </Field>
          <Field label="Quantity">
            <input className="input" type="number" placeholder="units" value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
          </Field>
          <Field label="Department">
            <select className="input" value={form.department_id}
              onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
              <option value="">— select —</option>
              {depts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </Field>
          {preview && (
            <div className="rounded-xl bg-brand-50 text-brand-700 text-sm font-semibold px-3 py-2">
              Auto-calc: {form.quantity} × {factor.co2e_per_unit} = <b>{preview} kg CO₂e</b>
            </div>
          )}
          <button className="btn-primary w-full" disabled={busy}>{busy ? 'Saving…' : 'Log & Recompute'}</button>
        </form>

        {/* List */}
        <div className="card lg:col-span-2">
          <h3 className="font-semibold text-slate-700 mb-3">Recent Transactions</h3>
          {!txs ? <Spinner /> : txs.length === 0 ? <Empty /> : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr>
                  <th className="th">Ref</th><th className="th">Type</th><th className="th">Factor</th>
                  <th className="th">Qty</th><th className="th">CO₂e (kg)</th><th className="th">Dept</th><th className="th">Date</th>
                </tr></thead>
                <tbody>
                  {txs.map((t) => (
                    <tr key={t.id}>
                      <td className="td font-semibold">{t.source_ref || '—'}</td>
                      <td className="td">{t.source_type}</td>
                      <td className="td text-slate-500">{factorName(t.emission_factor_id)}</td>
                      <td className="td">{t.quantity}</td>
                      <td className="td font-semibold text-rose-600">{t.co2e.toLocaleString()}</td>
                      <td className="td">{deptName(t.department_id)}</td>
                      <td className="td text-slate-400">{t.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
