import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import EntityManager from '../components/EntityManager'

const reindex = () => api.post('/ai/reindex').catch(() => {})

// Per-entity config: columns (table) + fields (form).
const CONFIGS = {
  Departments: {
    endpoint: '/departments', onSaved: reindex,
    columns: [{ key: 'name', label: 'Name' }, { key: 'code', label: 'Code' },
              { key: 'head', label: 'Head' }, { key: 'employee_count', label: 'Employees' },
              { key: 'status', label: 'Status' }],
    fields: [{ key: 'name', label: 'Name', type: 'text', required: true },
             { key: 'code', label: 'Code', type: 'text', required: true },
             { key: 'head', label: 'Head', type: 'text' },
             { key: 'parent_id', label: 'Parent department', type: 'ref', refKey: 'departments' },
             { key: 'employee_count', label: 'Employee count', type: 'number' },
             { key: 'status', label: 'Status', type: 'select', options: ['Active', 'Inactive'] }],
  },
  Categories: {
    endpoint: '/categories', onSaved: reindex,
    columns: [{ key: 'name', label: 'Name' }, { key: 'type', label: 'Type' }, { key: 'status', label: 'Status' }],
    fields: [{ key: 'name', label: 'Name', type: 'text', required: true },
             { key: 'type', label: 'Type', type: 'select', options: ['CSR Activity', 'Challenge'], required: true },
             { key: 'status', label: 'Status', type: 'select', options: ['Active', 'Inactive'] }],
  },
  'Emission Factors': {
    endpoint: '/emission-factors', onSaved: reindex,
    columns: [{ key: 'activity_type', label: 'Activity' }, { key: 'unit', label: 'Unit' },
              { key: 'co2e_per_unit', label: 'kg CO₂e/unit' }, { key: 'description', label: 'Description' }],
    fields: [{ key: 'activity_type', label: 'Activity type', type: 'text', required: true },
             { key: 'unit', label: 'Unit', type: 'text' },
             { key: 'co2e_per_unit', label: 'kg CO₂e per unit', type: 'number', required: true },
             { key: 'description', label: 'Description', type: 'text' }],
  },
  Products: {
    endpoint: '/products',
    columns: [{ key: 'product', label: 'Product' }, { key: 'esg_rating', label: 'Rating' },
              { key: 'carbon_footprint', label: 'Footprint' }, { key: 'recyclable_pct', label: 'Recyclable %' }],
    fields: [{ key: 'product', label: 'Product', type: 'text', required: true },
             { key: 'carbon_footprint', label: 'Carbon footprint (kg)', type: 'number' },
             { key: 'recyclable_pct', label: 'Recyclable %', type: 'number' },
             { key: 'ethical_sourcing', label: 'Ethical sourcing', type: 'text' },
             { key: 'esg_rating', label: 'ESG rating (A-D)', type: 'text' }],
  },
  Goals: {
    endpoint: '/goals', onSaved: reindex,
    columns: [{ key: 'target_metric', label: 'Metric' }, { key: 'target_value', label: 'Target' },
              { key: 'unit', label: 'Unit' }, { key: 'current_value', label: 'Current' }, { key: 'deadline', label: 'Deadline' }],
    fields: [{ key: 'target_metric', label: 'Target metric', type: 'text', required: true },
             { key: 'target_value', label: 'Target value', type: 'number', required: true },
             { key: 'unit', label: 'Unit', type: 'text' },
             { key: 'current_value', label: 'Current value', type: 'number' },
             { key: 'deadline', label: 'Deadline', type: 'date' },
             { key: 'department_id', label: 'Department', type: 'ref', refKey: 'departments' }],
  },
  Policies: {
    endpoint: '/policies', onSaved: reindex,
    columns: [{ key: 'title', label: 'Title' }, { key: 'category', label: 'Category' }, { key: 'version', label: 'Version' }],
    fields: [{ key: 'title', label: 'Title', type: 'text', required: true },
             { key: 'category', label: 'Category', type: 'select', options: ['Environmental', 'Social', 'Governance'], required: true },
             { key: 'version', label: 'Version', type: 'text' },
             { key: 'document', label: 'Document text (fed to AI copilot)', type: 'textarea', required: true }],
  },
  Badges: {
    endpoint: '/badges',
    columns: [{ key: 'icon', label: '' }, { key: 'name', label: 'Name' },
              { key: 'rule_metric', label: 'Metric' }, { key: 'rule_threshold', label: 'Threshold' }],
    fields: [{ key: 'name', label: 'Name', type: 'text', required: true },
             { key: 'description', label: 'Description', type: 'text' },
             { key: 'icon', label: 'Icon (emoji)', type: 'text' },
             { key: 'rule_metric', label: 'Unlock metric', type: 'select', options: ['xp', 'completed_challenges', 'points_balance'], required: true },
             { key: 'rule_threshold', label: 'Threshold', type: 'number', required: true }],
  },
  Rewards: {
    endpoint: '/rewards',
    columns: [{ key: 'name', label: 'Name' }, { key: 'points_required', label: 'Points' },
              { key: 'stock', label: 'Stock' }, { key: 'status', label: 'Status' }],
    fields: [{ key: 'name', label: 'Name', type: 'text', required: true },
             { key: 'description', label: 'Description', type: 'text' },
             { key: 'points_required', label: 'Points required', type: 'number', required: true },
             { key: 'stock', label: 'Stock', type: 'number' },
             { key: 'status', label: 'Status', type: 'select', options: ['Active', 'Inactive'] }],
  },
  Challenges: {
    endpoint: '/challenges', onSaved: reindex, canEdit: false, canDelete: false,
    columns: [{ key: 'title', label: 'Title' }, { key: 'xp', label: 'XP' },
              { key: 'difficulty', label: 'Difficulty' }, { key: 'status', label: 'Status' }],
    fields: [{ key: 'title', label: 'Title', type: 'text', required: true },
             { key: 'description', label: 'Description', type: 'textarea' },
             { key: 'xp', label: 'XP', type: 'number' },
             { key: 'difficulty', label: 'Difficulty', type: 'select', options: ['Easy', 'Medium', 'Hard'] },
             { key: 'evidence_required', label: 'Evidence required', type: 'checkbox', default: true },
             { key: 'deadline', label: 'Deadline', type: 'date' },
             { key: 'category_id', label: 'Category', type: 'ref', refKey: 'categories' },
             { key: 'status', label: 'Status', type: 'select', options: ['Draft', 'Active', 'Under Review', 'Completed', 'Archived'] }],
  },
  'CSR Activities': {
    endpoint: '/csr/activities', canEdit: false, canDelete: false,
    columns: [{ key: 'title', label: 'Title' }, { key: 'points', label: 'Points' }, { key: 'date', label: 'Date' }],
    fields: [{ key: 'title', label: 'Title', type: 'text', required: true },
             { key: 'description', label: 'Description', type: 'textarea' },
             { key: 'points', label: 'Points', type: 'number' },
             { key: 'date', label: 'Date', type: 'date' },
             { key: 'category_id', label: 'Category', type: 'ref', refKey: 'categories' },
             { key: 'department_id', label: 'Department', type: 'ref', refKey: 'departments' }],
  },
}

const TABS = Object.keys(CONFIGS)

export default function Admin() {
  const { isManager } = useAuth()
  const [tab, setTab] = useState(TABS[0])
  const [refs, setRefs] = useState({ departments: [], categories: [] })

  useEffect(() => {
    api.get('/departments').then((d) => setRefs((r) => ({ ...r, departments: d }))).catch(() => {})
    api.get('/categories').then((c) => setRefs((r) => ({ ...r, categories: c }))).catch(() => {})
  }, [])

  if (!isManager) {
    return <div className="card text-center text-slate-500 py-12">
      🔒 Admin data management is available to Managers and Admins only.
    </div>
  }

  const cfg = CONFIGS[tab]
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Data Management</h1>
        <p className="text-sm text-slate-400">Create and edit master data live — changes flow straight into scores, gamification and the AI copilot.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded-xl text-sm font-semibold transition ${
              tab === t ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}>
            {t}
          </button>
        ))}
      </div>

      <EntityManager key={tab} title={tab} refs={refs} {...cfg} />
    </div>
  )
}
