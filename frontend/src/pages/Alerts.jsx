import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BellRing, CheckCircle, XCircle, ArrowUpCircle } from 'lucide-react'
import { listAlerts, updateAlert, generateAlerts } from '../utils/api'
import { GrowthBadge, LoadingSpinner } from '../components/UI'

const DISMISS_REASONS = ['Duplicate', 'False Positive', 'Resolved Externally', 'Under Investigation']

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('Active')
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    listAlerts(filterStatus ? { status: filterStatus } : {})
      .then(setAlerts).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterStatus])

  const handleAction = async (id, status, dismissed_reason = null) => {
    await updateAlert(id, {
      status,
      analyst_hash: 'analyst_' + Date.now().toString(36),
      dismissed_reason,
    })
    load()
  }

  const runScan = async () => {
    setLoading(true)
    await generateAlerts()
    load()
  }

  if (loading) return <LoadingSpinner text="Loading alerts..." />

  const active = alerts.filter(a => a.status === 'Active')
  const history = alerts.filter(a => a.status !== 'Active')

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Early Warning Alerts</div>
          <div className="page-subtitle">CUSUM-triggered campaign growth alarms</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <select className="form-control" style={{ width: 140 }} value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}>
            <option value="">All</option>
            <option>Active</option><option>Acknowledged</option>
            <option>Escalated</option><option>Dismissed</option>
          </select>
          <button className="btn btn-primary" onClick={runScan}>
            <BellRing size={14} /> Run Alert Scan
          </button>
        </div>
      </div>

      {/* Active alerts */}
      {active.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#ef4444', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Active Alerts ({active.length})
          </div>
          {active.map(a => (
            <AlertCard key={a.id} alert={a} onAction={handleAction}
              onNavigate={() => navigate(`/lineages/${a.lineage_id}`)} />
          ))}
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Alert History
          </div>
          {history.map(a => (
            <AlertCard key={a.id} alert={a} onAction={handleAction}
              onNavigate={() => navigate(`/lineages/${a.lineage_id}`)} />
          ))}
        </div>
      )}

      {alerts.length === 0 && (
        <div className="empty-state">
          <BellRing size={32} />
          <p>No alerts. Run a scan after loading the dataset.</p>
        </div>
      )}
    </div>
  )
}

function AlertCard({ alert: a, onAction, onNavigate }) {
  const [dismissReason, setDismissReason] = useState('')
  const [showDismiss, setShowDismiss] = useState(false)

  const borderColor = a.status === 'Active'
    ? (a.recommended_action.includes('I4C') ? '#ef4444' : '#f59e0b')
    : 'var(--border)'

  return (
    <div className="card" style={{ marginBottom: 12, borderLeft: `3px solid ${borderColor}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{a.lineage_name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{a.script_type}</div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <GrowthBadge value={a.status === 'Active' ? 'Rising' : 'Resolved'} />
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{a.created_at?.slice(0, 16)}</span>
        </div>
      </div>

      <div style={{ fontSize: 13, color: '#fcd34d', marginBottom: 8 }}>⚠ {a.trigger_reason}</div>

      <div className="grid-3" style={{ marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>NOWCAST COUNT</div>
          <div style={{ fontWeight: 600, color: '#f59e0b' }}>{a.nowcast_count?.toFixed(1)}</div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>RECOMMENDED ACTION</div>
          <div style={{ fontWeight: 600, fontSize: 12, color: a.recommended_action.includes('I4C') ? '#ef4444' : '#e2e8f0' }}>
            {a.recommended_action}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>STATUS</div>
          <div style={{ fontWeight: 600, fontSize: 12 }}>{a.status}</div>
        </div>
      </div>

      {a.dismissed_reason && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
          Dismissed: {a.dismissed_reason}
        </div>
      )}

      {a.status === 'Active' && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={onNavigate}>View Lineage</button>
          <button className="btn btn-secondary btn-sm"
            onClick={() => onAction(a.id, 'Acknowledged')}>
            <CheckCircle size={12} /> Acknowledge
          </button>
          <button className="btn btn-primary btn-sm"
            onClick={() => onAction(a.id, 'Escalated')}>
            <ArrowUpCircle size={12} /> Escalate to I4C
          </button>
          <button className="btn btn-danger btn-sm"
            onClick={() => setShowDismiss(!showDismiss)}>
            <XCircle size={12} /> Dismiss
          </button>
          {showDismiss && (
            <div style={{ display: 'flex', gap: 6, width: '100%', marginTop: 4 }}>
              <select className="form-control" style={{ flex: 1 }}
                value={dismissReason} onChange={e => setDismissReason(e.target.value)}>
                <option value="">Select reason...</option>
                {DISMISS_REASONS.map(r => <option key={r}>{r}</option>)}
              </select>
              <button className="btn btn-danger btn-sm" disabled={!dismissReason}
                onClick={() => onAction(a.id, 'Dismissed', dismissReason)}>
                Confirm Dismiss
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
