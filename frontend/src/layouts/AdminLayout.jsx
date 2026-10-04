import { Navigate, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { BarChart3, Boxes, CreditCard, FileText, LayoutDashboard, LogOut, Package, ShoppingCart, Store, Truck, Users, UserCog, Wallet } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const links = [
  ['dashboard', 'Dashboard', LayoutDashboard, 'dashboard'],
  ['pos', 'POS', ShoppingCart, 'pos'],
  ['inventory', 'Inventory', Boxes, 'inventory'],
  ['purchases', 'Purchases', Package, 'purchases'],
  ['suppliers', 'Suppliers', Truck, 'suppliers'],
  ['expenses', 'Expenses', Wallet, 'expenses'],
  ['sales', 'Sales', FileText, 'sales'],
  ['reports', 'Reports', BarChart3, 'reports'],
  ['customers', 'Customers', Users, 'customers'],
  ['payments', 'Payments', CreditCard, 'payments'],
  ['users', 'Users', UserCog, 'users'],
]

export default function AdminLayout() {
  const { user, ready, logout } = useAuth()
  const navigate = useNavigate()
  if (!ready) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton" /></section>
  if (!user?.is_staff || !user?.menuPermissions?.admin_panel) return <Navigate to="/admin/login" replace />

  async function signOut() {
    await logout()
    navigate('/admin/login', { replace: true })
  }

  return <div className="admin-shell">
    <aside className="admin-sidebar">
      <div className="admin-brand"><span className="brand-mark"><Store size={21} /></span><div><strong>Momand</strong><small>CONTROL PANEL</small></div></div>
      <nav className="admin-nav">
        {links.filter(([, , , permission]) => user?.menuPermissions?.[permission]).map(([path, label, Icon]) => <NavLink key={path} to={path} className={({ isActive }) => 'admin-nav-link' + (isActive ? ' active' : '')}><Icon size={18} /><span>{label}</span></NavLink>)}
      </nav>
      <button className="admin-logout" onClick={signOut}><LogOut size={17} /> Sign out</button>
    </aside>
    <main className="admin-content">
      <div className="admin-topbar"><div><strong>{user.first_name || user.email}</strong><small>Staff account</small></div><NavLink className="button-outline" to="/">View Store</NavLink></div>
      <Outlet />
    </main>
  </div>
}
