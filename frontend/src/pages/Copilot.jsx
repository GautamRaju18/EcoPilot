import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

const SUGGESTED = [
  'What is our current emission target for manufacturing?',
  'What are our diversity commitments?',
  'How often are ESG audits conducted?',
  'How is the overall ESG score calculated?',
]

export default function Copilot() {
  const [msgs, setMsgs] = useState([
    { role: 'bot', text: 'Hi! I\'m EcoPilot. Ask me anything about your organisation\'s ESG policies and goals — my answers are grounded in your ingested documents.' },
  ])
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState(null)
  const endRef = useRef(null)

  useEffect(() => { api.get('/ai/status').then(setStatus).catch(() => {}) }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  const ask = async (question) => {
    const text = question || q
    if (!text.trim() || busy) return
    setMsgs((m) => [...m, { role: 'user', text }])
    setQ(''); setBusy(true)
    try {
      const res = await api.post('/ai/ask', { question: text })
      setMsgs((m) => [...m, { role: 'bot', text: res.answer, sources: res.sources, provider: res.provider }])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'bot', text: 'Error: ' + e.message }])
    } finally { setBusy(false) }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">🤖 Ask EcoPilot</h1>
          <p className="text-sm text-slate-400">RAG-grounded answers from your ESG policies & goals.</p>
        </div>
        {status && (
          <div className="text-xs text-slate-400 text-right">
            <div>provider: <b className="text-slate-600">{status.provider}</b></div>
            <div>{status.indexed_chunks} chunks · {status.retrieval_backend}</div>
          </div>
        )}
      </div>

      <div className="card h-[55vh] overflow-y-auto space-y-4">
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
              m.role === 'user' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-800'}`}>
              {m.text}
              {m.sources?.length > 0 && (
                <div className="mt-3 pt-2 border-t border-slate-200/60 space-y-1">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Sources</div>
                  {m.sources.map((s, j) => (
                    <div key={j} className="text-xs text-slate-500">
                      📄 <b>{s.title}</b> <span className="text-slate-400">({(s.score * 100).toFixed(0)}%)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="text-sm text-slate-400">EcoPilot is thinking…</div>}
        <div ref={endRef} />
      </div>

      <div className="flex flex-wrap gap-2">
        {SUGGESTED.map((s) => (
          <button key={s} className="pill bg-slate-100 text-slate-600 hover:bg-slate-200" onClick={() => ask(s)}>{s}</button>
        ))}
      </div>

      <div className="flex gap-2">
        <input className="input" placeholder="Ask about emission targets, CSR, governance…"
          value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && ask()} />
        <button className="btn-primary" onClick={() => ask()} disabled={busy}>Ask</button>
      </div>
    </div>
  )
}
