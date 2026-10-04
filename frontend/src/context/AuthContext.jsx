import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import { setAccessToken } from '../services/api'

const AuthContext = createContext(null)

const MENU_RULES = {
  admin_panel: ['mis.view_stockmovement', 'mis.view_purchase', 'mis.view_supplier', 'mis.view_expense', 'auth.view_user'],
  dashboard: ['mis.view_possale', 'mis.view_purchase', 'mis.view_expense', 'mis.view_stockmovement'],
  pos: ['mis.add_possale', 'mis.view_possale'],
  inventory: ['mis.view_stockmovement'],
  purchases: ['mis.view_purchase'],
  suppliers: ['mis.view_supplier'],
  expenses: ['mis.view_expense'],
  sales: ['mis.view_possale'],
  reports: ['mis.view_possale', 'mis.view_purchase', 'mis.view_expense'],
  customers: ['auth.view_user'],
  payments: ['mis.view_paymenttransaction'],
  users: ['auth.view_user', 'auth.add_user', 'auth.change_user'],
}

function withMenuPermissions(user) {
  const codes = user?.permissions || []
  const permissions = Object.fromEntries(
    Object.entries(MENU_RULES).map(([menu, required]) => [menu, required.some(code => codes.includes(code))])
  )
  return { ...user, permission_codes: codes, menuPermissions: permissions }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  async function loadUser() {
    try {
      const me = await api.me()
      setUser(withMenuPermissions(me))
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
    const nextUser = withMenuPermissions(result.user)
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
