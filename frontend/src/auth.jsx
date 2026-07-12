import { createContext, useContext, useEffect, useState } from 'react'
import { api, clearToken, getToken, setToken } from './api'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) { setLoading(false); return }
    api.get('/auth/me').then(setUser).catch(() => clearToken()).finally(() => setLoading(false))
  }, [])

  const login = async (email, password) => {
    const data = await api.login(email, password)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }
  const register = async (payload) => {
    const data = await api.post('/auth/register', payload)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }
  const logout = () => { clearToken(); setUser(null); location.href = '/login' }

  const isManager = user && (user.role === 'Manager' || user.role === 'Admin')

  return (
    <AuthCtx.Provider value={{ user, setUser, login, register, logout, loading, isManager }}>
      {children}
    </AuthCtx.Provider>
  )
}
