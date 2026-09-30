import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import { setAccessToken } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setReady(true))
  }, [])

  async function login(email, password) {
    const result = await api.login(email, password)
    setAccessToken(result.access)
    setUser(result.user)
    return result.user
  }

  async function register(payload) {
    await api.register(payload)
    return login(payload.email, payload.password)
  }

  async function logout() {
    try { await api.logout() } finally {
      setAccessToken(null)
      setUser(null)
    }
  }

  const value = useMemo(() => ({ user, ready, login, register, logout }), [user, ready])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
