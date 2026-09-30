import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../services/api'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try { await api.confirmPasswordReset({ uid: params.get('uid'), token: params.get('token'), password }); setDone(true) }
    catch (err) { setError(err.data?.password?.join(' ') || err.message) }
    finally { setBusy(false) }
  }
  return <section className="auth-page site-container"><div className="auth-card"><span className="eyebrow">ACCOUNT RECOVERY</span><h1>Choose a new password</h1>{done ? <><p>Your password has been changed.</p><Link className="button-primary" to="/login">Sign in</Link></> : <><p>Use a password that is at least 9 characters and not commonly used.</p>{error && <div className="inline-error" role="alert">{error}</div>}<form className="store-form" onSubmit={submit}><label>New password<input type="password" autoComplete="new-password" minLength="9" required value={password} onChange={(event) => setPassword(event.target.value)} /></label><label>Confirm new password<input type="password" autoComplete="new-password" minLength="9" required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label><button className="button-primary full-button" disabled={busy || password !== confirmation}>{busy ? 'Updating…' : 'Reset password'}</button></form></>}</div></section>
}
