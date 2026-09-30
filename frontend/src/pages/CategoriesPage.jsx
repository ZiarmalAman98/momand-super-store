import { ArrowUpRight, Shapes } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'

export default function CategoriesPage() {
  const [categories, setCategories] = useState([])
  const [error, setError] = useState('')
  useEffect(() => { api.categories().then((data) => setCategories(data.results || data)).catch((err) => setError(err.message)) }, [])
  return <section className="site-container page-section"><div className="page-title-row"><div><span className="eyebrow">FIND YOUR AISLE</span><h1>Shop by category</h1><p>Explore the categories in the Momand Super Store catalogue.</p></div></div>
    {error ? <div className="state-card error-state">{error}</div> : <div className="category-grid category-grid-page">{categories.map((item, index) => <Link className={`category-card category-tone-${index % 4}`} key={item.id} to={`/shop?category=${item.slug}`}><Shapes size={23} /><strong>{item.name}</strong><small>{item.product_count} products</small><ArrowUpRight className="category-arrow" size={18} /></Link>)}</div>}
  </section>
}
