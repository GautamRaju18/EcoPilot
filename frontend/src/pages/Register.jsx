import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

export default function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [mode, setMode] = useState('join')      // "join" | "create"
  const [companies, setCompanies] = useState([])
  const [form, setForm] = useState({
    full_name: '', email: '', password: '',
    company_id: '', company_name: '', industry: '',
  })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.get('/companies/public').then(setCompanies).catch(() => {}) }, [])

  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true)
    try {
      const payload = {
        full_name: form.full_name, email: form.email, password: form.password, mode,
      }
      if (mode === 'create') {
        payload.company_name = form.company_name
        payload.industry = form.industry
      } else {
        if (!form.company_id) throw new Error('Please choose a company to join')
        payload.company_id = Number(form.company_id)
      }
      await register(payload)
      nav('/')
    } catch (e) { setErr(e.message || 'Registration failed') } finally { setBusy(false) }
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-center bg-gradient-to-br from-brand-700 via-brand-800 to-brand-900 text-white p-14">
        <div className="text-5xl mb-4">🌱</div>
        <h1 className="text-4xl font-extrabold mb-3">Join EcoPilot</h1>
        <p className="text-brand-100 text-lg max-w-md">
          Create your company's ESG workspace, or join an existing one and start
          contributing to sustainability goals today.
        </p>
      </div>

      <div className="flex items-center justify-center p-8">
        <div className="card w-full max-w-md shadow-2xl">
          <h2 className="text-2xl font-bold mb-1">Create your account</h2>
          <p className="text-sm text-slate-400 mb-5">Get started in seconds</p>

          {/* Mode toggle */}
          <div className="grid grid-cols-2 gap-2 mb-5">
            <button type="button" onClick={() => setMode('join')}
              className={`py-2 rounded-xl text-sm font-semibold border ${mode === 'join'
                ? 'bg-brand-600 text-white border-brand-600' : 'bg-white text-slate-600 border-slate-200'}`}>
              Join a company
            </button>
            <button type="button" onClick={() => setMode('create')}
              className={`py-2 rounded-xl text-sm font-semibold border ${mode === 'create'
                ? 'bg-brand-600 text-white border-brand-600' : 'bg-white text-slate-600 border-slate-200'}`}>
              Create a company
            </button>
          </div>

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="label">Full name</label>
              <input className="input" value={form.full_name} onChange={set('full_name')} required />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" value={form.email} onChange={set('email')} required />
            </div>
            <div>
              <label className="label">Password</label>
              <input className="input" type="password" value={form.password} onChange={set('password')} required />
            </div>

            {mode === 'join' ? (
              <div>
                <label className="label">Company</label>
                <select className="input" value={form.company_id} onChange={set('company_id')} required>
                  <option value="">— select a company —</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}{c.industry ? ` · ${c.industry}` : ''}</option>
                  ))}
                </select>
                <p className="text-xs text-slate-400 mt-1">You'll join as an Employee.</p>
              </div>
            ) : (
              <>
                <div>
                  <label className="label">Company name</label>
                  <input className="input" value={form.company_name} onChange={set('company_name')} required />
                </div>
                <div>
                  <label className="label">Industry</label>
                  <input className="input" placeholder="e.g. Manufacturing" value={form.industry} onChange={set('industry')} />
                </div>
                <p className="text-xs text-slate-400">You'll be the company Admin.</p>
              </>
            )}

            {err && <div className="text-sm text-rose-600">{err}</div>}
            <button className="btn-primary w-full" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
          </form>

          <p className="text-sm text-slate-500 mt-5 text-center">
            Already have an account? <Link to="/login" className="text-brand-600 font-semibold">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
