import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Database, Download, CheckCircle, Loader } from 'lucide-react'
import { getDatasetStatus, loadDataset } from '../utils/api'

export default function DatasetLoader() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = async () => {
    const s = await getDatasetStatus()
    setStatus(s)
    setLoading(false)
  }

  useEffect(() => { load(); const i = setInterval(load, 2000); return () => clearInterval(i) }, [])

  const handleLoad = async () => {
    await loadDataset()
    await load()
  }

  const ingestProgress = status?.ingest_progress || {}
  const isRunning = ingestProgress.status === 'running'
  const isDone = ingestProgress.status === 'done'
  const pct = ingestProgress.total > 0 ? Math.round((ingestProgress.done / ingestProgress.total) * 100) : 0

  return (
    <div style={{ maxWidth: 700 }}>
      <div className="page-header">
        <div>
          <div className="page-title">Dataset Loader</div>
          <div className="page-subtitle">Load Mendeley SMS Phishing + synthetic Indian corpus</div>
        </div>
      </div>

      <div className="alert-banner alert-banner-info" style={{ marginBottom: 20 }}>
        📄 Dataset: Mendeley SMS Phishing Dataset (DOI: 10.17632/f45bkkt8pr.1) + 300 synthetic Indian-language scam messages (Hindi, Tamil, Telugu).
      </div>

      {/* Current status */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Current Database</div>
        <div className="grid-3">
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>COMPLAINTS INGESTED</div>
            <div style={{ fontSize: 26, fontWeight: 700 }}>{status?.complaint_count || 0}</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>LINEAGES CREATED</div>
            <div style={{ fontSize: 26, fontWeight: 700, color: '#8b5cf6' }}>{status?.lineage_count || 0}</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>STATUS</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: ingestProgress.status === 'idle' ? 'var(--text-muted)' : isRunning ? '#f59e0b' : '#10b981' }}>
              {ingestProgress.status || 'idle'}
            </div>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      {isRunning && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />
            <span style={{ fontSize: 13, fontWeight: 600 }}>
              Ingesting... {ingestProgress.done} / {ingestProgress.total}
            </span>
          </div>
          <div style={{ background: 'var(--border)', borderRadius: 4, height: 8 }}>
            <div style={{
              background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
              width: `${pct}%`,
              height: '100%',
              borderRadius: 4,
              transition: 'width 0.3s',
            }} />
          </div>
        </div>
      )}

      {isDone && (
        <div className="alert-banner alert-banner-info" style={{ marginBottom: 16, borderColor: '#10b981', background: 'rgba(16,185,129,0.1)' }}>
          <CheckCircle size={14} style={{ display: 'inline', marginRight: 6 }} />
          Dataset loaded successfully! {ingestProgress.done} complaints processed.
        </div>
      )}

      {/* Actions */}
      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Actions</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary"
            onClick={handleLoad}
            disabled={isRunning || loading}
          >
            <Download size={14} />
            {isRunning ? 'Loading...' : 'Load Dataset'}
          </button>
          {(status?.complaint_count || 0) > 0 && (
            <>
              <button className="btn btn-secondary" onClick={() => navigate('/')}>
                View Dashboard
              </button>
              <button className="btn btn-secondary" onClick={() => navigate('/lineages')}>
                View Lineages
              </button>
            </>
          )}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12 }}>
          Loading the dataset runs in the background. Each complaint is tagged, assigned to a lineage, and identifiers are hashed.
          Expect ~1–2 minutes for the full corpus.
        </div>
      </div>

      {/* What happens */}
      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>What Happens When You Load?</div>
        <ol style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8, paddingLeft: 20 }}>
          <li>Dataset is downloaded from Mendeley (or falls back to synthetic Indian corpus if unavailable)</li>
          <li>Each SMS is tagged with dialog-act sequences (GREET → IMPERSONATE → URGENCY → PAYMENT_REQUEST...)</li>
          <li>MinHash + Profile HMM assigns each complaint to a lineage or creates a new one</li>
          <li>Phone numbers, UPI IDs, URLs are extracted and SHA-256 hashed (only last 4 chars visible)</li>
          <li>Lineage metadata (script type, language distribution, banks) is updated</li>
          <li>Ready for nowcasting, CUSUM alerts, and cross-bank analysis</li>
        </ol>
      </div>
    </div>
  )
}
