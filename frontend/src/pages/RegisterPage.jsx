import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '', password_confirm: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  function update(event) { setForm((old) => ({ ...old, [event.target.name]: event.target.value })) }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try { await register(form); navigate('/account') } catch (err) {
      const errors = err.data || {}
      setError(Object.entries(errors).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' · ') || err.message)
    } finally { setBusy(false) }
  }
  return <section className="auth-page site-container"><div className="auth-card"><span className="eyebrow">JOIN MOMAND</span><h1>Create your account</h1><p>Set up your account to manage your orders.</p>{error && <div className="inline-error" role="alert">{error}</div>}
    <form className="store-form" onSubmit={submit}><div className="form-row"><label>First name<input name="first_name" autoComplete="given-name" required value={form.first_name} onChange={update} /></label><label>Last name<input name="last_name" autoComplete="family-name" required value={form.last_name} onChange={update} /></label></div><label>Email address<input name="email" type="email" autoComplete="email" required value={form.email} onChange={update} /></label><label>Password<input name="password" type="password" autoComplete="new-password" minLength="9" required value={form.password} onChange={update} /></label><label>Confirm password<input name="password_confirm" type="password" autoComplete="new-password" minLength="9" required value={form.password_confirm} onChange={update} /></label><button className="button-primary full-button" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</button></form>
    <div className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></div>
  </div></section>
}
