import { Search, SlidersHorizontal } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import ProductGrid from '../components/ProductGrid'
import { api } from '../services/api'

export default function ShopPage() {
  const [params, setParams] = useSearchParams()
  const [query, setQuery] = useState(params.get('search') || '')
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [page, setPage] = useState(1)
  const [next, setNext] = useState(null)
  const [previous, setPrevious] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const category = params.get('category') || ''
  const ordering = params.get('ordering') || '-date_created'

  useEffect(() => { api.categories().then((data) => setCategories(data.results || data)).catch(() => {}) }, [])
  useEffect(() => {
    setLoading(true)
    setError('')
    const search = new URLSearchParams({ page: String(page), ordering })
    if (query.trim()) search.set('search', query.trim())
    if (category) search.set('category', category)
    api.products(`?${search.toString()}`).then((data) => {
      setProducts(data.results || [])
      setNext(data.next)
      setPrevious(data.previous)
    }).catch((err) => setError(err.message)).finally(() => setLoading(false))
  }, [page, query, category, ordering])

  function chooseCategory(value) {
    const nextParams = new URLSearchParams(params)
    value ? nextParams.set('category', value) : nextParams.delete('category')
    setParams(nextParams)
    setPage(1)
  }

  return <div className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">MOMAND SUPER STORE</span><h1>Shop all products</h1><p>Browse our current selection of everyday essentials.</p></div><div className="results-tag"><SlidersHorizontal size={16} /> Easy to browse</div></div>
    <div className="shop-toolbar"><form className="shop-search" onSubmit={(event) => { event.preventDefault(); setPage(1) }}><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search products, SKU or barcode" aria-label="Search products" /></form>
      <label className="sort-control">Sort by<select value={ordering} onChange={(event) => { setParams((old) => { const copy = new URLSearchParams(old); copy.set('ordering', event.target.value); return copy }); setPage(1) }}><option value="-date_created">Newest</option><option value="stockrecords__price">Price: low to high</option><option value="-stockrecords__price">Price: high to low</option><option value="title">Name</option></select></label>
    </div>
    <div className="shop-layout"><aside className="shop-sidebar"><h2>Categories</h2><button className={!category ? 'filter-link selected' : 'filter-link'} onClick={() => chooseCategory('')}>All products</button>{categories.map((item) => <button key={item.id} className={category === item.slug ? 'filter-link selected' : 'filter-link'} onClick={() => chooseCategory(item.slug)}>{item.name}<span>{item.product_count}</span></button>)}</aside>
      <div className="shop-results"><ProductGrid products={products} loading={loading} error={error} />{!loading && !error && <div className="pagination-row"><button className="button-outline" disabled={!previous} onClick={() => setPage((p) => Math.max(1, p - 1))}>Previous</button><span>Page {page}</span><button className="button-outline" disabled={!next} onClick={() => setPage((p) => p + 1)}>Next</button></div>}</div>
    </div>
  </div>
}
