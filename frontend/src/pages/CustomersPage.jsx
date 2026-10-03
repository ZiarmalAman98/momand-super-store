import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function CustomersPage() {
  const { user } = useAuth()
  const [customers, setCustomers] = useState([])
  const [posCustomers, setPosCustomers] = useState([])
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrevious, setHasPrevious] = useState(false)
  const [posHasNext, setPosHasNext] = useState(false)
  const [posHasPrevious, setPosHasPrevious] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page) })
    if (submittedQuery) params.set('search', submittedQuery)
    const canViewPosCustomers = user?.is_superuser || user?.groups?.some(group => ['Admin', 'Super Admin'].includes(group)) || user?.permissions?.includes('mis.view_possale_all')
    const tasks = [api.customers(`?${params}`).then(result => {
      setCustomers(result.results || result)
      setHasNext(Boolean(result.next))
      setHasPrevious(Boolean(result.previous))
    })]
    if (canViewPosCustomers) tasks.push(api.posCustomers(`?${params}`).then(result => {
      setPosCustomers(result.results || result)
      setPosHasNext(Boolean(result.next))
      setPosHasPrevious(Boolean(result.previous))
    }))
    Promise.all(tasks).catch(err => setError(err.message)).finally(() => setLoading(false))
  }, [submittedQuery, page, user])

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">CUSTOMER ACCOUNTS</span><h1>Customers</h1><p>Customer accounts registered with the online store.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    <form className="balance-search" onSubmit={event => { event.preventDefault(); setPage(1); setSubmittedQuery(query.trim()) }}><label className="shop-search"><Search size={17} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search name or email" /></label><button className="button-primary">Search</button>{submittedQuery && <button className="button-outline" type="button" onClick={() => { setQuery(''); setPage(1); setSubmittedQuery('') }}>Clear</button>}</form>
    <h2 className="customer-list-heading">Online accounts</h2>
    {loading ? <div className="product-skeleton detail-skeleton" /> : customers.length === 0 ? <div className="state-card"><strong>No online customer accounts found.</strong><p>New customer registrations will appear here.</p></div> : <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Customer</th><th>Email</th><th>Joined</th><th>Account status</th></tr></thead><tbody>{customers.map(customer => <tr key={customer.id}><td><strong>{[customer.first_name, customer.last_name].filter(Boolean).join(' ') || 'Customer'}</strong></td><td>{customer.email}</td><td>{new Date(customer.date_joined).toLocaleDateString()}</td><td>{customer.is_active ? 'Active' : 'Disabled'}</td></tr>)}</tbody></table></div>}
    {!loading && (hasPrevious || hasNext) && <div className="pagination-row"><button className="button-outline" disabled={!hasPrevious} onClick={() => setPage(current => Math.max(1, current - 1))}>Previous</button><span>Page {page}</span><button className="button-outline" disabled={!hasNext} onClick={() => setPage(current => current + 1)}>Next</button></div>}
    {(user?.is_superuser || user?.groups?.some(group => ['Admin', 'Super Admin'].includes(group)) || user?.permissions?.includes('mis.view_possale_all')) && <><h2 className="customer-list-heading">POS customers</h2>{loading ? <div className="product-skeleton detail-skeleton" /> : posCustomers.length === 0 ? <div className="state-card"><strong>No named POS customers found.</strong><p>Customer names entered by cashiers will appear here.</p></div> : <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Customer</th><th>Phone</th><th>POS sales</th><th>Total spent</th><th>Last sale</th></tr></thead><tbody>{posCustomers.map((customer, index) => <tr key={`${customer.customer_phone}-${customer.customer_name}-${index}`}><td><strong>{customer.customer_name || 'Customer'}</strong></td><td>{customer.customer_phone || '—'}</td><td>{customer.sales_count}</td><td>{new Intl.NumberFormat(undefined, { style: 'currency', currency: 'AFN' }).format(customer.total_spent || 0)}</td><td>{new Date(customer.last_sale).toLocaleDateString()}</td></tr>)}</tbody></table></div>}{!loading && (posHasPrevious || posHasNext) && <div className="pagination-row"><button className="button-outline" disabled={!posHasPrevious} onClick={() => setPage(current => Math.max(1, current - 1))}>Previous</button><span>Page {page}</span><button className="button-outline" disabled={!posHasNext} onClick={() => setPage(current => current + 1)}>Next</button></div>}</>}
  </section>
}
