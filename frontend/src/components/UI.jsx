export function Badge({ value, type }) {
  const cls = `badge badge-${(value || '').toLowerCase().replace(/ /g, '-')}`
  return <span className={cls}>{value}</span>
}

export function GrowthBadge({ value }) {
  return <Badge value={value} />
}

export function ChurnBadge({ value }) {
  return <Badge value={value} />
}

export function StatusBadge({ value }) {
  const cls = value === 'Active' ? 'badge badge-critical'
    : value === 'Monitoring' ? 'badge badge-monitoring'
    : value === 'Resolved' ? 'badge badge-resolved'
    : 'badge badge-monitoring'
  return <span className={cls}>{value}</span>
}

export function ActSequence({ sequence }) {
  if (!sequence || sequence.length === 0) return <span style={{ color: 'var(--text-muted)' }}>—</span>
  return (
    <span>
      {sequence.map((act, i) => (
        <span key={i}>
          <span className="act-tag">{act}</span>
          {i < sequence.length - 1 && <span className="act-arrow">→</span>}
        </span>
      ))}
    </span>
  )
}

export function StatCard({ label, value, sub, icon: Icon, color = '#3b82f6' }) {
  return (
    <div className="card" style={{ position: 'relative', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600, marginBottom: 8 }}>
            {label}
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>{value}</div>
          {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{sub}</div>}
        </div>
        {Icon && (
          <div style={{
            width: 38, height: 38,
            background: `${color}18`,
            border: `1px solid ${color}30`,
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Icon size={18} color={color} />
          </div>
        )}
      </div>
    </div>
  )
}

export function PrivacyBanner({ message }) {
  return (
    <div className="alert-banner alert-banner-info" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      🔒 {message}
    </div>
  )
}

export function LoadingSpinner({ text = 'Loading...' }) {
  return (
    <div className="loading">
      <div className="spinner" />
      {text}
    </div>
  )
}
