import { Navigate, Link } from 'react-router-dom'
import { ClipboardList, LogOut, UserRound } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function AccountPage() {
  const { user, ready, logout } = useAuth()
  if (!ready) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton" /></section>
  if (!user) return <Navigate to="/login" replace />
  return <section className="site-container page-section"><div className="page-title-row"><div><span className="eyebrow">YOUR MOMAND ACCOUNT</span><h1>Hello, {user.first_name || user.email}</h1><p>Manage your account and view your shopping activity.</p></div></div><div className="account-grid"><article className="account-card"><UserRound /><h2>Profile</h2><p>{user.first_name} {user.last_name}<br />{user.email}</p><span>Profile editing will be available with account settings.</span></article><article className="account-card"><ClipboardList /><h2>Orders</h2><p>Review the orders placed using your account.</p><Link className="button-outline" to="/orders">View order history</Link></article><article className="account-card"><LogOut /><h2>Sign out</h2><p>Sign out of your Momand account on this device.</p><button className="button-outline" onClick={logout}>Sign out</button></article></div></section>
}
