import { Navigate, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { apiRequest } from '../services/api'
import { mediaUrl } from '../services/api'
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

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">YOUR SHOPPING</span><h1>Order history</h1><p>Orders placed using your account.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    {loading ? <div className="product-skeleton detail-skeleton" /> : orders.length === 0 ? <div className="state-card"><strong>No orders yet.</strong><p>Once you place an online order, it will show up here.</p><Link className="text-link" to="/shop">Browse products</Link></div> : <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Order</th><th>Date</th><th>Items</th><th>Payment</th><th>Status</th><th>Total</th><th>Receipt</th></tr></thead><tbody>{orders.map(order => <tr key={order.number}>
      <td><strong>{order.number}</strong></td><td>{new Date(order.date_placed).toLocaleDateString()}</td>
      <td><div className="customer-order-items">{order.items.map(item => <div className="customer-order-item" key={item.id}><img src={mediaUrl(item.image) || '/media/image_not_found.jpg'} alt="" onError={event => { event.currentTarget.onerror = null; event.currentTarget.src = '/media/image_not_found.jpg' }} /><span>{item.title} × {item.quantity}</span></div>)}</div></td>
      <td>{order.payment_method ? order.payment_method.replace('_', ' ') : '—'}<small className="table-subtext">{order.payment_status || ''}</small></td><td><span className="order-status">{order.status || 'Pending'}</span></td><td>{money(order.total_incl_tax, order.currency)}</td><td><Link className="text-link" to={`/orders/${encodeURIComponent(order.number)}/receipt`}>Print</Link></td>
    </tr>)}</tbody></table></div>}
    <Link className="text-link orders-back" to="/account">Back to account</Link>
  </section>
}
