import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts'
import {
  MessageSquareWarning, GitBranch, AlertTriangle, TrendingUp, BellRing
} from 'lucide-react'
import { getDashboardStats, getDashboardActivity, generateAlerts } from '../utils/api'
import { StatCard, GrowthBadge, StatusBadge, LoadingSpinner } from '../components/UI'

const GROWTH_COLOR = { Critical: '#ef4444', Rising: '#f59e0b', Slow: '#10b981' }

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [activity, setActivity] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = async () => {
    try {
      const [s, a] = await Promise.all([getDashboardStats(), getDashboardActivity()])
      setStats(s)
      setActivity(a)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleGenerateAlerts = async () => {
    await generateAlerts()
    await load()
  }

  if (loading) return <LoadingSpinner text="Loading dashboard..." />

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Surveillance Dashboard</div>
          <div className="page-subtitle">Real-time scam campaign lineage monitoring</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary" onClick={load}>↻ Refresh</button>
          <button className="btn btn-primary" onClick={handleGenerateAlerts}>
            <BellRing size={14} /> Run Alert Scan
          </button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <StatCard
          label="Complaints Today"
          value={stats?.complaints_today ?? 0}
          sub="Ingested in last 24h"
          icon={MessageSquareWarning}
          color="#3b82f6"
        />
        <StatCard
          label="Active Lineages"
          value={stats?.active_lineages ?? 0}
          sub="Campaigns being tracked"
          icon={GitBranch}
          color="#8b5cf6"
        />
        <StatCard
          label="Variants of Concern"
          value={stats?.variants_of_concern ?? 0}
          sub="Critical growth rate"
          icon={AlertTriangle}
          color="#ef4444"
        />
        <StatCard
          label="Est. Unreported"
          value={stats?.estimated_unreported ?? 0}
          sub="Nowcast correction"
          icon={TrendingUp}
          color="#f59e0b"
        />
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Activity chart */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: 'var(--text-secondary)' }}>
            7-Day Complaint Activity
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={activity} barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }}
                tickFormatter={d => d.slice(5)} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
                cursor={{ fill: 'rgba(59,130,246,0.08)' }}
              />
              <Bar dataKey="count" fill="#3b82f6" radius={[3, 3, 0, 0]} name="Complaints" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Growth distribution */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: 'var(--text-secondary)' }}>
            Lineage Growth Distribution
          </div>
          {stats?.lineages?.length > 0 ? (
            <div>
              {['Critical', 'Rising', 'Slow'].map(gr => {
                const count = stats.lineages.filter(l => l.growth_rate === gr).length
                const pct = stats.lineages.length > 0
                  ? Math.round(count / stats.lineages.length * 100) : 0
                return (
                  <div key={gr} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                      <span style={{ color: GROWTH_COLOR[gr] }}>{gr}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{count} lineages ({pct}%)</span>
                    </div>
                    <div style={{ background: 'var(--border)', borderRadius: 3, height: 6 }}>
                      <div style={{
                        background: GROWTH_COLOR[gr],
                        width: `${pct}%`,
                        height: '100%',
                        borderRadius: 3,
                        transition: 'width 0.5s',
                      }} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: 40 }}>No lineages yet.<br />
              <a href="/dataset" onClick={e => { e.preventDefault(); navigate('/dataset') }}>Load dataset →</a>
            </div>
          )}
        </div>
      </div>

      {/* Lineage table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
            Active Campaign Lineages
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/lineages')}>
            View All
          </button>
        </div>

        {stats?.lineages?.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Lineage</th>
                  <th>Script Type</th>
                  <th>Languages</th>
                  <th>Observed</th>
                  <th>Nowcast</th>
                  <th>Growth</th>
                  <th>Status</th>
                  <th>Banks</th>
                </tr>
              </thead>
              <tbody>
                {stats.lineages.map(l => (
                  <tr key={l.id} onClick={() => navigate(`/lineages/${l.id}`)}>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#e2e8f0' }}>{l.name}</div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>{l.id.slice(0, 8)}...</div>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{l.script_type}</td>
                    <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {l.language_mix.slice(0, 3).join(', ') || '—'}
                    </td>
                    <td style={{ fontWeight: 500 }}>{l.complaint_count}</td>
                    <td>
                      <span style={{ color: '#f59e0b', fontWeight: 600 }}>
                        {typeof l.nowcast_count === 'number' ? l.nowcast_count.toFixed(1) : '—'}
                      </span>
                    </td>
                    <td><GrowthBadge value={l.growth_rate} /></td>
                    <td><StatusBadge value={l.status} /></td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {l.banks_count} bank{l.banks_count !== 1 ? 's' : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <GitBranch size={32} />
            <p>No lineages tracked yet.</p>
            <p style={{ marginTop: 8, fontSize: 12 }}>
              <a href="/dataset" onClick={e => { e.preventDefault(); navigate('/dataset') }}>
                Load the dataset
              </a> or <a href="/ingest" onClick={e => { e.preventDefault(); navigate('/ingest') }}>
                ingest a complaint
              </a> to start tracking.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
