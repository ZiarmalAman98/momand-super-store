import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../services/api'

const CASHIER_PERMS = ['catalogue.view_product', 'mis.add_possale', 'mis.view_possale']
const ADMIN_HINT = ['mis.view_stockmovement', 'mis.view_purchase', 'mis.view_supplier', 'mis.view_expense', 'mis.view_possale', 'mis.add_possale', 'auth.view_user', 'auth.add_user', 'auth.change_user']

const emptyForm = () => ({ email: '', password: '', first_name: '', last_name: '', permissions: [...CASHIER_PERMS], is_active: true })

export default function UsersPage() {
  const { user } = useAuth()
  const [data, setData] = useState({ results: [], available_permissions: [] })
  const [form, setForm] = useState(emptyForm())
  const [editing, setEditing] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function load() {
    try { setData(await api.users()); setError('') } catch (err) { setError(err.message) }
  }
  useEffect(() => { if (user?.permissions?.users) load() }, [user])

  const available = data.available_permissions
  const editablePermissions = useMemo(() => available.filter(p => p.code !== 'auth.add_user' || user?.is_superuser || user?.permission_codes?.includes('auth.add_user')), [available, user])

  function toggleForm(key, code) {
    setForm(prev => ({ ...prev, permissions: prev.permissions.includes(code) ? prev.permissions.filter(x => x !== code) : [...prev.permissions, code] }))
  }
  function toggleEdit(code) {
    setEditForm(prev => ({ ...prev, permissions: prev.permissions.includes(code) ? prev.permissions.filter(x => x !== code) : [...prev.permissions, code] }))
  }
  function startEdit(row) {
    setEditing(row.id)
    setEditForm({ first_name: row.first_name, last_name: row.last_name, password: '', permissions: row.permissions, is_active: row.is_active })
    setMessage(''); setError('')
  }
  function applyCashierPreset() { setForm(prev => ({ ...prev, permissions: [...CASHIER_PERMS] })) }
  function applyAdminPreset() {
    const allowed = new Set(user?.permission_codes || [])
    setForm(prev => ({ ...prev, permissions: ADMIN_HINT.filter(code => user?.is_superuser || allowed.has(code)) }))
  }

  async function createUser(e) {
    e.preventDefault(); setError(''); setMessage('')
    try {
      await api.createUser(form)
      setMessage('User created successfully.')
      setForm(emptyForm())
      await load()
    } catch (err) { setError(err.data ? Object.values(err.data).flat().join(' ') : err.message) }
  }

  async function saveEdit(id) {
    setError(''); setMessage('')
    try {
      await api.updateUser(id, editForm)
      setMessage('User permissions updated successfully.')
      setEditing(null); setEditForm(null)
      await load()
    } catch (err) { setError(err.data ? Object.values(err.data).flat().join(' ') : err.message) }
  }

  async function toggleActive(row) {
    try { await api.updateUser(row.id, { is_active: !row.is_active }); await load() }
    catch (err) { setError(err.message) }
  }

  if (!user?.permissions?.users) return <section className="site-container page-section"><div className="state-card"><strong>Access denied.</strong></div></section>

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">ACCESS CONTROL</span><h1>Users & permissions</h1><p>Create users, choose exactly what they can do, change permissions later, or disable an account.</p></div></div>
    {error && <div className="inline-error">{error}</div>}
    {message && <div className="form-message">{message}</div>}

    <div className="admin-form-grid">
      <form className="form-card" onSubmit={createUser}>
        <div className="page-title-row"><div><h2>Create user</h2><p>Cashier accounts start with POS sale + product search + receipt access only.</p></div></div>
        <div className="form-grid">
          <label>Email<input type="email" required value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} /></label>
          <label>Password<input type="password" required minLength="8" value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} /></label>
          <label>First name<input value={form.first_name} onChange={e => setForm(p => ({ ...p, first_name: e.target.value }))} /></label>
          <label>Last name<input value={form.last_name} onChange={e => setForm(p => ({ ...p, last_name: e.target.value }))} /></label>
        </div>
        <div className="table-actions">
          <button type="button" className="button-outline" onClick={applyCashierPreset}>Cashier only</button>
          {user?.is_superuser && <button type="button" className="button-outline" onClick={applyAdminPreset}>Admin permissions</button>}
        </div>
        <h3>Permissions</h3>
        <div className="permission-grid">
          {editablePermissions.map(p => <label key={p.code} className="permission-item"><input type="checkbox" checked={form.permissions.includes(p.code)} onChange={() => toggleForm('permissions', p.code)} />{p.label}</label>)}
        </div>
        <button className="button-primary" type="submit">Create user</button>
      </form>

      <div className="form-card">
        <h2>Existing users</h2>
        <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Status</th><th>Permissions</th><th>Actions</th></tr></thead><tbody>
          {data.results.map(row => <tr key={row.id}>
            <td><strong>{row.email}</strong></td>
            <td>{row.first_name} {row.last_name}</td>
            <td>{row.is_superuser ? 'Owner' : row.groups.join(', ') || 'Custom'}</td>
            <td>{row.is_active ? 'Active' : 'Disabled'}</td>
            <td>{row.permissions.length}</td>
            <td>{!row.is_superuser && <div className="table-actions"><button className="text-button" type="button" onClick={() => startEdit(row)}>Edit permissions</button><button className="text-button" type="button" onClick={() => toggleActive(row)}>{row.is_active ? 'Disable' : 'Enable'}</button></div>}</td>
          </tr>)}
        </tbody></table></div>
      </div>
    </div>

    {editing && editForm && <div className="modal-backdrop"><section className="modal-card">
      <div className="page-title-row"><div><span className="eyebrow">USER RESTRICTIONS</span><h2>Edit permissions</h2><p>Remove every permission the user does not need. The server also prevents an admin from granting permissions they do not have.</p></div><button className="icon-button" type="button" onClick={() => setEditing(null)}>×</button></div>
      <div className="form-grid">
        <label>First name<input value={editForm.first_name} onChange={e => setEditForm(p => ({ ...p, first_name: e.target.value }))} /></label>
        <label>Last name<input value={editForm.last_name} onChange={e => setEditForm(p => ({ ...p, last_name: e.target.value }))} /></label>
        <label>New password<input type="password" minLength="8" value={editForm.password} onChange={e => setEditForm(p => ({ ...p, password: e.target.value }))} placeholder="Leave blank to keep current" /></label>
      </div>
      <h3>Permissions</h3>
      <div className="permission-grid">{editablePermissions.map(p => <label key={p.code} className="permission-item"><input type="checkbox" checked={editForm.permissions.includes(p.code)} onChange={() => toggleEdit(p.code)} />{p.label}</label>)}</div>
      <div className="modal-actions"><button className="button-outline" type="button" onClick={() => setEditing(null)}>Cancel</button><button className="button-primary" type="button" onClick={() => saveEdit(editing)}>Save restrictions</button></div>
    </section></div>}
  </section>
}
