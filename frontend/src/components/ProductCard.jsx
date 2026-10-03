import { Link } from 'react-router-dom'
import { ShoppingBasket } from 'lucide-react'
import { useState } from 'react'
import { api, mediaUrl } from '../services/api'

export default function ProductCard({ product }) {
  const [adding, setAdding] = useState(false)
  const [message, setMessage] = useState('')
  const image = mediaUrl(product.image) || '/media/image_not_found.jpg'

  async function addToCart() {
    setAdding(true)
    setMessage('')
    try {
      await api.addToCart(product.id)
      setMessage('Added to cart')
      window.dispatchEvent(new Event('cart-updated'))
    } catch (error) {
      setMessage(error.message)
    } finally {
      setAdding(false)
      window.setTimeout(() => setMessage(''), 2500)
    }
  }

  return (
    <article className="product-card">
      <Link className="product-image" to={`/product/${product.slug}`}>
        <img src={image} alt={product.title} loading="lazy" onError={event => { event.currentTarget.onerror = null; event.currentTarget.src = '/media/image_not_found.jpg' }} />
        {!product.in_stock && <span className="stock-pill">Out of stock</span>}
      </Link>
      <div className="product-info">
        {product.category_names?.[0] && <span className="product-category">{product.category_names[0]}</span>}
        <Link className="product-title" to={`/product/${product.slug}`}>{product.title}</Link>
        <div className="product-bottom"><strong>{product.price ? new Intl.NumberFormat(undefined, { style: 'currency', currency: product.currency || 'AFN' }).format(product.price) : 'Price unavailable'}</strong>
          <button className="add-button" onClick={addToCart} disabled={!product.in_stock || adding} aria-label={`Add ${product.title} to cart`}><ShoppingBasket size={17} />{adding ? 'Adding' : 'Add'}</button>
        </div>
        {message && <p className="card-message" role="status">{message}</p>}
      </div>
    </article>
  )
}
