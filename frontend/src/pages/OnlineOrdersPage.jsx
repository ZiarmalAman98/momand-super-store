import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { api } from '../services/api'

const money = (amount, currency = 'AFN') => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amount || 0)

export default function OnlineOrdersPage() {
  const [orders, setOrders] = useState([])
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrevious, setHasPrevious] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page) })
    if (submittedQuery) params.set('search', submittedQuery)
    api.onlineOrders(`?${params}`).then(result => {
      setOrders(result.results || result)
      setHasNext(Boolean(result.next))
      setHasPrevious(Boolean(result.previous))
    }).catch(err => setError(err.message)).finally(() => setLoading(false))
  }, [submittedQuery, page])

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">ONLINE STORE</span><h1>Online orders</h1><p>Customer orders, delivery details and payment status.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    <form className="balance-search" onSubmit={event => { event.preventDefault(); setSubmittedQuery(query.trim()) }}>
      <label className="shop-search"><Search size={17} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search order, customer, email or phone" /></label>
      <button className="button-primary">Search</button>
      {submittedQuery && <button className="button-outline" type="button" onClick={() => { setQuery(''); setPage(1); setSubmittedQuery('') }}>Clear</button>}
    </form>
    {loading ? <div className="product-skeleton detail-skeleton" /> : orders.length === 0 ? <div className="state-card"><strong>No online orders found.</strong><p>New online orders will appear here.</p></div> : <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Order</th><th>Date</th><th>Customer</th><th>Delivery</th><th>Items</th><th>Payment</th><th>Status</th><th>Total</th></tr></thead><tbody>{orders.map(order => <tr key={order.number}>
      <td><strong>{order.number}</strong></td>
      <td>{order.date_placed ? new Date(order.date_placed).toLocaleString() : '—'}</td>
      <td>{order.customer_name || 'Customer'}<small className="table-subtext">{order.customer_email}{order.phone ? ` · ${order.phone}` : ''}</small></td>
      <td>{order.delivery_address || '—'}</td>
      <td><div className="admin-order-items">{order.items.map(item => <div key={item.id}><img src={item.image?.startsWith('/') || /^https?:/i.test(item.image || '') ? item.image : item.image ? `/media/${item.image}` : '/media/image_not_found.jpg'} alt="" onError={event => { event.currentTarget.onerror = null; event.currentTarget.src = '/media/image_not_found.jpg' }} /><span>{item.title} × {item.quantity}</span></div>)}</div></td>
      <td>{order.payment ? <>{order.payment.method.replace('_', ' ')}<small className="table-subtext">{order.payment.status}</small></> : '—'}</td>
      <td><span className="order-status">{order.status || 'Pending'}</span></td>
      <td><strong>{money(order.total_incl_tax, order.currency)}</strong></td>
    </tr>)}</tbody></table></div>}
    {!loading && (hasPrevious || hasNext) && <div className="pagination-row"><button className="button-outline" disabled={!hasPrevious} onClick={() => setPage(current => Math.max(1, current - 1))}>Previous</button><span>Page {page}</span><button className="button-outline" disabled={!hasNext} onClick={() => setPage(current => current + 1)}>Next</button></div>}
  </section>
}
