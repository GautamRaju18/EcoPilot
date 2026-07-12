import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Carbon from './pages/Carbon'
import CSR from './pages/CSR'
import Challenges from './pages/Challenges'
import Governance from './pages/Governance'
import Copilot from './pages/Copilot'
import Report from './pages/Report'
import Admin from './pages/Admin'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center"><Spinner /></div>
  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/carbon" element={<Protected><Carbon /></Protected>} />
      <Route path="/csr" element={<Protected><CSR /></Protected>} />
      <Route path="/challenges" element={<Protected><Challenges /></Protected>} />
      <Route path="/governance" element={<Protected><Governance /></Protected>} />
      <Route path="/copilot" element={<Protected><Copilot /></Protected>} />
      <Route path="/report" element={<Protected><Report /></Protected>} />
      <Route path="/admin" element={<Protected><Admin /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
