import { useEffect, useState } from 'react'
import { Navigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../services/api'

export default function POSSalesPage() {
  const { user, ready } = useAuth()
  const [sales, setSales] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [correctionSale, setCorrectionSale] = useState(null)
  const [quantities, setQuantities] = useState({})
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  async function loadSales() {
    setLoading(true)
    try {
      const data = await api.posSales()
      setSales(data.results || data)
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (user?.is_staff) loadSales() }, [user])

  if (!ready) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton" /></section>
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_staff) return <section className="site-container page-section"><div className="state-card"><strong>Staff access required.</strong></div></section>

  const money = (amount, currency) => new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'AFN' }).format(amount || 0)

  async function openCorrection(invoice) {
    setError(''); setMessage('')
    try {
      const sale = await api.posSaleDetail(invoice)
      setCorrectionSale(sale)
      setQuantities(Object.fromEntries(sale.items.map(item => [item.id, item.quantity])))
      setReason('')
    } catch (err) {
      setError(err.message)
    }
  }

  async function saveCorrection(event) {
    event.preventDefault()
    if (!correctionSale) return
    setSaving(true); setError(''); setMessage('')
    try {
      const items = correctionSale.items
        .filter(item => Number(quantities[item.id]) < Number(item.quantity))
        .map(item => ({ sale_item_id: item.id, corrected_quantity: Number(quantities[item.id]) }))
      if (!items.length) throw new Error('Reduce at least one item quantity before saving the correction.')
      const result = await api.correctPosSale(correctionSale.invoice_number, { items, reason })
      setMessage(`Sale ${result.invoice_number} corrected. New total: ${money(result.corrected_total, correctionSale.currency)}.`)
      setCorrectionSale(null)
      await loadSales()
    } catch (err) {
      setError(err.data && typeof err.data === 'object' ? Object.values(err.data).flat().join(' ') : err.message)
    } finally {
      setSaving(false)
    }
  }

  return <section className="site-container page-section">
    <div className="page-title-row">
      <div><span className="eyebrow">CASHIER OPERATIONS</span><h1>POS sales</h1><p>Completed in-store sales, corrections and receipt reprints.</p></div>
      <Link className="button-primary" to="/pos">Open POS</Link>
    </div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    {message && <div className="form-message" role="status">{message}</div>}
    {loading ? <div className="product-skeleton detail-skeleton" /> : sales.length === 0 ? <div className="state-card"><strong>No POS sales yet.</strong><p>Completed cashier sales will appear here.</p></div> : <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Invoice</th><th>Date</th><th>Cashier</th><th>Items</th><th>Payment</th><th>Total</th><th>Actions</th></tr></thead><tbody>{sales.map(sale => <tr key={sale.invoice_number}><td><strong>{sale.invoice_number}</strong></td><td>{new Date(sale.created_at).toLocaleString()}</td><td>{sale.cashier_name}</td><td>{sale.items.reduce((sum,item)=>sum+item.quantity,0)}</td><td>{sale.payment_method}</td><td>{money(sale.total,sale.currency)}</td><td><div className="table-actions"><Link className="text-link" to={`/pos/sales/${encodeURIComponent(sale.invoice_number)}`}>Reprint</Link>{user.can_correct_sales && <button className="text-button" type="button" onClick={() => openCorrection(sale.invoice_number)}>Correction</button>}</div></td></tr>)}</tbody></table></div>}

    {correctionSale && <div className="modal-backdrop"><article className="modal-card sale-correction-modal">
      <div className="page-title-row"><div><span className="eyebrow">ADMIN SALE CORRECTION</span><h2>Correct {correctionSale.invoice_number}</h2><p>This creates an audit record and adjusts stock. It does not delete the original sale.</p></div><button className="icon-button" type="button" onClick={() => setCorrectionSale(null)}>×</button></div>
      <form onSubmit={saveCorrection}>
        <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Product</th><th>Original</th><th>Correct quantity</th><th>Change</th></tr></thead><tbody>{correctionSale.items.map(item => <tr key={item.id}><td>{item.title}</td><td>{item.quantity}</td><td><input type="number" min="1" max={item.quantity} value={quantities[item.id] ?? item.quantity} onChange={e => setQuantities({...quantities, [item.id]: e.target.value})} /></td><td>{Number(quantities[item.id] ?? item.quantity) - item.quantity}</td></tr>)}</tbody></table></div>
        <label>Reason<input required maxLength="240" value={reason} onChange={e => setReason(e.target.value)} placeholder="Example: Customer received 8 instead of 10." /></label>
        <div className="modal-actions"><button className="button-outline" type="button" onClick={() => setCorrectionSale(null)}>Cancel</button><button className="button-primary" disabled={saving}>{saving ? 'Saving correction…' : 'Save correction'}</button></div>
      </form>
    </article></div>}
  </section>
}
