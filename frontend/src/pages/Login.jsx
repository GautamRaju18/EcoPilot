import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const DEMO = [
  { label: 'GreenCore Mgr', email: 'manager@ecopilot.com', pw: 'manager123' },
  { label: 'GreenCore (Priya)', email: 'priya@ecopilot.com', pw: 'priya123' },
  { label: 'TerraLogistics', email: 'admin@terralogistics.com', pw: 'admin123' },
]

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('manager@ecopilot.com')
  const [pw, setPw] = useState('manager123')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e, em = email, p = pw) => {
    e?.preventDefault()
    setErr(''); setBusy(true)
    try {
      await login(em, p)
      nav('/')
    } catch (e) {
      setErr(e.message || 'Login failed')
    } finally { setBusy(false) }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Brand panel */}
      <div className="hidden lg:flex flex-col justify-center bg-gradient-to-br from-brand-700 via-brand-800 to-brand-900 text-white p-14">
        <div className="text-5xl mb-4">🌱</div>
        <h1 className="text-4xl font-extrabold mb-3">EcoPilot</h1>
        <p className="text-brand-100 text-lg max-w-md">
          AI-powered ESG management — carbon accounting, CSR & governance
          workflows, and gamified sustainability in one dashboard.
        </p>
        <ul className="mt-8 space-y-2 text-brand-200 text-sm">
          <li>📊 Weighted ESG scoring across departments</li>
          <li>🤖 AI copilot grounded in your own policies</li>
          <li>🏆 Challenges, badges & leaderboards</li>
        </ul>
      </div>

      {/* Form */}
      <div className="flex items-center justify-center p-8">
        <div className="card w-full max-w-sm shadow-2xl">
          <h2 className="text-2xl font-bold mb-1">Sign in</h2>
          <p className="text-sm text-slate-400 mb-6">Access your ESG dashboard</p>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label">Password</label>
              <input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
            </div>
            {err && <div className="text-sm text-rose-600">{err}</div>}
            <button className="btn-primary w-full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
          </form>

          <p className="text-sm text-slate-500 mt-4 text-center">
            New here? <Link to="/register" className="text-brand-600 font-semibold">Create an account</Link>
          </p>

          <div className="mt-6">
            <div className="text-xs font-semibold text-slate-400 mb-2">Quick demo login</div>
            <div className="grid grid-cols-3 gap-2">
              {DEMO.map((d) => (
                <button key={d.email} className="btn-ghost text-xs py-1.5"
                  onClick={(e) => { setEmail(d.email); setPw(d.pw); submit(e, d.email, d.pw) }}>
                  {d.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
