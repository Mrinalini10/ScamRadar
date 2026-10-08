import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Lock } from 'lucide-react'
import { getCrossBank } from '../utils/api'
import { GrowthBadge, LoadingSpinner, PrivacyBanner } from '../components/UI'

export default function CrossBank() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    getCrossBank().then(setData).finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner text="Computing cross-bank intelligence..." />

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Cross-Bank Intelligence</div>
          <div className="page-subtitle">Campaigns detected across multiple institutions (PSI-based, privacy-preserving)</div>
        </div>
      </div>

      <PrivacyBanner message={data?.privacy_notice || 'No raw complaint data is shared between institutions. Only anonymised campaign sketches are compared.'} />

      <div className="alert-banner alert-banner-info" style={{ marginBottom: 20 }}>
        <Lock size={13} style={{ display: 'inline', marginRight: 6 }} />
        Threshold: min {data?.threshold?.min_banks} banks, min {data?.threshold?.min_complaints} complaints before a campaign is surfaced.
      </div>

      <div className="card">
        {data?.campaigns?.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Campaign Lineage</th>
                  <th>Script Type</th>
                  <th>Banks Involved</th>
                  <th>Total Complaints</th>
                  <th>Overlap Score</th>
                  <th>Growth</th>
                </tr>
              </thead>
              <tbody>
                {data.campaigns.map(c => (
                  <tr key={c.lineage_id} onClick={() => navigate(`/lineages/${c.lineage_id}`)}>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: 12 }}>{c.lineage_name}</div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{c.lineage_id.slice(0, 8)}...</div>
                    </td>
                    <td style={{ fontSize: 12 }}>{c.script_type}</td>
                    <td>
                      <span style={{
                        background: 'rgba(139,92,246,0.15)',
                        color: '#a78bfa',
                        padding: '2px 8px',
                        borderRadius: 4,
                        fontWeight: 700,
                        fontSize: 12,
                      }}>
                        {c.bank_count} banks
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{c.total_complaints}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ background: 'var(--border)', borderRadius: 3, height: 6, width: 80 }}>
                          <div style={{
                            background: '#8b5cf6',
                            width: `${c.overlap_score}%`,
                            height: '100%', borderRadius: 3,
                          }} />
                        </div>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.overlap_score}%</span>
                      </div>
                    </td>
                    <td><GrowthBadge value={c.growth_rate} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <Building2 size={32} />
            <p>No cross-bank campaigns detected yet.</p>
            <p style={{ fontSize: 12, marginTop: 8 }}>Load dataset and run alert scan to surface cross-institution activity.</p>
          </div>
        )}
      </div>
    </div>
  )
}
