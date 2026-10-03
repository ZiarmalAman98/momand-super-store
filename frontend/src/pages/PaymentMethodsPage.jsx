import { useEffect, useState } from 'react'
import { api } from '../services/api'

const choices = [
  { code: 'cod', name: 'Cash on delivery', help: 'Collect cash when the customer receives the order.' },
  { code: 'bank_transfer', name: 'Bank transfer', help: 'A cashier confirms the transfer from the Payments page.' },
]

export default function PaymentMethodsPage() {
  const [settings, setSettings] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.storeSettings().then(setSettings).catch(err => setError(err.message)) }, [])

  function toggle(code) {
    setSettings(current => {
      const methods = current.payment_methods.includes(code) ? current.payment_methods.filter(item => item !== code) : [...current.payment_methods, code]
      return { ...current, payment_methods: methods }
    })
    setMessage('')
  }

  async function save(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const saved = await api.updateStoreSettings({ payment_methods: settings.payment_methods, bank_transfer_instructions: settings.bank_transfer_instructions })
      setSettings(saved)
      setMessage('Payment methods updated. The checkout page now shows these options.')
    } catch (err) {
      setError(err.data && typeof err.data === 'object' ? Object.values(err.data).flat().join(' ') : err.message)
    } finally {
      setBusy(false)
    }
  }

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">ONLINE CHECKOUT</span><h1>Payment methods</h1><p>Choose which offline payment options customers can use at checkout.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}{message && <div className="form-message" role="status">{message}</div>}
    {!settings ? !error && <div className="product-skeleton detail-skeleton" /> : <form className="store-form settings-form" onSubmit={save}>
      <div className="settings-option-list">{choices.map(choice => <label className="settings-option" key={choice.code}><input type="checkbox" checked={settings.payment_methods.includes(choice.code)} onChange={() => toggle(choice.code)} /><span><strong>{choice.name}</strong><small>{choice.help}</small></span></label>)}</div>
      {settings.payment_methods.includes('bank_transfer') && <label className="settings-label">Bank transfer instructions shown to customers<textarea rows="4" required value={settings.bank_transfer_instructions} onChange={event => setSettings({ ...settings, bank_transfer_instructions: event.target.value })} placeholder="Bank name, account holder and account number" /></label>}
      <div className="report-notice">Orders using these methods remain pending until staff confirms payment from the Payments page.</div>
      <button className="button-primary" disabled={busy || !settings.payment_methods.length}>{busy ? 'Saving…' : 'Save payment methods'}</button>
    </form>}
  </section>
}
