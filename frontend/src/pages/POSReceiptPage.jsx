import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Printer } from 'lucide-react'
import { api } from '../services/api'

export default function POSReceiptPage() {
  const { invoice } = useParams()
  const [sale, setSale] = useState(null)
  const [error, setError] = useState('')
  const [width, setWidth] = useState(localStorage.getItem('momand_receipt_width') || '80')
  const [autoPrint, setAutoPrint] = useState(localStorage.getItem('momand_receipt_auto_print') === 'true')
  useEffect(() => { api.posSaleDetail(invoice).then(setSale).catch(err=>setError(err.message)) },[invoice])
  useEffect(() => { if (sale && autoPrint) window.print() },[sale,autoPrint])
  const money = amount => new Intl.NumberFormat(undefined,{style:'currency',currency:sale?.currency||'AFN'}).format(amount||0)
  return <section className="site-container page-section receipt-page" data-width={width} style={{'--receipt-width':`${width}mm`}}><div className="receipt-controls"><Link className="text-link" to="/pos/sales">Back to POS sales</Link><label>Paper width<select value={width} onChange={event=>{setWidth(event.target.value);localStorage.setItem('momand_receipt_width',event.target.value)}}><option value="58">58 mm</option><option value="80">80 mm</option></select></label><label><input type="checkbox" checked={autoPrint} onChange={event=>{setAutoPrint(event.target.checked);localStorage.setItem('momand_receipt_auto_print',String(event.target.checked))}}/> Print automatically</label><button className="button-primary" disabled={!sale} onClick={()=>window.print()}><Printer size={16}/> Print receipt</button></div>
    {error&&<div className="inline-error" role="alert">{error}</div>}{!sale&&!error&&<div className="product-skeleton detail-skeleton"/>}{sale&&<article className="thermal-receipt"><header><strong>MOMAND SUPER STORE</strong><span>Thank you for shopping with us</span></header><hr/><div>Invoice: {sale.invoice_number}</div><div>Date: {new Date(sale.created_at).toLocaleString()}</div><div>Cashier: {sale.cashier_name}</div><hr/>{sale.items.map((item,index)=><div className="receipt-columns" key={index}><span>{item.title}</span><span>{item.quantity}</span><span>{money(item.line_total)}</span></div>)}<hr/><div>Subtotal: {money(sale.subtotal)}</div><div>Discount: {money(sale.discount)}</div><div>Tax: {money(sale.tax)}</div><div className="receipt-total"><span>TOTAL</span><strong>{money(sale.total)}</strong></div><div>Payment: {sale.payment_method}</div>{sale.payments?.map(payment => <div className="receipt-payment" key={payment.transaction_ref}><span>{payment.method}</span><span>{money(payment.amount)}</span></div>)}<div>Paid: {money(sale.amount_tendered)}</div><div>Change: {money(sale.change_due)}</div><footer>Thank you for shopping!</footer></article>}</section>
}
