import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { api } from '../services/api'

const fields = [
  ['first_name', 'First name'], ['last_name', 'Last name'], ['phone', 'Phone number'],
  ['address', 'Street address'], ['district', 'District'], ['province', 'Province'], ['city', 'City'],
]

export default function CheckoutPage() {
  const { user, ready } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ first_name: user?.first_name || '', last_name: user?.last_name || '', phone: '', address: '', district: '', province: '', city: '', country: 'AF', payment_method: 'cod', delivery_notes: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [countries, setCountries] = useState([])
  useEffect(() => { api.countries().then(data => setCountries(data.results || [])).catch(() => {}) }, [])
  if (!ready) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton" /></section>
  if (!user) return <Navigate to="/login" replace />
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try { const order = await api.checkout(form); window.dispatchEvent(new Event('cart-updated')); navigate('/orders', { state: { placed: order.number } }) }
    catch (err) { setError(err.data && typeof err.data === 'object' ? Object.values(err.data).flat().join(' ') : err.message) }
    finally { setBusy(false) }
  }
  return <section className="site-container page-section"><div className="page-title-row"><div><span className="eyebrow">SECURE CHECKOUT</span><h1>Delivery details</h1><p>Confirm where and how you would like to receive your order.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    <form className="checkout-form" onSubmit={submit}><div className="checkout-fields">{fields.map(([key, label]) => <label key={key}>{label}<input required={['first_name','last_name','phone','address','city'].includes(key)} value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} /></label>)}<label>Country<select required value={form.country} onChange={e => setForm({ ...form, country: e.target.value })}><option value="">{countries.length ? 'Select a country' : 'Country list not configured'}</option>{countries.map(country => <option key={country.code} value={country.code}>{country.name}</option>)}</select></label><label className="checkout-wide">Delivery notes<textarea rows="3" value={form.delivery_notes} onChange={e => setForm({ ...form, delivery_notes: e.target.value })} /></label></div><aside className="order-summary"><h2>Cash on delivery</h2><p>Prices and available stock are checked again when your order is placed.</p><button className="button-primary checkout-button" disabled={busy || countries.length === 0}>{busy ? 'Placing order…' : 'Place order'}</button><Link className="text-link" to="/cart">Back to basket</Link></aside></form>
  </section>
}
