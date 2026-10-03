import { useEffect, useState } from 'react'
import { CalendarDays, RefreshCw } from 'lucide-react'
import { api } from '../services/api'

function localDateValue(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const today = localDateValue()

export default function ReportsPage() {
  const [startDate, setStartDate] = useState(today)
  const [endDate, setEndDate] = useState(today)
  const [report, setReport] = useState(null)
  const [currency, setCurrency] = useState('AFN')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function load(start = startDate, end = endDate) {
    setBusy(true)
    setError('')
    try {
      const data = await api.financialReport(start, end)
      setReport(data)
      setCurrency(data.currency || 'AFN')
    } catch (err) {
      setError(err.data?.detail || err.message || 'Could not load the report.')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { load(today, today) }, [])

  const money = amount => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(Number(amount || 0))
  const totals = report && [
    ['Gross sales incl. tax', report.revenue.gross_including_tax],
    ['Net revenue excl. tax', report.revenue.net_ex_tax],
    ['Refunds', report.pos_sales.refunds],
    ['Purchases', report.purchases.total],
    ['Operating expenses', report.expenses.total],
    ['Net profit estimate', report.profit.net],
  ]

  function submit(event) {
    event.preventDefault()
    if (startDate > endDate) {
      setError('The start date must be on or before the end date.')
      return
    }
    load()
  }

  return <section className="site-container page-section financial-report">
    <div className="page-title-row">
      <div><span className="eyebrow">FINANCIAL MANAGEMENT</span><h1>Daily accounts &amp; sales</h1><p>Review sales, returns, purchases, expenses and estimated profit by day.</p></div>
      <button className="button-outline report-refresh" type="button" onClick={() => load()} disabled={busy}><RefreshCw size={16} /> Refresh</button>
    </div>

    <form className="report-filters dashboard-panel" onSubmit={submit}>
      <label><span>From</span><input type="date" value={startDate} onChange={event => setStartDate(event.target.value)} required /></label>
      <label><span>To</span><input type="date" value={endDate} onChange={event => setEndDate(event.target.value)} required /></label>
      <button className="button-primary" disabled={busy}><CalendarDays size={16} /> {busy ? 'Loading…' : 'Show report'}</button>
    </form>

    {error && <div className="inline-error" role="alert">{error}</div>}
    {report && <>
      {report.accounting_status !== 'cogs_modeled' && <div className="report-notice" role="status"><strong>Profit needs review.</strong> {report.accounting_note}</div>}
      <div className="dashboard-kpis report-kpis">{totals.map(([label, value]) => <article className="dashboard-kpi" key={label}><small>{label}</small><strong>{money(value)}</strong></article>)}</div>

      <div className="dashboard-panels report-panels">
        <article className="dashboard-panel dashboard-panel-wide">
          <h2>Daily activity</h2>
          {!report.daily.length ? <p className="muted-empty">No activity for these dates.</p> : <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Date</th><th>POS sales</th><th>Online sales</th><th>Refunds</th><th>Purchases</th><th>Expenses</th><th>Net activity¹</th></tr></thead><tbody>{report.daily.map(day => <tr key={day.date}><td>{new Date(`${day.date}T00:00:00`).toLocaleDateString()}</td><td>{money(day.pos_sales)}<small className="report-count">{day.pos_transactions} receipts</small></td><td>{money(day.online_sales)}<small className="report-count">{day.online_orders} orders</small></td><td>{money(day.pos_refunds)}<small className="report-count">{day.refund_transactions} returns</small></td><td>{money(day.purchases)}</td><td>{money(day.expenses)}</td><td><strong>{money(day.net_cash_activity)}</strong></td></tr>)}</tbody></table></div>}
          <p className="report-footnote">¹ Sales less refunds, recorded purchases and expenses. This is an activity estimate, not a cash balance; purchase records do not store whether the supplier was paid. Sales include tax; profit below excludes collected tax.</p>
        </article>

        <article className="dashboard-panel">
          <h2>Payments received</h2>
          {!report.payment_breakdown.length ? <p className="muted-empty">No payments recorded for these dates.</p> : report.payment_breakdown.map(row => <div className="dashboard-row" key={row.method}><span>{row.method.replaceAll('_', ' ')}<small>{row.count} payments</small></span><b>{money(row.amount)}</b></div>)}
          <div className="dashboard-row"><span>Cash refunds</span><b>−{money(report.cash.refunded)}</b></div>
          <div className="dashboard-row report-total"><span>Net POS cash before expenses</span><b>{money(report.cash.net)}</b></div>
        </article>

        <article className="dashboard-panel">
          <h2>Profit estimate</h2>
          <div className="dashboard-row"><span>Net revenue, before tax</span><b>{money(report.revenue.net_ex_tax)}</b></div>
          <div className="dashboard-row"><span>Cost of goods sold</span><b>−{money(report.cogs.net)}</b></div>
          <div className="dashboard-row"><span>Operating expenses</span><b>−{money(report.expenses.total)}</b></div>
          <div className="dashboard-row report-total"><span>Estimated net profit</span><b>{money(report.profit.net)}</b></div>
          <p className="report-footnote">Purchases add stock and are shown as cash outflow in daily activity; they are not deducted again from profit.</p>
        </article>
      </div>
    </>}
  </section>
}
