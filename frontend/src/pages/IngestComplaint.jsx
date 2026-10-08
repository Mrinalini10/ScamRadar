import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, CheckCircle, GitBranch, Upload, FileText } from 'lucide-react'
import { ingestComplaint } from '../utils/api'
import { ActSequence } from '../components/UI'
import api from '../utils/api'

const BANKS = ['Bank_A', 'Bank_B', 'Bank_C']
const LANGUAGES = ['auto', 'English', 'Hindi', 'Tamil', 'Telugu', 'Kannada', 'Hinglish']

const SAMPLE_MESSAGES = [
  'Dear customer, your SBI account will be blocked. Update KYC immediately at sbi-kyc-verify-123.xyz or call 9876543210',
  'Congratulations! You won ₹50,000 in BSNL lucky draw. Send your UPI ID to pay.1234@ybl to claim within 2 hours.',
  'आपका बैंक खाता बंद हो जाएगा। अभी KYC अपडेट करें: verify-aadhaar-456.in पर जाएं।',
  'URGENT: RBI alert - suspicious transaction on your account. Verify now: rbi-refund-789.com OTP required.',
  'Income Tax dept: Refund of ₹8,240 pending. Claim here: incometax-refund.xyz Enter your PAN and OTP.',
]

export default function IngestComplaint() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('single') // 'single' | 'bulk'
  const [form, setForm] = useState({
    raw_text: '',
    reported_date: new Date().toISOString().slice(0, 10),
    source_bank: 'Bank_A',
    language: 'auto',
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  // Bulk state
  const [csvFile, setCsvFile] = useState(null)
  const [bulkLoading, setBulkLoading] = useState(false)
  const [bulkResult, setBulkResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.raw_text.trim()) { setError('Message text is required.'); return }
    setLoading(true); setError(''); setResult(null)
    try {
      const res = await ingestComplaint({
        ...form,
        reported_date: new Date(form.reported_date).toISOString(),
      })
      setResult(res)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ingestion failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const handleBulkUpload = async () => {
    if (!csvFile) return
    setBulkLoading(true); setBulkResult(null)
    try {
      const formData = new FormData()
      formData.append('file', csvFile)
      const res = await api.post('/complaints/bulk', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setBulkResult(res.data)
    } catch (err) {
      setBulkResult({ error: err.response?.data?.detail || 'Upload failed' })
    } finally {
      setBulkLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <div className="page-header">
        <div>
          <div className="page-title">Ingest Complaint</div>
          <div className="page-subtitle">Submit a fraud complaint for analysis and lineage assignment</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
        {[['single', 'Single Complaint'], ['bulk', 'Bulk CSV Upload']].map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} style={{
            padding: '8px 16px', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 500,
            background: 'transparent',
            color: tab === key ? 'var(--accent-blue)' : 'var(--text-muted)',
            borderBottom: tab === key ? '2px solid var(--accent-blue)' : '2px solid transparent',
            marginBottom: -1,
          }}>{label}</button>
        ))}
      </div>

      {tab === 'single' && (
        <>
          {/* Sample messages */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Try a sample scam message
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {SAMPLE_MESSAGES.map((msg, i) => (
                <button key={i} className="btn btn-secondary btn-sm"
                  onClick={() => setForm(f => ({ ...f, raw_text: msg }))}>
                  Sample {i + 1}
                </button>
              ))}
            </div>
          </div>

          <div className="card">
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Complaint / SMS Text *</label>
                <textarea className="form-control" style={{ minHeight: 120 }}
                  placeholder="Paste the raw scam SMS or complaint text here..."
                  value={form.raw_text}
                  onChange={e => setForm(f => ({ ...f, raw_text: e.target.value }))} />
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  {form.raw_text.length} characters — identifiers (phone, UPI, URL) are auto-extracted and hashed
                </div>
              </div>

              <div className="grid-3">
                <div className="form-group">
                  <label>Reported Date</label>
                  <input type="date" className="form-control" value={form.reported_date}
                    onChange={e => setForm(f => ({ ...f, reported_date: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Source Bank</label>
                  <select className="form-control" value={form.source_bank}
                    onChange={e => setForm(f => ({ ...f, source_bank: e.target.value }))}>
                    {BANKS.map(b => <option key={b}>{b}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Language</label>
                  <select className="form-control" value={form.language}
                    onChange={e => setForm(f => ({ ...f, language: e.target.value }))}>
                    {LANGUAGES.map(l => <option key={l}>{l}</option>)}
                  </select>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>"auto" = detected from script</div>
                </div>
              </div>

              {error && <div className="alert-banner alert-banner-error" style={{ marginBottom: 16 }}>{error}</div>}

              <button type="submit" className="btn btn-primary" disabled={loading}>
                <Send size={14} />
                {loading ? 'Analysing...' : 'Submit & Analyse'}
              </button>
            </form>
          </div>

          {result && (
            <div className="card" style={{ marginTop: 20, borderColor: result.created_new_lineage ? '#8b5cf6' : 'var(--status-slow)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <CheckCircle size={20} color={result.created_new_lineage ? '#8b5cf6' : '#10b981'} />
                <div style={{ fontWeight: 600, fontSize: 15 }}>
                  {result.created_new_lineage ? 'New Lineage Created' : 'Assigned to Existing Lineage'}
                </div>
              </div>

              <div className="grid-2">
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>SCRIPT TYPE</div>
                  <div style={{ fontWeight: 600 }}>{result.script_type}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>LANGUAGE DETECTED</div>
                  <div style={{ fontWeight: 600 }}>{result.language}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>MATCH CONFIDENCE</div>
                  <div style={{ fontWeight: 600, color: result.lineage_confidence > 0.6 ? '#10b981' : '#f59e0b' }}>
                    {(result.lineage_confidence * 100).toFixed(0)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>COMPLAINT ID</div>
                  <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)' }}>{result.id}</div>
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>ACT SEQUENCE DETECTED</div>
                <ActSequence sequence={result.act_sequence} />
              </div>

              <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/lineages/${result.lineage_id}`)}>
                  <GitBranch size={12} /> View Lineage
                </button>
                <button className="btn btn-secondary btn-sm"
                  onClick={() => { setResult(null); setForm(f => ({ ...f, raw_text: '' })) }}>
                  Submit Another
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {tab === 'bulk' && (
        <div className="card">
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Upload CSV File</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
              Required columns: <code style={{ background: 'var(--bg-secondary)', padding: '1px 5px', borderRadius: 3 }}>raw_text</code>, <code style={{ background: 'var(--bg-secondary)', padding: '1px 5px', borderRadius: 3 }}>reported_date</code>, <code style={{ background: 'var(--bg-secondary)', padding: '1px 5px', borderRadius: 3 }}>source_bank</code>
              <br />Optional: <code style={{ background: 'var(--bg-secondary)', padding: '1px 5px', borderRadius: 3 }}>language</code>
            </div>
            <div style={{
              border: '2px dashed var(--border)',
              borderRadius: 8,
              padding: '32px',
              textAlign: 'center',
              background: csvFile ? 'rgba(59,130,246,0.05)' : 'transparent',
              cursor: 'pointer',
            }}
              onClick={() => document.getElementById('csv-input').click()}
            >
              <FileText size={28} style={{ color: 'var(--text-muted)', marginBottom: 8 }} />
              <div style={{ fontSize: 13, color: csvFile ? 'var(--accent-blue)' : 'var(--text-muted)' }}>
                {csvFile ? csvFile.name : 'Click to select CSV file'}
              </div>
              <input id="csv-input" type="file" accept=".csv" style={{ display: 'none' }}
                onChange={e => setCsvFile(e.target.files[0])} />
            </div>
          </div>

          <button className="btn btn-primary" onClick={handleBulkUpload}
            disabled={!csvFile || bulkLoading}>
            <Upload size={14} />
            {bulkLoading ? 'Uploading...' : 'Upload & Process'}
          </button>

          {bulkResult && !bulkResult.error && (
            <div className="alert-banner alert-banner-info" style={{ marginTop: 16, borderColor: '#10b981', background: 'rgba(16,185,129,0.1)' }}>
              <CheckCircle size={14} style={{ display: 'inline', marginRight: 6 }} />
              <strong>{bulkResult.ingested}</strong> complaints ingested.
              {bulkResult.failed > 0 && <span style={{ color: '#fca5a5' }}> {bulkResult.failed} failed.</span>}
            </div>
          )}
          {bulkResult?.error && (
            <div className="alert-banner alert-banner-error" style={{ marginTop: 16 }}>{bulkResult.error}</div>
          )}

          {/* Sample CSV download */}
          <div style={{ marginTop: 20, padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: 6 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>SAMPLE CSV FORMAT</div>
            <pre style={{ fontSize: 11, color: '#93c5fd', overflow: 'auto' }}>{`raw_text,reported_date,source_bank,language
"Dear SBI customer KYC blocked visit sbi-kyc.xyz",2026-10-01,Bank_A,English
"आपका खाता बंद होगा अभी verify करें",2026-10-02,Bank_B,Hindi`}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
