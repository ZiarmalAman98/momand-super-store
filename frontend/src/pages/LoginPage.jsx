import { LockKeyhole, Mail } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try { await login(email, password); navigate('/account') } catch (err) { setError(err.data?.detail || 'Email or password is incorrect.') } finally { setBusy(false) }
  }
  return <section className="auth-page site-container"><div className="auth-card"><span className="eyebrow">WELCOME BACK</span><h1>Sign in to your account</h1><p>See your account and keep track of your orders.</p>{error && <div className="inline-error" role="alert">{error}</div>}
    <form className="store-form" onSubmit={submit}><label>Email address<span className="field-icon"><Mail size={17} /><input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></span></label><label>Password<span className="field-icon"><LockKeyhole size={17} /><input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></span></label><button className="button-primary full-button" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button></form>
    <div className="auth-switch"><Link to="/forgot-password">Forgot password?</Link><br />New to Momand Store? <Link to="/register">Create an account</Link></div>
  </div></section>
}
