import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { AlertTriangle, ArrowDownToLine, Banknote, Boxes, ClipboardList, ShoppingCart, Users } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { api } from '../services/api'

export default function DashboardPage() {
  const { user, ready } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user?.is_staff) return
    let active = true
    const refresh = () => api.dashboard().then(value => {
      if (active) { setData(value); setError('') }
    }).catch(err => { if (active) setError(err.message) })
    refresh()
    const timer = setInterval(refresh, 15000)
    return () => { active = false; clearInterval(timer) }
  }, [user])

  if (!ready) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton" /></section>
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_staff) return <section className="site-container page-section"><div className="state-card"><strong>Staff access required.</strong></div></section>

  const currency = data?.currency || 'AFN'
  const money = amount => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amount || 0)
  const cards = data ? [
    ...(data.today_sales !== undefined ? [[Banknote, 'Sales today', money(data.today_sales)], [ShoppingCart, 'Transactions today', data.today_transactions]] : []),
    ...(data.pending_orders !== undefined ? [[ClipboardList, 'Orders pending', data.pending_orders]] : []),
    ...(data.products !== undefined ? [[Boxes, 'Products', data.products]] : []),
    ...(data.low_stock_products !== undefined ? [[AlertTriangle, 'Low stock items', data.low_stock_products]] : []),
    ...(data.suppliers !== undefined ? [[Users, 'Active suppliers', data.suppliers]] : []),
    ...(data.purchases_month !== undefined ? [[ArrowDownToLine, 'Purchases this month', money(data.purchases_month)]] : []),
    ...(data.expenses_month !== undefined ? [[Banknote, 'Expenses this month', money(data.expenses_month)]] : []),
    ...(data.outstanding_balance_total !== undefined ? [[Banknote, 'Customer balances due', money(data.outstanding_balance_total)]] : []),
  ] : []
  const peak = Math.max(1, ...(data?.daily_sales || []).map(item => Number(item.sales)))
  const saleLink = invoice => `/admin/pos/sales?invoice=${encodeURIComponent(invoice)}`

  return <main className="site-container page-section admin-dashboard">
    <div className="page-title-row"><div><h1>Dashboard</h1></div><div className="dashboard-links"><Link className="button-outline" to="/admin/pos">Open POS</Link><Link className="button-outline" to="/admin/inventory">Inventory</Link><Link className="button-outline" to="/admin/purchases">Purchases</Link><Link className="button-outline" to="/admin/suppliers">Suppliers</Link><Link className="button-outline" to="/admin/expenses">Expenses</Link></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    {!data && !error && <div className="product-skeleton detail-skeleton" />}
    {data && <>
      <div className="dashboard-kpis">{cards.map(([Icon, label, value]) => <article className="dashboard-kpi" key={label}><span><Icon size={17} /></span><small>{label}</small><strong>{value}</strong></article>)}</div>
      <div className="dashboard-panels">
        {data.daily_sales && <article className="dashboard-panel"><h2>Sales · last 7 days</h2><div className="sales-bars">{data.daily_sales.map(item => <div className="sales-bar-col" key={item.date}><div className="sales-bar" title={money(item.sales)} style={{ height: `${Math.max(3, Number(item.sales) / peak * 100)}%` }} /><small>{new Date(item.date + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short' })}</small></div>)}</div></article>}
        {data.cashier_sales && <article className="dashboard-panel"><h2>Sales by cashier today</h2>{data.cashier_sales.length === 0 ? <p className="muted-empty">No cashier sales today.</p> : data.cashier_sales.map(row => <div className="dashboard-row" key={row.cashier}><span>{row.cashier}<small>{row.transactions} receipts · {row.units || 0} units</small></span><b>{money(row.total)}</b></div>)}</article>}
        {data.top_products && <article className="dashboard-panel"><h2>Top POS products</h2>{data.top_products.length === 0 ? <p className="muted-empty">No POS sales recorded yet.</p> : data.top_products.map(row => <div className="dashboard-row" key={row.title}><span>{row.title}</span><b>{row.quantity} sold</b></div>)}</article>}
        {data.low_stock && <article className="dashboard-panel"><h2>Low stock products</h2>{data.low_stock.length === 0 ? <p className="muted-empty">No products below their stock threshold.</p> : data.low_stock.map(row => <div className="dashboard-row" key={row.sku || row.product}><span>{row.product}<small>{row.sku}</small></span><b>{row.available} left</b></div>)}</article>}
        {data.payment_methods && <article className="dashboard-panel"><h2>Payment methods</h2>{data.payment_methods.length === 0 ? <p className="muted-empty">No POS payments recorded yet.</p> : data.payment_methods.map(row => <div className="dashboard-row" key={row.payment_method}><span>{row.payment_method.replace('_', ' ')}</span><b>{money(row.amount)}</b></div>)}</article>}
        {data.outstanding_balances && <article className="dashboard-panel dashboard-panel-wide"><h2>Customer balances due <span className="dashboard-alert-count">{data.outstanding_balance_count}</span></h2>{data.outstanding_balances.length === 0 ? <p className="muted-empty">No customer balances are outstanding.</p> : data.outstanding_balances.map(item => <div className="dashboard-row" key={item.invoice_number}><span><strong>{item.customer_name || 'Customer name missing'} · {item.customer_phone || 'No phone'}</strong><small>{item.invoice_number} · {item.cashier} · {new Date(item.created_at).toLocaleString()}</small></span><b>{money(item.balance_due)}</b></div>)}</article>}
        {data.correction_requests && <article className="dashboard-panel dashboard-panel-wide"><h2>Cashier correction requests <span className="dashboard-alert-count">{data.correction_requests.length}</span></h2>{data.correction_requests.length === 0 ? <p className="muted-empty">No pending correction requests.</p> : data.correction_requests.map(item => <div className="dashboard-row correction-request-row" key={item.id}><span><strong>{item.invoice_number}</strong><small>{item.cashier_name} · {new Date(item.created_at).toLocaleString()}</small><small>{item.reason}</small></span><Link className="text-link" to={saleLink(item.invoice_number)}>Review &amp; correct</Link></div>)}</article>}
      </div>
    </>}
  </main>
}
