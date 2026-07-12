import { useEffect, useState } from 'react'
import { api } from '../api'
import { Empty, Field, Modal, Spinner } from './ui'

// Generic CRUD table + create/edit modal driven by a field config.
// Works against any REST resource exposing GET/POST /<endpoint> and
// (optionally) PUT/DELETE /<endpoint>/{id}.
export default function EntityManager({
  title, endpoint, columns, fields,
  canCreate = true, canEdit = true, canDelete = true,
  refs = {}, onSaved,
}) {
  const [rows, setRows] = useState(null)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({})
  const [busy, setBusy] = useState(false)

  const load = () => api.get(endpoint).then(setRows).catch((e) => { setRows([]); console.error(e) })
  useEffect(() => { load() }, [endpoint])

  const openCreate = () => {
    const blank = {}
    fields.forEach((f) => { blank[f.key] = f.type === 'checkbox' ? (f.default ?? false) : '' })
    setForm(blank); setEditing(null); setOpen(true)
  }
  const openEdit = (row) => {
    const f = {}
    fields.forEach((fl) => { f[fl.key] = row[fl.key] ?? (fl.type === 'checkbox' ? false : '') })
    setForm(f); setEditing(row); setOpen(true)
  }

  const buildPayload = () => {
    const p = {}
    for (const f of fields) {
      let v = form[f.key]
      if (f.type === 'number') v = v === '' || v == null ? 0 : Number(v)
      else if (f.type === 'checkbox') v = !!v
      else if (f.type === 'ref') v = v ? Number(v) : null
      else if (f.type === 'date') v = v || null
      else if (v === '') v = f.required ? '' : null
      p[f.key] = v
    }
    return p
  }

  const save = async (e) => {
    e.preventDefault(); setBusy(true)
    try {
      const payload = buildPayload()
      if (editing) await api.put(`${endpoint}/${editing.id}`, payload)
      else await api.post(endpoint, payload)
      setOpen(false); load()
      onSaved && onSaved()
    } catch (err) { alert(err.message) } finally { setBusy(false) }
  }

  const remove = async (row) => {
    if (!confirm(`Delete "${row[columns[0].key]}"?`)) return
    try { await api.del(`${endpoint}/${row.id}`); load(); onSaved && onSaved() }
    catch (err) { alert(err.message) }
  }

  const refOptions = (f) => refs[f.refKey] || []
  const refLabel = (item) => item.name || item.title || item.activity_type || item.full_name || item.product || `#${item.id}`

  const showActions = canEdit || canDelete

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-700">{title}</h3>
        {canCreate && <button className="btn-primary py-1.5 px-3 text-sm" onClick={openCreate}>+ Add</button>}
      </div>

      {!rows ? <Spinner /> : rows.length === 0 ? <Empty /> : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead><tr>
              {columns.map((c) => <th key={c.key} className="th">{c.label}</th>)}
              {showActions && <th className="th"></th>}
            </tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  {columns.map((c) => (
                    <td key={c.key} className="td">{c.render ? c.render(row) : String(row[c.key] ?? '—')}</td>
                  ))}
                  {showActions && (
                    <td className="td text-right whitespace-nowrap">
                      {canEdit && <button className="text-brand-600 text-xs font-semibold mr-3" onClick={() => openEdit(row)}>Edit</button>}
                      {canDelete && <button className="text-rose-500 text-xs font-semibold" onClick={() => remove(row)}>Delete</button>}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title={`${editing ? 'Edit' : 'New'} ${title.replace(/s$/, '')}`}>
        <form onSubmit={save} className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
          {fields.map((f) => (
            <Field key={f.key} label={f.label + (f.required ? ' *' : '')}>
              {f.type === 'textarea' ? (
                <textarea className="input h-28" required={f.required}
                  value={form[f.key] ?? ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
              ) : f.type === 'select' ? (
                <select className="input" required={f.required}
                  value={form[f.key] ?? ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}>
                  <option value="">— select —</option>
                  {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : f.type === 'ref' ? (
                <select className="input"
                  value={form[f.key] ?? ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}>
                  <option value="">— none —</option>
                  {refOptions(f).map((o) => <option key={o.id} value={String(o.id)}>{refLabel(o)}</option>)}
                </select>
              ) : f.type === 'checkbox' ? (
                <input type="checkbox" className="h-5 w-5 accent-brand-600"
                  checked={!!form[f.key]} onChange={(e) => setForm({ ...form, [f.key]: e.target.checked })} />
              ) : (
                <input className="input" type={f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text'}
                  step="any" required={f.required}
                  value={form[f.key] ?? ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
              )}
            </Field>
          ))}
          <div className="flex gap-2 pt-2">
            <button className="btn-primary flex-1" disabled={busy}>{busy ? 'Saving…' : editing ? 'Save changes' : 'Create'}</button>
            <button type="button" className="btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
