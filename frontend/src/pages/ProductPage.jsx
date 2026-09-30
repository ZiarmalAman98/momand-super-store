import { ArrowLeft, Check, ShoppingBasket } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../services/api'

export default function ProductPage() {
  const { slug } = useParams()
  const [product, setProduct] = useState(null)
  const [error, setError] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [message, setMessage] = useState('')
  useEffect(() => { api.product(slug).then(setProduct).catch((err) => setError(err.message)) }, [slug])
  async function addToCart() {
    try { await api.addToCart(product.id, quantity); setMessage('Added to your cart'); window.dispatchEvent(new Event('cart-updated')) }
    catch (err) { setMessage(err.message) }
  }
  if (error) return <section className="site-container page-section"><div className="state-card error-state">{error}</div></section>
  if (!product) return <section className="site-container page-section"><div className="product-skeleton detail-skeleton" /></section>
  const image = product.image?.startsWith('/') ? product.image : product.image ? `/media/${product.image}` : null
  const price = product.price ? new Intl.NumberFormat(undefined, { style: 'currency', currency: product.currency || 'AFN' }).format(product.price) : 'Price unavailable'
  return <section className="site-container page-section"><Link className="back-link" to="/shop"><ArrowLeft size={16} /> Back to shop</Link>
    <div className="product-detail"><div className="detail-image">{image ? <img src={image} alt={product.title} /> : <div className="image-placeholder">{product.title.slice(0, 1)}</div>}</div>
      <div className="detail-info"><span className="eyebrow">{product.category_names?.[0] || 'MOMAND STORE'}</span><h1>{product.title}</h1><div className="detail-price">{price}</div><div className={product.in_stock ? 'detail-stock in-stock' : 'detail-stock out-stock'}>{product.in_stock ? <><Check size={16} /> Available</> : 'Currently unavailable'}</div>
        {product.description && <div className="detail-description">{product.description}</div>}
        {product.upc && <div className="detail-meta"><span>Barcode</span><strong>{product.upc}</strong></div>}
        <div className="purchase-controls"><label>Quantity<input type="number" min="1" max={product.available_quantity || 99} value={quantity} onChange={(event) => setQuantity(Math.max(1, Number(event.target.value)))} /></label><button className="button-primary" disabled={!product.in_stock} onClick={addToCart}><ShoppingBasket size={18} /> Add to basket</button></div>
        {message && <p className="form-message" role="status">{message}</p>}
      </div>
    </div>
  </section>
}
