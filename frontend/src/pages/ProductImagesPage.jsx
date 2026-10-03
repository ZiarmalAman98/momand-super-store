import { useEffect, useState } from 'react'
import { Search, Upload } from 'lucide-react'
import { api, mediaUrl } from '../services/api'

export default function ProductImagesPage() {
  const [products, setProducts] = useState([])
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrevious, setHasPrevious] = useState(false)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    const params = new URLSearchParams({ page: String(page), ordering: 'title' })
    if (submittedQuery) params.set('search', submittedQuery)
    api.products(`?${params}`).then(result => {
      setProducts(result.results || result)
      setHasNext(Boolean(result.next))
      setHasPrevious(Boolean(result.previous))
    }).catch(err => setError(err.message)).finally(() => setLoading(false))
  }, [page, submittedQuery])

  async function upload(product, file) {
    if (!file) return
    setBusy(product.id)
    setError('')
    setMessage('')
    try {
      const result = await api.uploadProductImage(product.id, file)
      setProducts(current => current.map(item => item.id === product.id ? { ...item, image: result.image } : item))
      setMessage(`Image updated for ${product.title}. Customers can see it in the shop.`)
    } catch (err) {
      setError(err.data && typeof err.data === 'object' ? Object.values(err.data).flat().join(' ') : err.message)
    } finally {
      setBusy(null)
    }
  }

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">CUSTOMER CATALOGUE</span><h1>Product images</h1><p>Upload or replace the photos customers see in the shop and on product pages.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}{message && <div className="form-message" role="status">{message}</div>}
    <form className="balance-search" onSubmit={event => { event.preventDefault(); setPage(1); setSubmittedQuery(query.trim()) }}><label className="shop-search"><Search size={17} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search product name or barcode" /></label><button className="button-primary">Search</button>{submittedQuery && <button className="button-outline" type="button" onClick={() => { setQuery(''); setSubmittedQuery(''); setPage(1) }}>Clear</button>}</form>
    {loading ? <div className="product-skeleton detail-skeleton" /> : products.length === 0 ? <div className="state-card"><strong>No matching products.</strong><p>Try a different product name or barcode.</p></div> : <div className="orders-table-wrap"><table className="orders-table product-images-table"><thead><tr><th>Photo</th><th>Product</th><th>Category</th><th>Barcode</th><th>Upload</th></tr></thead><tbody>{products.map(product => <tr key={product.id}>
      <td><img className="product-image-preview" src={mediaUrl(product.image) || '/media/image_not_found.jpg'} alt={product.title} onError={event => { event.currentTarget.onerror = null; event.currentTarget.src = '/media/image_not_found.jpg' }} /></td>
      <td><strong>{product.title}</strong></td><td>{product.category_names?.join(', ') || '—'}</td><td>{product.upc || '—'}</td>
      <td><label className="button-outline product-image-upload"><Upload size={15} />{busy === product.id ? 'Uploading…' : product.image ? 'Replace photo' : 'Add photo'}<input type="file" accept="image/*" disabled={busy === product.id} onChange={event => { upload(product, event.target.files?.[0]); event.target.value = '' }} /></label></td>
    </tr>)}</tbody></table></div>}
    {!loading && (hasPrevious || hasNext) && <div className="pagination-row"><button className="button-outline" disabled={!hasPrevious} onClick={() => setPage(current => Math.max(1, current - 1))}>Previous</button><span>Page {page}</span><button className="button-outline" disabled={!hasNext} onClick={() => setPage(current => current + 1)}>Next</button></div>}
    <p className="report-footnote">Choose clear, product-specific photos in JPEG, PNG or WebP format. Maximum file size: 8 MB.</p>
  </section>
}
