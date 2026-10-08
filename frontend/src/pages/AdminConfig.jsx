import { useState, useEffect } from 'react'
import { Save } from 'lucide-react'
import { getAdminConfig, updateAdminConfig } from '../utils/api'
import { LoadingSpinner } from '../components/UI'

export default function AdminConfig() {
  const [cfg, setCfg] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getAdminConfig().then(setCfg).finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    await updateAdminConfig(cfg)
    setSaving(false); setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const update = (key, val) => setCfg(c => ({ ...c, [key]: parseFloat(val) || parseInt(val) || val }))

  if (loading || !cfg) return <LoadingSpinner text="Loading config..." />

  const delaySum = +(cfg.delay_instant_pct + cfg.delay_normal_pct + cfg.delay_tail_pct).toFixed(2)
  const delayValid = Math.abs(delaySum - 1) < 0.01

  return (
    <div style={{ maxWidth: 700 }}>
      <div className="page-header">
        <div>
          <div className="page-title">Admin Configuration</div>
          <div className="page-subtitle">Nowcasting delay calibration and alert thresholds</div>
        </div>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving || !delayValid}>
          <Save size={14} /> {saving ? 'Saving...' : saved ? '✓ Saved' : 'Save Changes'}
        </button>
      </div>

      {/* Delay distribution */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Reporting Delay Distribution</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          Controls how the nowcasting engine corrects for victims reporting fraud late. Values must sum to 1.0.
        </div>
        <div className="grid-3">
          {[
            { key: 'delay_instant_pct', label: 'Instant (0–6h)', hint: 'Default: 0.20' },
            { key: 'delay_normal_pct', label: 'Delayed (2–5 days)', hint: 'Default: 0.60' },
            { key: 'delay_tail_pct',   label: 'Tail lag (10–30 days)', hint: 'Default: 0.20' },
          ].map(({ key, label, hint }) => (
            <div className="form-group" key={key}>
              <label>{label}</label>
              <input type="number" step="0.05" min="0" max="1" className="form-control"
                value={cfg[key]} onChange={e => update(key, e.target.value)} />
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{hint}</div>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 12, marginTop: 4, color: delayValid ? '#10b981' : '#ef4444' }}>
          Sum: {delaySum} {delayValid ? '✓' : '✗ — must equal 1.0'}
        </div>
      </div>

      {/* Correction preview */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Correction Factor Preview</div>
        <div style={{ display: 'flex', gap: 10 }}>
          {[0, 1, 2, 3, 5, 7, 14].map(lag => {
            let p = lag === 0 ? cfg.delay_instant_pct
              : lag <= 5 ? cfg.delay_instant_pct + (cfg.delay_normal_pct * lag / 5)
              : Math.min(1, cfg.delay_instant_pct + cfg.delay_normal_pct + cfg.delay_tail_pct * Math.min((lag - 5) / 9, 1))
            const factor = p > 0.01 ? (1 / p).toFixed(2) : '—'
            return (
              <div key={lag} style={{ textAlign: 'center', flex: 1 }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>lag {lag}d</div>
                <div style={{ fontWeight: 700, fontSize: 16, color: '#f59e0b' }}>{factor}×</div>
              </div>
            )
          })}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
          2.0× means today's count is doubled — 50% of complaints haven't been filed yet.
        </div>
      </div>

      {/* Thresholds */}
      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Alert & PSI Thresholds</div>
        <div className="grid-2">
          {[
            { key: 'alert_threshold_daily', label: 'Daily alert threshold',   hint: 'Min daily complaints to trigger CUSUM' },
            { key: 'psi_min_banks',         label: 'PSI min banks',           hint: 'Min institutions for cross-bank surfacing' },
            { key: 'psi_min_complaints',    label: 'PSI min complaints',      hint: 'Min complaints for cross-bank surfacing' },
            { key: 'poison_report_cap',     label: 'Poisoning report cap',    hint: 'Max reports per reporter per lineage/24h' },
          ].map(({ key, label, hint }) => (
            <div className="form-group" key={key}>
              <label>{label}</label>
              <input type="number" min="1" className="form-control"
                value={cfg[key]} onChange={e => update(key, e.target.value)} />
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{hint}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
