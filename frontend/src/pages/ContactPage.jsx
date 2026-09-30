import { CheckCircle2, Mail, MapPin, Phone } from 'lucide-react'
import { useState } from 'react'
import { api } from '../services/api'

export default function ContactPage() {
  const [form, setForm] = useState({ name: '', email: '', phone: '', subject: '', message: '' })
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  function update(event) { setForm((old) => ({ ...old, [event.target.name]: event.target.value })) }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try { await api.sendContact(form); setSent(true) } catch (err) { setError(err.data ? Object.values(err.data).flat().join(' ') : err.message) } finally { setBusy(false) }
  }
  return <section className="site-container page-section"><div className="page-title-row"><div><span className="eyebrow">WE’RE HERE TO HELP</span><h1>Contact Momand</h1><p>Send a message to our store team and we’ll get back to you.</p></div></div>
    <div className="contact-layout"><div className="contact-information"><h2>Get in touch</h2><p>Store contact details can be set by the store administrator.</p><div className="contact-detail"><MapPin /><div><strong>Visit our store</strong><span>Address to be configured</span></div></div><div className="contact-detail"><Phone /><div><strong>Call the store</strong><span>Phone number to be configured</span></div></div><div className="contact-detail"><Mail /><div><strong>Email</strong><span>Contact email to be configured</span></div></div></div>
      <div className="contact-form-card">{sent ? <div className="success-state"><CheckCircle2 size={38} /><h2>Message received</h2><p>Your message has been saved for the store team.</p></div> : <><h2>Send us a message</h2>{error && <div className="inline-error" role="alert">{error}</div>}<form className="store-form" onSubmit={submit}><label>Your name<input name="name" autoComplete="name" required value={form.name} onChange={update} /></label><div className="form-row"><label>Email<input name="email" type="email" autoComplete="email" required value={form.email} onChange={update} /></label><label>Phone <span className="optional-label">optional</span><input name="phone" type="tel" autoComplete="tel" value={form.phone} onChange={update} /></label></div><label>Subject<input name="subject" required maxLength="180" value={form.subject} onChange={update} /></label><label>Message<textarea name="message" rows="5" required value={form.message} onChange={update} /></label><button className="button-primary" disabled={busy}>{busy ? 'Sending…' : 'Send message'}</button></form></>}</div>
    </div>
  </section>
}
