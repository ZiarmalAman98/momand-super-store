import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../services/api'

const money = (amount, currency = 'AFN') => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amount || 0)

export default function PaymentsPage() {
  const { user } = useAuth()
  const [payments, setPayments] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrevious, setHasPrevious] = useState(false)
  const canConfirm = user?.is_superuser || user?.groups?.some(group => ['Admin', 'Super Admin'].includes(group)) || user?.permissions?.includes('mis.change_paymenttransaction')

  async function load() {
    try {
      const result = await api.payments(`?page=${page}`)
      setPayments(result.results || result)
      setTotal(result.count ?? (result.results || result).length)
      setHasNext(Boolean(result.next))
      setHasPrevious(Boolean(result.previous))
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page])

  async function confirm(payment) {
    setBusy(payment.transaction_ref)
    setError('')
    try {
      await api.confirmPayment(payment.transaction_ref)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  const due = useMemo(() => payments.filter(payment => payment.status === 'pending').reduce((total, payment) => total + Number(payment.amount), 0), [payments])

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">PAYMENT RECORDS</span><h1>Payments</h1><p>POS receipts and online payments awaiting confirmation.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}
    <div className="dashboard-kpis report-kpis"><article className="dashboard-kpi"><span>All transactions</span><strong>{total}</strong></article><article className="dashboard-kpi"><span>Pending amount on this page</span><strong>{money(due)}</strong></article></div>
    {loading ? <div className="product-skeleton detail-skeleton" /> : payments.length === 0 ? <div className="state-card"><strong>No payment transactions yet.</strong><p>Payments recorded for POS and online orders will appear here.</p></div> : <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Reference</th><th>Date</th><th>Sale / order</th><th>Method</th><th>Status</th><th>Amount</th><th /></tr></thead><tbody>{payments.map(payment => <tr key={payment.transaction_ref}>
      <td><strong>{payment.transaction_ref}</strong></td>
      <td>{payment.paid_at || payment.created_at ? new Date(payment.paid_at || payment.created_at).toLocaleString() : '—'}</td>
      <td>{payment.order_number ? `Online · ${payment.order_number}` : payment.sale_invoice || '—'}</td>
      <td>{payment.method.replace('_', ' ')}</td>
      <td><span className="order-status">{payment.status.replace('_', ' ')}</span></td>
      <td><strong>{money(payment.amount)}</strong></td>
      <td>{canConfirm && payment.status === 'pending' && <button className="text-button" disabled={busy === payment.transaction_ref} onClick={() => confirm(payment)}>{busy === payment.transaction_ref ? 'Saving…' : 'Mark received'}</button>}</td>
    </tr>)}</tbody></table></div>}
    {!loading && (hasPrevious || hasNext) && <div className="pagination-row"><button className="button-outline" disabled={!hasPrevious} onClick={() => setPage(current => Math.max(1, current - 1))}>Previous</button><span>Page {page}</span><button className="button-outline" disabled={!hasNext} onClick={() => setPage(current => current + 1)}>Next</button></div>}
  </section>
}
