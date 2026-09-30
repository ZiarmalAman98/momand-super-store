import { ArrowRight, Minus, Plus, ShoppingBasket, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function CartPage() {
  const [cart, setCart] = useState({ items: [], count: 0, total: '0.00', currency: 'AFN' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  async function reload() { try { setCart(await api.cart()); setError('') } catch (err) { setError(err.message) } finally { setLoading(false) } }
  useEffect(() => { reload() }, [])
  async function update(line, quantity) { try { setCart(await api.updateCartItem(line.id, quantity)); window.dispatchEvent(new Event('cart-updated')) } catch (err) { setError(err.message) } }
  async function remove(line) { try { setCart(await api.removeCartItem(line.id)); window.dispatchEvent(new Event('cart-updated')) } catch (err) { setError(err.message) } }
  const money = (value) => new Intl.NumberFormat(undefined, { style: 'currency', currency: cart.currency || 'AFN' }).format(value || 0)
  return <section className="site-container page-section"><div className="page-title-row"><div><span className="eyebrow">YOUR BASKET</span><h1>Shopping cart</h1><p>Review your items before checkout.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    {loading ? <div className="product-skeleton detail-skeleton" /> : cart.items.length === 0 ? <div className="empty-cart"><span><ShoppingBasket size={30} /></span><h2>Your cart is empty</h2><p>Browse the store and add products to your basket.</p><Link className="button-primary" to="/shop">Explore products <ArrowRight size={17} /></Link></div> : <div className="cart-layout"><div className="cart-lines">{cart.items.map((line) => <article className="cart-line" key={line.id}><Link className="cart-line-title" to={`/product/${line.slug}`}>{line.title}</Link><div className="quantity-stepper"><button aria-label="Decrease quantity" disabled={line.quantity <= 1} onClick={() => update(line, line.quantity - 1)}><Minus size={14} /></button><span>{line.quantity}</span><button aria-label="Increase quantity" onClick={() => update(line, line.quantity + 1)}><Plus size={14} /></button></div><strong>{money(line.line_total)}</strong><button className="icon-button danger-icon" aria-label={`Remove ${line.title}`} onClick={() => remove(line)}><Trash2 size={17} /></button></article>)}</div>
      <aside className="order-summary"><h2>Order summary</h2><div><span>Items ({cart.count})</span><strong>{money(cart.total)}</strong></div><p>Delivery and any applicable taxes are confirmed at checkout.</p><Link className="button-primary checkout-button" to="/checkout">Continue to checkout <ArrowRight size={17} /></Link><Link className="text-link" to="/shop">Continue shopping</Link></aside></div>}
  </section>
}
