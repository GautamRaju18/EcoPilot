import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import Markdown from '../components/Markdown'

const SUGGESTED = [
  'What is our emission reduction target?',
  'What are our CSR commitments?',
  'How often are ESG audits conducted?',
  'How is the overall ESG score calculated?',
]

const GREETING = { role: 'bot', text: "Hi! I'm **EcoPilot**. Ask me anything about your organisation's ESG policies and goals — my answers are grounded in your ingested documents and cite their sources." }

export default function Copilot() {
  const { user } = useAuth()
  // Persist the conversation per-company for the whole session so it survives
  // navigating between sections and page reloads (cleared on logout / tab close).
  const chatKey = `ecopilot_chat_${user?.company_id ?? 'anon'}`
  const [msgs, setMsgs] = useState(() => {
    try {
      const saved = sessionStorage.getItem(chatKey)
      return saved ? JSON.parse(saved) : [GREETING]
    } catch { return [GREETING] }
  })
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState(null)
  const endRef = useRef(null)

  useEffect(() => { api.get('/ai/status').then(setStatus).catch(() => {}) }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])
  // Save on every change
  useEffect(() => {
    try { sessionStorage.setItem(chatKey, JSON.stringify(msgs)) } catch { /* quota */ }
  }, [msgs, chatKey])

  const clearChat = () => { setMsgs([GREETING]); sessionStorage.removeItem(chatKey) }

  const ask = async (question) => {
    const text = question || q
    if (!text.trim() || busy) return
    setMsgs((m) => [...m, { role: 'user', text }])
    setQ(''); setBusy(true)
    try {
      const res = await api.post('/ai/ask', { question: text })
      setMsgs((m) => [...m, { role: 'bot', text: res.answer, sources: res.sources, provider: res.provider }])
      setStatus((s) => (s ? { ...s, provider: res.provider } : s))  // reflect real provider used
    } catch (e) {
      setMsgs((m) => [...m, { role: 'bot', text: 'Sorry — ' + e.message }])
    } finally { setBusy(false) }
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">🤖 Ask EcoPilot</h1>
          <p className="text-sm text-slate-400">RAG-grounded answers from your ESG policies &amp; goals.</p>
        </div>
        <div className="flex items-center gap-3">
          {status && (
            <div className="text-xs text-slate-400 text-right">
              <div>provider: <b className="text-slate-600">{status.provider}</b></div>
              <div>{status.indexed_chunks} chunks · {status.retrieval_backend}</div>
            </div>
          )}
          {msgs.length > 1 && (
            <button onClick={clearChat} title="Clear conversation"
              className="btn-ghost py-1.5 px-3 text-xs">Clear</button>
          )}
        </div>
      </div>

      {/* Conversation */}
      <div className="card flex-1 overflow-y-auto space-y-4 !p-4">
        {msgs.map((m, i) => (
          <div key={i} className={`flex gap-2.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {m.role === 'bot' && (
              <div className="shrink-0 h-8 w-8 rounded-full bg-brand-100 flex items-center justify-center text-lg">🌱</div>
            )}
            <div className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-[15px] break-words ${
              m.role === 'user'
                ? 'bg-brand-600 text-white rounded-br-sm'
                : 'bg-slate-100 text-slate-800 rounded-bl-sm'}`}>
              {m.role === 'bot'
                ? <Markdown text={m.text} className="space-y-0.5" />
                : <span className="whitespace-pre-wrap">{m.text}</span>}

              {m.sources?.length > 0 && (
                <div className="mt-3 pt-2 border-t border-slate-200/70">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1">Sources</div>
                  <div className="flex flex-wrap gap-1.5">
                    {m.sources.map((s, j) => (
                      <span key={j} title={s.snippet}
                        className="inline-flex items-center gap-1 rounded-full bg-white border border-slate-200 px-2 py-0.5 text-[11px] text-slate-600">
                        📄 {s.title}
                        <span className="text-brand-600 font-semibold">{(s.score * 100).toFixed(0)}%</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex gap-2.5 justify-start">
            <div className="shrink-0 h-8 w-8 rounded-full bg-brand-100 flex items-center justify-center text-lg">🌱</div>
            <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1">
              <span className="h-2 w-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="h-2 w-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="h-2 w-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2 mt-3">
        {SUGGESTED.map((s) => (
          <button key={s} disabled={busy}
            className="pill bg-slate-100 text-slate-600 hover:bg-slate-200 disabled:opacity-50"
            onClick={() => ask(s)}>{s}</button>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2 mt-3">
        <input className="input" placeholder="Ask about emission targets, CSR, governance…"
          value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && ask()} />
        <button className="btn-primary px-6" onClick={() => ask()} disabled={busy || !q.trim()}>Ask</button>
      </div>
    </div>
  )
}
