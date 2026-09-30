import { useEffect, useRef, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { Barcode, Check, Minus, Plus, Printer, Search, Trash2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { api } from '../services/api'

export default function POSPage() {
  const { user, ready } = useAuth()
  const inputRef = useRef(null)
  const [term, setTerm] = useState('')
  const [results, setResults] = useState([])
  const [cart, setCart] = useState([])
  const [payment, setPayment] = useState('cash')
  const [tendered, setTendered] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sale, setSale] = useState(null)
  const [taxRate, setTaxRate] = useState(0)
  const width = localStorage.getItem('momand_receipt_width') || '80'

  useEffect(() => { api.storeConfig().then(config => setTaxRate(Number(config.tax_rate) || 0)).catch(() => {}) }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!term.trim()) { setResults([]); return }
      api.posSearch(term.trim()).then(data => {
        const matches = data.results || []
        setResults(matches)
        if (matches.length === 1 && matches[0].upc?.toLowerCase() === term.trim().toLowerCase()) add(matches[0])
      }).catch(err => setError(err.message))
    }, 170)
    return () => clearTimeout(timer)
  }, [term])

  if (!ready) return <main className="site-container page-section"><div className="product-skeleton detail-skeleton" /></main>
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_staff) return <main className="site-container page-section"><div className="state-card"><strong>Staff access required.</strong><p>Sign in with an authorised store account to use POS.</p></div></main>

  function add(product) {
    if (!product.in_stock) { setError(`${product.title} is out of stock.`); return }
    setCart(old => {
      const existing = old.find(item => item.id === product.id)
      if (existing) return old.map(item => item.id === product.id ? { ...item, quantity: Math.min(item.quantity + 1, product.available_quantity || 999) } : item)
      return [...old, { ...product, quantity: 1 }]
    })
    setError(''); setTerm(''); setResults([]); inputRef.current?.focus()
  }
  function change(id, quantity) { setCart(old => old.map(item => item.id === id ? { ...item, quantity } : item).filter(item => item.quantity > 0)) }
  const currency = cart[0]?.currency || 'AFN'
  const subtotal = cart.reduce((sum, item) => sum + Number(item.price || 0) * item.quantity, 0)
  const tax = cart.reduce((sum, item) => sum + Math.round(Number(item.price || 0) * taxRate * 100) / 100 * item.quantity, 0)
  const total = subtotal + tax
  const money = value => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(value || 0)

  async function pay(event) {
    event.preventDefault(); if (!cart.length) return
    setLoading(true); setError('')
    try {
      const result = await api.posSale({ items: cart.map(item => ({ product_id: item.id, quantity: item.quantity })), payment_method: payment, amount_tendered: payment === 'cash' ? tendered : total.toFixed(2) })
      setSale(result); setCart([]); setTendered('')
      if (localStorage.getItem('momand_receipt_auto_print') === 'true') setTimeout(() => window.print(), 150)
    } catch (err) { setError(err.data && typeof err.data === 'object' ? Object.values(err.data).flat().join(' ') : err.message) }
    finally { setLoading(false) }
  }

  return <main className="pos-shell">
    <header className="pos-heading"><div><span className="eyebrow">MOMAND SUPER STORE · CASHIER</span><h1>Point of sale</h1><p>Scan a barcode or search the product catalogue.</p></div><div className="pos-heading-actions"><Link className="button-outline" to="/pos/sales">Sales history</Link><Link className="button-outline" to="/pos/returns">Returns</Link><span className="pos-operator">{user.first_name || user.email}</span></div></header>
    <section className="pos-workspace"><div className="pos-catalogue"><label className="pos-search"><Barcode size={19} /><input ref={inputRef} autoFocus value={term} onChange={event => setTerm(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && results.length) { event.preventDefault(); add(results[0]) } }} placeholder="Scan barcode or search products…" /><Search size={18} /></label>
      {results.length > 0 && <div className="pos-results">{results.map(product => <button key={product.id} className="pos-result" onClick={() => add(product)}><span><b>{product.title}</b><small>{product.upc || 'No barcode'} · {product.in_stock ? `${product.available_quantity ?? '∞'} available` : 'Out of stock'}</small></span><strong>{money(product.price)}</strong></button>)}</div>}
      <div className="pos-catalogue-empty">{term ? (results.length ? 'Choose a matching product or press Enter to add the first exact barcode match.' : 'No matching products.') : 'The cashier product search is ready. Scanner input is handled as keyboard input.'}</div>
    </div><aside className="pos-checkout"><div className="pos-cart-head"><h2>Current sale</h2><span>{cart.reduce((sum,item)=>sum+item.quantity,0)} items</span></div><div className="pos-cart-lines">{cart.length === 0 ? <div className="pos-empty">Products added to this sale appear here.</div> : cart.map(item => <article className="pos-cart-row" key={item.id}><div className="pos-item-name"><strong>{item.title}</strong><small>{money(item.price)} each</small></div><div className="pos-qty"><button onClick={() => change(item.id,item.quantity-1)} aria-label="Decrease quantity"><Minus size={13}/></button><span>{item.quantity}</span><button disabled={item.available_quantity != null && item.quantity >= item.available_quantity} onClick={() => change(item.id,item.quantity+1)} aria-label="Increase quantity"><Plus size={13}/></button></div><b>{money(Number(item.price)*item.quantity)}</b><button className="icon-button danger-icon" onClick={() => change(item.id,0)} aria-label={`Remove ${item.title}`}><Trash2 size={15}/></button></article>)}</div>
      <div className="pos-totals"><div><span>Subtotal</span><b>{money(subtotal)}</b></div><div><span>Tax</span><b>{money(tax)}</b></div><div className="pos-grand-total"><span>Total</span><b>{money(total)}</b></div></div><form onSubmit={pay} className="pos-payment"><label>Payment method<select value={payment} onChange={event => setPayment(event.target.value)}><option value="cash">Cash</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option></select></label>{payment === 'cash' && <label>Amount received<input required type="number" min={total} step="0.01" value={tendered} onChange={event => setTendered(event.target.value)} placeholder={total.toFixed(2)} /></label>}<button className="button-primary pos-pay" disabled={loading || cart.length === 0}>{loading ? 'Recording sale…' : 'Complete sale'}</button></form>
    </aside></section>
    {error && <div className="inline-error pos-error" role="alert">{error}</div>}
    {sale && <div className="pos-sale-backdrop"><article className="pos-sale-modal" style={{'--receipt-width':`${width}mm`,page:width==='58'?'receipt58':'receipt80'}}><button className="pos-close" onClick={() => {setSale(null);inputRef.current?.focus()}}>×</button><div className="sale-success"><Check size={19}/><span>Sale recorded</span></div><p>Invoice <strong>{sale.invoice_number}</strong> · Change {money(sale.change_due)}</p><article className="thermal-receipt pos-receipt"><header><strong>MOMAND SUPER STORE</strong><span>Thank you for shopping with us</span></header><hr/><div>Invoice: {sale.invoice_number}</div><div>Date: {new Date(sale.created_at).toLocaleString()}</div><div>Cashier: {sale.cashier_name || user.email}</div><hr/>{sale.items.map((item,index)=><div className="receipt-columns" key={index}><span>{item.title}</span><span>{item.quantity}</span><span>{money(item.line_total)}</span></div>)}<hr/><div>Subtotal: {money(sale.subtotal)}</div><div>Tax: {money(sale.tax)}</div><div className="receipt-total"><span>TOTAL</span><strong>{money(sale.total)}</strong></div><div>Payment: {sale.payment_method}</div>{sale.payments?.map(payment => <div className="receipt-payment" key={payment.transaction_ref}><span>{payment.method}</span><span>{money(payment.amount)}</span></div>)}<div>Change: {money(sale.change_due)}</div><footer>Thank you for shopping!</footer></article><button className="button-primary" onClick={() => window.print()}><Printer size={16}/> Print receipt</button></article></div>}
  </main>
}
