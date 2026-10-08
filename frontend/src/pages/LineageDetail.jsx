import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, PieChart, Pie, Cell, AreaChart, Area
} from 'recharts'
import { ArrowLeft, AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react'
import { getLineage, updateLineageStatus } from '../utils/api'
import { ActSequence, GrowthBadge, StatusBadge, LoadingSpinner } from '../components/UI'

const LANG_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4']

export default function LineageDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [note, setNote] = useState('')
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    getLineage(id).then(setData).finally(() => setLoading(false))
  }, [id])

  const handleAction = async (status, extraNote = '') => {
    setUpdating(true)
    try {
      await updateLineageStatus(id, {
        status,
        analyst_hash: 'analyst_' + Date.now().toString(36),
        note: note || extraNote,
      })
      const fresh = await getLineage(id)
      setData(fresh)
      setNote('')
    } finally {
      setUpdating(false)
    }
  }

  if (loading) return <LoadingSpinner text="Loading lineage..." />
  if (!data) return <div className="empty-state">Lineage not found.</div>

  // Prepare chart data
  const chartData = (data.daily_counts || []).map((d, i) => ({
    date: d.date?.slice(5),
    observed: d.observed,
    nowcast: d.nowcast,
    cusum: data.cusum_series?.[i] ?? 0,
  }))

  // Language pie
  const langData = Object.entries(data.language_distribution || {}).map(([k, v]) => ({ name: k, value: v }))

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/lineages')}>
          <ArrowLeft size={13} /> Back
        </button>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{data.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {data.script_type} · Created {data.created_date?.slice(0, 10)}
          </div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          <GrowthBadge value={data.growth_rate} />
          <StatusBadge value={data.status} />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid-4" style={{ marginBottom: 20 }}>
        {[
          { label: 'Observed', value: data.complaint_count },
          { label: 'Nowcast (corrected)', value: data.nowcast_count?.toFixed(1), color: '#f59e0b' },
          { label: 'Rt (growth rate)', value: data.rt?.toFixed(2), color: data.rt > 1.3 ? '#ef4444' : data.rt > 1 ? '#f59e0b' : '#10b981' },
          { label: 'Banks Involved', value: data.banks_count },
        ].map(({ label, value, color }) => (
          <div className="card" key={label}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 26, fontWeight: 700, color: color || 'var(--text-primary)' }}>{value ?? '—'}</div>
          </div>
        ))}
      </div>

      {/* Act sequence */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>
          Script Act Sequence (Manipulation Pattern)
        </div>
        <ActSequence sequence={data.act_sequence} />
      </div>

      {/* Charts row */}
      <div className="grid-2" style={{ marginBottom: 16 }}>
        {/* Nowcast timeline */}
        <div className="card">
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
            Observed vs Nowcast-Corrected (30 days)
          </div>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="nowcastGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="obsGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', fontSize: 11, borderRadius: 6 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="nowcast" stroke="#f59e0b" fill="url(#nowcastGrad)" strokeWidth={2} name="Nowcast" strokeDasharray="4 2" />
                <Area type="monotone" dataKey="observed" stroke="#3b82f6" fill="url(#obsGrad)" strokeWidth={2} name="Observed" />
              </AreaChart>
            </ResponsiveContainer>
          ) : <div className="empty-state" style={{ padding: 40 }}>Not enough data</div>}
        </div>

        {/* Language distribution */}
        <div className="card">
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
            Language Distribution
          </div>
          {langData.length > 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <PieChart width={140} height={140}>
                <Pie data={langData} cx={65} cy={65} outerRadius={55} dataKey="value" strokeWidth={0}>
                  {langData.map((_, i) => <Cell key={i} fill={LANG_COLORS[i % LANG_COLORS.length]} />)}
                </Pie>
              </PieChart>
              <div style={{ flex: 1 }}>
                {langData.map((d, i) => (
                  <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: LANG_COLORS[i % LANG_COLORS.length] }} />
                    <span style={{ fontSize: 12 }}>{d.name}</span>
                    <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : <div className="empty-state" style={{ padding: 40 }}>No data</div>}
        </div>
      </div>

      {/* CUSUM chart */}
      {(data.cusum_series || []).length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
              CUSUM Early Warning Monitor
            </div>
            {data.cusum_triggered && (
              <span className="badge badge-critical">⚠ ALARM TRIGGERED</span>
            )}
          </div>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', fontSize: 11, borderRadius: 6 }} />
              <Line type="monotone" dataKey="cusum" stroke="#ef4444" strokeWidth={2} dot={false} name="CUSUM S+" />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
            CUSUM S+ value. Alarm triggers when S+ exceeds decision threshold h=4.0 (standardized units).
          </div>
        </div>
      )}

      {/* Identifiers */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
            Identifier Churn Panel
          </div>
          <span className={`badge badge-${(data.churn_rate || '').toLowerCase()}`}>
            Churn: {data.churn_rate}
          </span>
        </div>
        {data.identifiers?.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Type</th><th>Identifier</th><th>First Seen</th><th>Last Seen</th><th>Complaint Count</th>
                </tr>
              </thead>
              <tbody>
                {data.identifiers.map(id => (
                  <tr key={id.id}>
                    <td><span className={`badge badge-monitoring`}>{id.type}</span></td>
                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{id.display_value}</td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{id.first_seen?.slice(0, 10)}</td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{id.last_seen?.slice(0, 10)}</td>
                    <td>{id.complaint_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No identifiers extracted yet.</div>
        )}
      </div>

      {/* Complaints list */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Complaints in This Lineage ({data.complaints?.length})
        </div>
        {data.complaints?.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Text Preview</th><th>Reported</th><th>Bank</th><th>Language</th></tr>
              </thead>
              <tbody>
                {data.complaints.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontSize: 12, maxWidth: 300 }}>{c.raw_text}</td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{c.reported_date?.slice(0, 10)}</td>
                    <td style={{ fontSize: 12 }}>{c.source_bank}</td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{c.language}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="empty-state" style={{ padding: 30 }}>No complaints yet</div>}
      </div>

      {/* Actions */}
      <div className="card">
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Analyst Actions
        </div>
        <div className="form-group">
          <label>Note (optional)</label>
          <input className="form-control" value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="Add a note about this action..." />
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="btn btn-primary" disabled={updating} onClick={() => handleAction('Alert', 'Marked as Variant of Concern')}>
            <AlertTriangle size={13} /> Mark Variant of Concern
          </button>
          <button className="btn btn-secondary" disabled={updating} onClick={() => handleAction('Monitoring')}>
            Monitor
          </button>
          <button className="btn btn-secondary" disabled={updating} onClick={() => handleAction('Resolved')}>
            <CheckCircle size={13} /> Mark Resolved
          </button>
        </div>
      </div>
    </div>
  )
}
