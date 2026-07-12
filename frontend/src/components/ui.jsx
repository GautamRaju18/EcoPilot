// Small reusable presentational components shared across pages.

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center gap-2 text-slate-400 text-sm py-8 justify-center">
      <span className="h-4 w-4 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
      {label}
    </div>
  )
}

const PILL_COLORS = {
  green: 'bg-brand-100 text-brand-700',
  amber: 'bg-amber-100 text-amber-700',
  red: 'bg-rose-100 text-rose-700',
  slate: 'bg-slate-100 text-slate-600',
  blue: 'bg-sky-100 text-sky-700',
  violet: 'bg-violet-100 text-violet-700',
}
export function Pill({ color = 'slate', children }) {
  return <span className={`pill ${PILL_COLORS[color] || PILL_COLORS.slate}`}>{children}</span>
}

const STATUS_COLOR = {
  Approved: 'green', Active: 'green', Resolved: 'green', Completed: 'green',
  Pending: 'amber', 'Under Review': 'amber', 'In Progress': 'amber', Draft: 'slate',
  Rejected: 'red', Open: 'red', Archived: 'slate',
}
export const StatusPill = ({ status }) => <Pill color={STATUS_COLOR[status] || 'slate'}>{status}</Pill>

export function StatCard({ label, value, sub, icon }) {
  return (
    <div className="card flex items-center gap-4">
      {icon && <div className="text-3xl">{icon}</div>}
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</div>
        <div className="text-2xl font-bold text-slate-800">{value}</div>
        {sub && <div className="text-xs text-slate-400">{sub}</div>}
      </div>
    </div>
  )
}

// Circular gauge for a 0-100 score.
export function ScoreRing({ value = 0, size = 150, label = 'Overall ESG' }) {
  const r = size / 2 - 12
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, value)) / 100
  const color = value >= 75 ? '#059669' : value >= 50 ? '#f59e0b' : '#f43f5e'
  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#e2e8f0" strokeWidth="12" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="12" fill="none"
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
          style={{ transition: 'stroke-dashoffset .8s ease',
                   filter: `drop-shadow(0 3px 10px ${color}66)` }} />
      </svg>
      <div className="-mt-[95px] text-center pointer-events-none">
        <div className="text-4xl font-extrabold text-slate-800">{value}</div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</div>
      </div>
      <div className="mt-16" />
    </div>
  )
}

// Horizontal labelled score bar.
export function Bar({ label, value, max = 100 }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  const color = value >= 75 ? 'bg-brand-500' : value >= 50 ? 'bg-amber-400' : 'bg-rose-400'
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="font-medium text-slate-600">{label}</span>
        <span className="font-semibold text-slate-800">{value}</span>
      </div>
      <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%`, transition: 'width .6s' }} />
      </div>
    </div>
  )
}

export function Modal({ open, onClose, title, children }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="card w-full max-w-lg shadow-2xl animate-float-in" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-800">{title}</h3>
          <button className="text-slate-400 hover:text-slate-600" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Field({ label, children }) {
  return <div><label className="label">{label}</label>{children}</div>
}

export function Empty({ children = 'Nothing here yet.' }) {
  return <div className="text-center text-sm text-slate-400 py-10">{children}</div>
}
