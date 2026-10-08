import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { GitBranch, Search } from 'lucide-react'
import { listLineages } from '../utils/api'
import { GrowthBadge, StatusBadge, LoadingSpinner } from '../components/UI'

export default function Lineages() {
  const [lineages, setLineages] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ growth: '', status: '', search: '' })
  const navigate = useNavigate()

  useEffect(() => {
    listLineages().then(setLineages).finally(() => setLoading(false))
  }, [])

  const filtered = lineages.filter(l => {
    if (filter.growth && l.growth_rate !== filter.growth) return false
    if (filter.status && l.status !== filter.status) return false
    if (filter.search && !l.name.toLowerCase().includes(filter.search.toLowerCase())
      && !l.script_type.toLowerCase().includes(filter.search.toLowerCase())) return false
    return true
  })

  if (loading) return <LoadingSpinner text="Loading lineages..." />

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Lineage Tree</div>
          <div className="page-subtitle">{lineages.length} campaign lineages tracked</div>
        </div>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            className="form-control"
            style={{ paddingLeft: 30 }}
            placeholder="Search by name or script type..."
            value={filter.search}
            onChange={e => setFilter(f => ({ ...f, search: e.target.value }))}
          />
        </div>
        <select className="form-control" style={{ width: 130 }} value={filter.growth}
          onChange={e => setFilter(f => ({ ...f, growth: e.target.value }))}>
          <option value="">All Growth</option>
          <option>Critical</option><option>Rising</option><option>Slow</option>
        </select>
        <select className="form-control" style={{ width: 140 }} value={filter.status}
          onChange={e => setFilter(f => ({ ...f, status: e.target.value }))}>
          <option value="">All Status</option>
          <option>Monitoring</option><option>Alert</option><option>Resolved</option>
        </select>
      </div>

      <div className="card">
        {filtered.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Lineage Name</th>
                  <th>Script Type</th>
                  <th>Languages</th>
                  <th>Observed</th>
                  <th>Nowcast</th>
                  <th>Growth</th>
                  <th>Churn</th>
                  <th>Status</th>
                  <th>Banks</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(l => (
                  <tr key={l.id} onClick={() => navigate(`/lineages/${l.id}`)}>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: 12 }}>{l.name}</div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{l.id.slice(0, 8)}...</div>
                    </td>
                    <td style={{ fontSize: 12 }}>{l.script_type}</td>
                    <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {(l.language_mix || []).slice(0, 2).join(', ') || '—'}
                    </td>
                    <td>{l.complaint_count}</td>
                    <td style={{ color: '#f59e0b', fontWeight: 600 }}>
                      {typeof l.nowcast_count === 'number' ? l.nowcast_count.toFixed(1) : '—'}
                    </td>
                    <td><GrowthBadge value={l.growth_rate} /></td>
                    <td><span className={`badge badge-${(l.churn_rate || '').toLowerCase()}`}>{l.churn_rate}</span></td>
                    <td><StatusBadge value={l.status} /></td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{l.banks_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <GitBranch size={32} />
            <p>No lineages found. {filter.search || filter.growth ? 'Try clearing filters.' : 'Load the dataset first.'}</p>
          </div>
        )}
      </div>
    </div>
  )
}
