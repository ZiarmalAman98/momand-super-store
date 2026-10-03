import { Navigate, Outlet, useLocation } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { useAuth } from '../context/AuthContext'

export default function StoreLayout() {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return null
  if (user?.is_staff && !location.pathname.startsWith('/pos')) return <Navigate to="/admin/pos" replace />
  if (user?.is_staff && location.pathname.startsWith('/pos/returns') && !user.permissions?.includes('mis.add_possalereturn')) return <Navigate to="/admin/pos" replace />
  return <><Header /><main className="store-main"><Outlet /></main><Footer /></>
}
