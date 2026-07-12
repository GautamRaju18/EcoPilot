import { useRef, useState } from 'react'
import { api } from '../api'

// Shown to a brand-new company (no data yet). Three ways to get started:
// load sample data, import an ESG CSV, or dismiss and set up manually.
export default function Onboarding({ companyName, onDone, onDismiss }) {
  const [busy, setBusy] = useState('')
  const [result, setResult] = useState(null)
  const fileRef = useRef(null)

  const loadSample = async () => {
    setBusy('sample')
    try {
      const r = await api.post('/onboarding/sample-data')
      setResult(`✅ Loaded ${r.departments} departments & sample activity — overall ESG ${r.overall}.`)
      setTimeout(onDone, 900)
    } catch (e) { alert(e.message); setBusy('') }
  }

  const onFile = async (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setBusy('import')
    try {
      const fd = new FormData()
      fd.append('file', f)
      const r = await api.postForm('/onboarding/import', fd)
      setResult(`✅ Imported ${r.imported} records${r.skipped ? ` (${r.skipped} skipped)` : ''} — overall ESG ${r.overall}.`)
      setTimeout(onDone, 900)
    } catch (e) { alert(e.message); setBusy('') }
  }

  const downloadTemplate = () => window.open('/api/onboarding/template', '_blank')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-7">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🌱</div>
          <h2 className="text-2xl font-bold text-slate-800">Welcome to EcoPilot{companyName ? `, ${companyName}` : ''}!</h2>
          <p className="text-sm text-slate-500 mt-1">
            Your workspace is empty. Let's get some ESG data in so your dashboard, scores and leaderboard come to life.
          </p>
        </div>

        {result ? (
          <div className="text-center py-6 text-brand-700 font-semibold">{result}</div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {/* Sample data */}
            <button onClick={loadSample} disabled={!!busy}
              className="text-left rounded-xl border-2 border-brand-200 hover:border-brand-500 p-5 transition disabled:opacity-60">
              <div className="text-3xl mb-2">✨</div>
              <div className="font-bold text-slate-800">Load sample data</div>
              <div className="text-sm text-slate-500 mt-1">
                Instantly populate your company with realistic departments, employees, emissions, challenges and policies.
              </div>
              <div className="mt-3 text-brand-600 font-semibold text-sm">
                {busy === 'sample' ? 'Generating…' : 'Recommended →'}
              </div>
            </button>

            {/* Import CSV */}
            <div className="rounded-xl border-2 border-slate-200 p-5">
              <div className="text-3xl mb-2">📤</div>
              <div className="font-bold text-slate-800">Import your ESG data</div>
              <div className="text-sm text-slate-500 mt-1">
                Upload a CSV of your emissions data. We'll create departments and carbon records automatically.
              </div>
              <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={onFile} />
              <div className="mt-3 flex items-center gap-3">
                <button onClick={() => fileRef.current?.click()} disabled={!!busy}
                  className="btn-primary py-1.5 px-3 text-sm">
                  {busy === 'import' ? 'Importing…' : 'Upload CSV'}
                </button>
                <button onClick={downloadTemplate} className="text-brand-600 text-xs font-semibold underline">
                  template
                </button>
              </div>
            </div>
          </div>
        )}

        {!result && (
          <div className="text-center mt-6">
            <button onClick={onDismiss} className="text-sm text-slate-400 hover:text-slate-600">
              I'll set it up manually
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
