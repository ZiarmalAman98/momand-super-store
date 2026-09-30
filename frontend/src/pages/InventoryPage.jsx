import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'

export default function InventoryPage() {
  const { user, ready } = useAuth()
  const [stock, setStock] = useState([])
  const [movements, setMovements] = useState([])
  const [form, setForm] = useState({ stockrecord_id: '', quantity_delta: '', movement_type: 'adjustment', note: '' })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  async function reload() {
    try { const [low, history] = await Promise.all([apiRequest('/inventory/low-stock/'), apiRequest('/inventory/movements/')]); setStock(low.results || []); setMovements(history.results || history); setError('') }
    catch (err) { setError(err.message) } finally { setLoading(false) }
  }
  useEffect(() => { if (user?.is_staff) reload() }, [user])
  if (!ready) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton"/></section>
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_staff) return <section className="site-container page-section"><div className="state-card"><strong>Staff access required.</strong></div></section>
  async function adjust(event) {
    event.preventDefault(); setError(''); setMessage('')
    try { await apiRequest('/inventory/adjust/', { method:'POST', body:JSON.stringify(form) }); setMessage('Stock adjustment recorded.'); setForm({...form,quantity_delta:'',note:''}); await reload() }
    catch (err) { setError(err.data && typeof err.data==='object' ? Object.values(err.data).flat().join(' ') : err.message) }
  }
  return <section className="site-container page-section"><div className="page-title-row"><div><span className="eyebrow">STOCK CONTROL</span><h1>Inventory</h1><p>Current low-stock levels and an auditable movement ledger.</p></div><button className="button-outline" onClick={reload}><RefreshCw size={15}/> Refresh</button></div>
    {error&&<div className="inline-error" role="alert">{error}</div>}{message&&<div className="form-message">{message}</div>}
    <div className="inventory-grid"><article className="dashboard-panel"><h2><AlertTriangle size={17}/> Low stock ({stock.length})</h2>{loading?<div className="product-skeleton detail-skeleton"/>:stock.length===0?<p className="muted-empty">No products have crossed their configured minimum.</p>:<div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Product</th><th>Barcode</th><th>Available</th><th>Minimum</th><th>Status</th><th>Adjust</th></tr></thead><tbody>{stock.map(item=><tr key={item.stockrecord_id}><td>{item.product}</td><td>{item.barcode||'—'}</td><td>{item.available}</td><td>{item.minimum}</td><td>{item.status.replace('_',' ')}</td><td><button className="text-link" onClick={()=>setForm({...form,stockrecord_id:String(item.stockrecord_id)})}>Select</button></td></tr>)}</tbody></table></div>}</article>
      <article className="dashboard-panel"><h2>Record stock movement</h2><form className="staff-form" onSubmit={adjust}><label>Stock record ID<input required type="number" min="1" value={form.stockrecord_id} onChange={e=>setForm({...form,stockrecord_id:e.target.value})}/></label><label>Quantity change<input required type="number" step="1" value={form.quantity_delta} onChange={e=>setForm({...form,quantity_delta:e.target.value})} placeholder="Positive adds, negative removes"/></label><label>Reason<select value={form.movement_type} onChange={e=>setForm({...form,movement_type:e.target.value})}><option value="adjustment">Adjustment</option><option value="damage">Damaged stock</option><option value="return">Return</option><option value="opening">Opening stock</option></select></label><label>Note<input maxLength="240" value={form.note} onChange={e=>setForm({...form,note:e.target.value})}/></label><button className="button-primary">Save movement</button></form></article></div>
    <article className="dashboard-panel movement-history"><h2>Recent stock movements</h2>{loading?<div className="product-skeleton detail-skeleton"/>:movements.length===0?<p className="muted-empty">No inventory movements recorded.</p>:<div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Date</th><th>Product</th><th>Type</th><th>Change</th><th>After</th><th>Reference</th></tr></thead><tbody>{movements.map(item=><tr key={item.id}><td>{new Date(item.created_at).toLocaleString()}</td><td>{item.product}</td><td>{item.movement_type.replace('_',' ')}</td><td>{item.quantity_delta>0?'+':''}{item.quantity_delta}</td><td>{item.quantity_after}</td><td>{item.reference||'—'}</td></tr>)}</tbody></table></div>}</article>
  </section>
}
