import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { AlertTriangle, ArrowDownToLine, Banknote, Boxes, ClipboardList, ShoppingCart, Users } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { api } from '../services/api'

export default function DashboardPage() {
  const { user, ready } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { if (user?.is_staff) api.dashboard().then(setData).catch(err => setError(err.message)) }, [user])
  if (!ready) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton" /></section>
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_staff) return <section className="site-container page-section"><div className="state-card"><strong>Staff access required.</strong></div></section>
  const currency = data?.currency || 'AFN'
  const money = amount => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amount || 0)
  const cards = data ? [
    ...(data.today_sales !== undefined ? [[Banknote, 'Sales today', money(data.today_sales)], [ShoppingCart, 'Transactions today', data.today_transactions]] : []),
    ...(data.pending_orders !== undefined ? [[ClipboardList, 'Orders pending', data.pending_orders]] : []),
    [Boxes, 'Products', data.products], [AlertTriangle, 'Low stock items', data.low_stock_products], [Users, 'Active suppliers', data.suppliers],
    ...(data.purchases_month !== undefined ? [[ArrowDownToLine, 'Purchases this month', money(data.purchases_month)]] : []),
    ...(data.expenses_month !== undefined ? [[Banknote, 'Expenses this month', money(data.expenses_month)]] : []),
  ] : []
  const peak = Math.max(1, ...(data?.daily_sales || []).map(item => Number(item.sales)))
  return <main className="site-container page-section admin-dashboard"><div className="page-title-row"><div><span className="eyebrow">STORE MANAGEMENT</span><h1>Dashboard</h1><p>Live totals from sales, stock, purchases and expenses.</p></div><div className="dashboard-links"><Link className="button-outline" to="/pos">Open POS</Link><Link className="button-outline" to="/pos/returns">Returns</Link><Link className="button-outline" to="/inventory">Inventory</Link><Link className="button-outline" to="/purchases">Purchases</Link><Link className="button-outline" to="/suppliers">Suppliers</Link><Link className="button-outline" to="/expenses">Expenses</Link></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}{!data && !error && <div className="product-skeleton detail-skeleton" />}
    {data && <><div className="dashboard-kpis">{cards.map(([Icon, label, value]) => <article className="dashboard-kpi" key={label}><span><Icon size={17} /></span><small>{label}</small><strong>{value}</strong></article>)}</div>{data.daily_sales && <div className="dashboard-panels"><article className="dashboard-panel"><h2>Sales · last 7 days</h2><div className="sales-bars">{data.daily_sales.map(item => <div className="sales-bar-col" key={item.date}><div className="sales-bar" title={money(item.sales)} style={{ height: `${Math.max(3, Number(item.sales) / peak * 100)}%` }} /><small>{new Date(item.date + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short' })}</small></div>)}</div></article><article className="dashboard-panel"><h2>Top POS products</h2>{data.top_products.length === 0 ? <p className="muted-empty">No POS sales recorded yet.</p> : data.top_products.map(row => <div className="dashboard-row" key={row.title}><span>{row.title}</span><b>{row.quantity} sold</b></div>)}</article><article className="dashboard-panel"><h2>Payment methods</h2>{data.payment_methods.length === 0 ? <p className="muted-empty">No POS payments recorded yet.</p> : data.payment_methods.map(row => <div className="dashboard-row" key={row.payment_method}><span>{row.payment_method.replace('_', ' ')}</span><b>{money(row.amount)}</b></div>)}</article></div>}</>}
  </main>
}
