import { Navigate, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { apiRequest } from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function OrdersPage() {
  const { user, ready } = useAuth()
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    if (!user) return
    apiRequest('/orders/').then(result => setOrders(result.results || result)).catch(err => setError(err.message)).finally(() => setLoading(false))
  }, [user])
  if (!ready) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton" /></section>
  if (!user) return <Navigate to="/login" replace />
  const money = (amount, currency) => new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'AFN' }).format(amount || 0)
  return <section className="site-container page-section"><div className="page-title-row"><div><span className="eyebrow">YOUR SHOPPING</span><h1>Order history</h1><p>Orders placed using your account.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    {loading ? <div className="product-skeleton detail-skeleton" /> : orders.length === 0 ? <div className="state-card"><strong>No orders yet.</strong><p>Once you place an online order, it will show up here.</p><Link className="text-link" to="/shop">Browse products</Link></div> : <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Order</th><th>Date</th><th>Items</th><th>Status</th><th>Total</th><th>Receipt</th></tr></thead><tbody>{orders.map(order => <tr key={order.number}><td><strong>{order.number}</strong><div className="order-items">{order.items.map(item => `${item.title} × ${item.quantity}`).join(', ')}</div></td><td>{new Date(order.date_placed).toLocaleDateString()}</td><td>{order.items.reduce((sum, item) => sum + item.quantity, 0)}</td><td><span className="order-status">{order.status || 'Pending'}</span></td><td>{money(order.total_incl_tax, order.currency)}</td><td><Link className="text-link" to={`/orders/${encodeURIComponent(order.number)}/receipt`}>Print</Link></td></tr>)}</tbody></table></div>}
    <Link className="text-link orders-back" to="/account">Back to account</Link>
  </section>
}
