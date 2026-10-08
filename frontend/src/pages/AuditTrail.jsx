import { useState, useEffect } from 'react'
import { ShieldCheck } from 'lucide-react'
import { listAuditLogs } from '../utils/api'
import { LoadingSpinner } from '../components/UI'

export default function AuditTrail() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    listAuditLogs().then(setLogs).finally(() => setLoading(false))
  }, [])

  const filtered = logs.filter(l =>
    !search ||
    l.action?.toLowerCase().includes(search.toLowerCase()) ||
    l.lineage_id?.includes(search)
  )

  if (loading) return <LoadingSpinner text="Loading audit trail..." />

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Audit Trail</div>
          <div className="page-subtitle">Tamper-evident log of all analyst actions — RBI FREE-AI compliant</div>
        </div>
      </div>

      <div className="alert-banner alert-banner-info" style={{ marginBottom: 20 }}>
        🔒 Every entry is HMAC-SHA256 signed. Analyst identities are one-way hashed. This log is read-only.
      </div>

      <div style={{ marginBottom: 16 }}>
        <input className="form-control" placeholder="Filter by action or lineage ID..."
          value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      <div className="card">
        {filtered.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Analyst</th>
                  <th>Action</th>
                  <th>Lineage</th>
                  <th>Detail</th>
                  <th>Hash</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(l => (
                  <tr key={l.id} style={{ cursor: 'default' }}>
                    <td style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {l.timestamp?.slice(0, 19).replace('T', ' ')}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{l.analyst_hash}</td>
                    <td>
                      <span style={{
                        fontSize: 11, fontWeight: 600,
                        color: l.action?.includes('ALERT') ? '#f59e0b' : '#93c5fd',
                      }}>{l.action}</span>
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                      {l.lineage_id?.slice(0, 8) || '—'}...
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {l.detail || '—'}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: 10, color: 'var(--text-muted)' }}>
                      {l.system_hash}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <ShieldCheck size={32} />
            <p>No audit log entries yet.</p>
          </div>
        )}
      </div>
    </div>
  )
}
