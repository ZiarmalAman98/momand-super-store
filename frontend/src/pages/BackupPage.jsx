import { useState } from 'react'
import { Download } from 'lucide-react'
import { downloadStoreBackup } from '../services/api'

export default function BackupPage() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function download() {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const backup = await downloadStoreBackup()
      const url = URL.createObjectURL(backup.blob)
      const link = document.createElement('a')
      link.href = url
      link.download = backup.filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      setMessage('Backup downloaded. Store the ZIP file somewhere private and safe.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return <section className="site-container page-section">
    <div className="page-title-row"><div><span className="eyebrow">DATA SAFETY</span><h1>Store backup</h1><p>Download a copy of the database and uploaded product images.</p></div></div>
    {error && <div className="inline-error" role="alert">{error}</div>}{message && <div className="form-message" role="status">{message}</div>}
    <article className="dashboard-panel backup-panel"><h2>Download backup archive</h2><p>The ZIP contains a Django database export and all files in the media folder. Only the store superuser can create this archive.</p><button className="button-primary" onClick={download} disabled={busy}><Download size={17} />{busy ? 'Preparing backup…' : 'Download backup'}</button></article>
  </section>
}
