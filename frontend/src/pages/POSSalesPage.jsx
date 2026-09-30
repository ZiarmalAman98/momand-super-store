import { useEffect, useState } from 'react'
import { Navigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../services/api'

export default function POSSalesPage() {
  const { user, ready } = useAuth()
  const [sales, setSales] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => { if (user?.is_staff) api.posSales().then(data => setSales(data.results || data)).catch(err => setError(err.message)).finally(() => setLoading(false)) }, [user])
  if (!ready) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton" /></section>
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_staff) return <section className="site-container page-section"><div className="state-card"><strong>Staff access required.</strong></div></section>
  const money = (amount, currency) => new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'AFN' }).format(amount || 0)
  return <section className="site-container page-section"><div className="page-title-row"><div><span className="eyebrow">CASHIER OPERATIONS</span><h1>POS sales</h1><p>Completed in-store sales and receipt reprints.</p></div><Link className="button-primary" to="/pos">Open POS</Link></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    {loading ? <div className="product-skeleton detail-skeleton" /> : sales.length === 0 ? <div className="state-card"><strong>No POS sales yet.</strong><p>Completed cashier sales will appear here.</p></div> : <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Invoice</th><th>Date</th><th>Cashier</th><th>Items</th><th>Payment</th><th>Total</th><th>Receipt</th></tr></thead><tbody>{sales.map(sale => <tr key={sale.invoice_number}><td><strong>{sale.invoice_number}</strong></td><td>{new Date(sale.created_at).toLocaleString()}</td><td>{sale.cashier_name}</td><td>{sale.items.reduce((sum,item)=>sum+item.quantity,0)}</td><td>{sale.payment_method}</td><td>{money(sale.total,sale.currency)}</td><td><Link className="text-link" to={`/pos/sales/${encodeURIComponent(sale.invoice_number)}`}>Reprint</Link></td></tr>)}</tbody></table></div>}
  </section>
}
