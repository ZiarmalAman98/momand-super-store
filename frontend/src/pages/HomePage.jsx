import { ArrowRight, BadgeCheck, Clock3, PackageCheck, ShieldCheck, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import ProductGrid from '../components/ProductGrid'
import { api } from '../services/api'

const benefits = [
  { icon: <BadgeCheck />, title: 'Products you can trust', text: 'A carefully selected range for your everyday needs.' },
  { icon: <PackageCheck />, title: 'Easy online ordering', text: 'Find products, add them to your basket and keep track of your order.' },
  { icon: <ShieldCheck />, title: 'Helpful customer care', text: 'Our store team is ready to help when you need us.' },
  { icon: <Clock3 />, title: 'Shop on your time', text: 'Browse the store whenever it suits your day.' },
]

export default function HomePage() {
  const [categories, setCategories] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.categories(), api.products('?ordering=title&page_size=8')])
      .then(([categoryData, productData]) => {
        setCategories(categoryData.results || categoryData)
        setProducts(productData.results || [])
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return <>
    <section className="hero-section">
      <div className="site-container hero-content">
        <div className="hero-copy">
          <span className="eyebrow"><Sparkles size={15} /> YOUR NEIGHBORHOOD STORE</span>
          <h1>Welcome to <span>Momand</span> Super Store</h1>
          <p>Your trusted store for quality products. Shop groceries, beverages, household items, personal care and more.</p>
          <div className="hero-buttons"><Link className="button-primary" to="/shop">Shop now <ArrowRight size={18} /></Link><Link className="button-light" to="/shop?sort=offers">Explore the store</Link></div>
          <div className="hero-trust"><span><BadgeCheck size={17} /> Quality products</span><span><ShieldCheck size={17} /> Friendly service</span></div>
        </div>
        <div className="hero-art" aria-label="Fresh grocery shopping illustration" role="img"><div className="hero-glow" /><div className="hero-basket"><div className="basket-fruit fruit-orange">●</div><div className="basket-fruit fruit-green">●</div><div className="basket-fruit fruit-red">●</div><div className="basket-fruit fruit-yellow">●</div><div className="basket-box"><span>GOOD</span><strong>FOOD</strong><small>GOOD MOOD</small></div><div className="basket-handle" /></div><div className="floating-tag tag-top">Fresh finds, every day</div><div className="floating-tag tag-bottom">Shopping made simple</div></div>
      </div>
      <div className="hero-wave" />
    </section>

    <section className="section-block categories-section"><div className="site-container">
      <div className="section-heading"><div><span className="eyebrow">BROWSE THE STORE</span><h2>Shop by category</h2><p>Find what you need in just a few clicks.</p></div><Link className="text-link" to="/categories">All categories <ArrowRight size={16} /></Link></div>
      <div className="category-grid">{categories.slice(0, 8).map((category, index) => <Link className={`category-card category-tone-${index % 4}`} key={category.id} to={`/shop?category=${category.slug}`}><span className="category-number">0{index + 1}</span><strong>{category.name}</strong><small>{category.product_count} products</small><ArrowRight className="category-arrow" size={17} /></Link>)}</div>
    </div></section>

    <section className="section-block featured-section"><div className="site-container">
      <div className="section-heading"><div><span className="eyebrow">PICKED FOR YOU</span><h2>Popular products</h2><p>Everyday favorites from our current catalogue.</p></div><Link className="text-link" to="/shop">Browse all products <ArrowRight size={16} /></Link></div>
      <ProductGrid products={products} loading={loading} error={error} />
    </div></section>

    <section className="service-section"><div className="site-container"><div className="section-heading centered"><div><span className="eyebrow">THE MOMAND DIFFERENCE</span><h2>A better everyday shop</h2><p>Good service makes every visit feel easier.</p></div></div><div className="benefit-grid">{benefits.map((item) => <article className="benefit-card" key={item.title}><span className="benefit-icon">{item.icon}</span><h3>{item.title}</h3><p>{item.text}</p></article>)}</div></div></section>
  </>
}
