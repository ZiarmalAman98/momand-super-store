import ProductCard from './ProductCard'

export default function ProductGrid({ products, loading, error, emptyText = 'No products found.' }) {
  if (loading) return <div className="product-grid" aria-label="Loading products">{Array.from({ length: 8 }, (_, i) => <div className="product-skeleton" key={i} />)}</div>
  if (error) return <div className="state-card error-state"><strong>We couldn’t load the products.</strong><p>{error}</p></div>
  if (!products?.length) return <div className="state-card"><strong>{emptyText}</strong><p>Try another search or browse a category.</p></div>
  return <div className="product-grid">{products.map((product) => <ProductCard key={product.id} product={product} />)}</div>
}
