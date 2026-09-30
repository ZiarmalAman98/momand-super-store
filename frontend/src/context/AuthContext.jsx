import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import { setAccessToken } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  async function loadUser() {
    try {
      const me = await api.me()
      const access = await api.access()
      setUser({ ...me, permissions: access.menus, permission_codes: access.permissions })
    } catch {
      setUser(null)
    } finally {
      setReady(true)
    }
  }

  useEffect(() => { loadUser() }, [])

  async function login(email, password) {
    const result = await api.login(email, password)
    setAccessToken(result.access)
    const access = await api.access()
    const nextUser = { ...result.user, permissions: access.menus, permission_codes: access.permissions }
    setUser(nextUser)
    return nextUser
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
