import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function StoreSettingsPage() {
  const [settings, setSettings] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.storeSettings().then(setSettings).catch(err => setError(err.message)) }, [])

  function update(key, value) {
    setSettings(current => ({ ...current, [key]: value }))
    setMessage('')
  }

  async function save(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    try {
      setSettings(await api.updateStoreSettings({ ...settings, tax_rate: String(Number(settings.tax_rate) / 100) }))
      setMessage('Store settings saved.')
    } catch (err) {
      setError(err.data && typeof err.data === 'object' ? Object.values(err.data).flat().join(' ') : err.message)
    } finally {
      setBusy(false)
    }
  }

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">STORE CONFIGURATION</span><h1>Store settings</h1><p>Update the store details shown to online customers.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}{message && <div className="form-message" role="status">{message}</div>}
    {!settings ? !error && <div className="product-skeleton detail-skeleton" /> : <form className="store-form settings-form" onSubmit={save}>
      <div className="form-grid">
        <label>Store name<input required maxLength="160" value={settings.store_name} onChange={event => update('store_name', event.target.value)} /></label>
        <label>Tagline<input maxLength="240" value={settings.tagline} onChange={event => update('tagline', event.target.value)} /></label>
        <label>Currency code<input required maxLength="3" minLength="3" value={settings.currency} onChange={event => update('currency', event.target.value.toUpperCase())} /></label>
        <label>Tax rate (%)<input type="number" min="0" max="100" step="0.1" value={Number(settings.tax_rate) * 100} onChange={event => update('tax_rate', event.target.value)} /></label>
        <label>Phone<input maxLength="40" value={settings.phone} onChange={event => update('phone', event.target.value)} /></label>
        <label>Email<input type="email" value={settings.email} onChange={event => update('email', event.target.value)} /></label>
        <label className="checkout-wide">Store address<textarea rows="3" value={settings.address} onChange={event => update('address', event.target.value)} /></label>
      </div>
      <div className="report-notice">Payment options are managed separately under Payment methods. This tax rate applies to new POS sales and does not change existing sales.</div>
      <button className="button-primary" disabled={busy}>{busy ? 'Saving…' : 'Save store settings'}</button>
    </form>}
  </section>
}
