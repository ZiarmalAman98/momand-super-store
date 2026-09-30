import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try { await api.requestPasswordReset(email); setSent(true) } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <section className="auth-page site-container"><div className="auth-card"><span className="eyebrow">ACCOUNT RECOVERY</span><h1>Reset your password</h1>{sent ? <p>If an account matches that email, we’ve sent a reset link. In local development, check the Django console email output.</p> : <><p>Enter the email used for your account. We’ll send a password reset link if it matches.</p>{error && <div className="inline-error" role="alert">{error}</div>}<form className="store-form" onSubmit={submit}><label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><button className="button-primary full-button" disabled={busy}>{busy ? 'Sending…' : 'Send reset link'}</button></form></>}<div className="auth-switch"><Link to="/login">Back to sign in</Link></div></div></section>
}
