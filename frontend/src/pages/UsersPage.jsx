import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'

const CASHIER_PERMS = [
  'mis.add_possale',
  'mis.view_possale',
  'mis.view_cashiershift',
  'mis.change_cashiershift',
]

export default function UsersPage() {
  const { user } = useAuth()
  const [data, setData] = useState({ results: [], available_permissions: [] })
  const [form, setForm] = useState({ email: '', password: '', first_name: '', last_name: '', permissions: CASHIER_PERMS })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function load() {
    try { setData(await api.users()); setError('') } catch (err) { setError(err.message) }
  }
  useEffect(() => { if (user?.permissions?.users) load() }, [user])

  const setField = (key, value) => setForm(prev => ({ ...prev, [key]: value }))
  const toggle = code => setField('permissions', form.permissions.includes(code)
    ? form.permissions.filter(x => x !== code)
    : [...form.permissions, code])

  async function createUser(e) {
    e.preventDefault(); setError(''); setMessage('')
    try {
      await api.createUser(form)
      setMessage('User created successfully.')
      setForm({ email: '', password: '', first_name: '', last_name: '', permissions: CASHIER_PERMS })
      await load()
    } catch (err) { setError(err.data ? Object.values(err.data).flat().join(' ') : err.message) }
  }

  async function toggleActive(row) {
    try { await api.updateUser(row.id, { is_active: !row.is_active }); await load() }
    catch (err) { setError(err.message) }
  }

  if (!user?.permissions?.users) return <section className="site-container page-section"><div className="state-card"><strong>Access denied.</strong></div></section>

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">ACCESS CONTROL</span><h1>Users & permissions</h1><p>Create a user and give only the permissions required for the job.</p></div></div>
    {error && <div className="inline-error">{error}</div>}
    {message && <div className="form-message">{message}</div>}

    <div className="admin-form-grid">
      <form className="form-card" onSubmit={createUser}>
        <h2>Create user</h2>
        <div className="form-grid">
          <label>Email<input type="email" required value={form.email} onChange={e => setField('email', e.target.value)} /></label>
          <label>Password<input type="password" required minLength="8" value={form.password} onChange={e => setField('password', e.target.value)} /></label>
          <label>First name<input value={form.first_name} onChange={e => setField('first_name', e.target.value)} /></label>
          <label>Last name<input value={form.last_name} onChange={e => setField('last_name', e.target.value)} /></label>
        </div>
        <h3>Permissions</h3>
        <div className="permission-grid">
          {data.available_permissions.map(p => <label key={p.code} className="permission-item"><input type="checkbox" checked={form.permissions.includes(p.code)} onChange={() => toggle(p.code)} />{p.label}</label>)}
        </div>
        <button className="button-primary" type="submit">Create user</button>
      </form>

      <div className="form-card">
        <h2>Existing users</h2>
        <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Status</th><th>Permissions</th><th></th></tr></thead><tbody>
          {data.results.map(row => <tr key={row.id}><td><strong>{row.email}</strong></td><td>{row.first_name} {row.last_name}</td><td>{row.is_superuser ? 'Owner' : row.groups.join(', ') || 'Custom'}</td><td>{row.is_active ? 'Active' : 'Disabled'}</td><td>{row.permissions.length}</td><td>{!row.is_superuser && <button className="text-button" type="button" onClick={() => toggleActive(row)}>{row.is_active ? 'Disable' : 'Enable'}</button>}</td></tr>)}
        </tbody></table></div>
      </div>
    </div>
  </section>
