import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiRequest } from '../services/api'

export default function ReceiptPage() {
  const { number } = useParams()
  const [order, setOrder] = useState(null)
  const [error, setError] = useState('')
  const [width, setWidth] = useState(localStorage.getItem('momand_receipt_width') || '80')
  useEffect(() => { apiRequest(`/orders/${encodeURIComponent(number)}/`).then(setOrder).catch(err => setError(err.message)) }, [number])
  useEffect(() => { if (order && localStorage.getItem('momand_receipt_auto_print') === 'true') window.print() }, [order])
  const currency = order?.currency || 'AFN'
  const money = amount => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amount || 0)
  return <section className="site-container page-section receipt-page" data-width={width} style={{ '--receipt-width': `${width}mm` }}>
    <div className="receipt-controls"><Link className="text-link" to="/orders">Back to orders</Link><label>Paper width<select value={width} onChange={event => { setWidth(event.target.value); localStorage.setItem('momand_receipt_width', event.target.value) }}><option value="58">58 mm</option><option value="80">80 mm</option></select></label><label><input type="checkbox" checked={localStorage.getItem('momand_receipt_auto_print') === 'true'} onChange={event => localStorage.setItem('momand_receipt_auto_print', String(event.target.checked))} /> Print automatically</label><button className="button-primary" onClick={() => window.print()} disabled={!order}>Print receipt</button></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    {!order && !error ? <div className="product-skeleton detail-skeleton" /> : order && <article className="thermal-receipt"><header><strong>MOMAND SUPER STORE</strong><span>Thank you for shopping with us</span></header><hr /><div>Receipt: {order.number}</div><div>Date: {order.date_placed ? new Date(order.date_placed).toLocaleString() : '—'}</div><div>Status: {order.status || 'Pending'}</div><hr /><div className="receipt-columns"><b>Product</b><b>Qty</b><b>Total</b></div>{order.items.map(item => <div className="receipt-columns" key={item.id}><span>{item.title}</span><span>{item.quantity}</span><span>{money(item.line_price_incl_tax)}</span></div>)}<hr /><div className="receipt-total"><span>Total</span><strong>{money(order.total_incl_tax)}</strong></div><footer>Keep this receipt for your records.</footer></article>}
  </section>
}
