import { LockKeyhole, Mail, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function AdminLoginPage() {
  const { login, logout } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const user = await login(email, password)
      if (!user?.is_staff) {
        await logout()
        throw new Error('This account does not have staff access.')
      }
      navigate('/admin/dashboard', { replace: true })
    } catch (err) {
      setError(err.message || err.data?.detail || 'Admin email or password is incorrect.')
    } finally {
      setBusy(false)
    }
  }

  return <section className="auth-page site-container">
    <div className="auth-card admin-login-card">
      <span className="eyebrow"><ShieldCheck size={14} /> STAFF CONTROL PANEL</span>
      <h1>Admin Login</h1>
      <p>Sign in with an authorized staff account to manage the store.</p>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <form className="store-form" onSubmit={submit}>
        <label>Email address<span className="field-icon"><Mail size={17} /><input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} /></span></label>
        <label>Password<span className="field-icon"><LockKeyhole size={17} /><input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></span></label>
        <button className="button-primary full-button" disabled={busy}>{busy ? 'Signing in…' : 'Sign in to Admin'}</button>
      </form>
      <div className="auth-switch"><Link to="/forgot-password">Forgot password?</Link><br />Return to <Link to="/">Momand Super Store</Link></div>
    </div>
  </section>
}
