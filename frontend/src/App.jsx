import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import IngestComplaint from './pages/IngestComplaint'
import Lineages from './pages/Lineages'
import LineageDetail from './pages/LineageDetail'
import Alerts from './pages/Alerts'
import CrossBank from './pages/CrossBank'
import AuditTrail from './pages/AuditTrail'
import AdminConfig from './pages/AdminConfig'
import DatasetLoader from './pages/DatasetLoader'

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <Sidebar />
        <main style={{
          marginLeft: 220,
          flex: 1,
          padding: '28px 32px',
          maxWidth: 'calc(100vw - 220px)',
          overflowX: 'hidden',
        }}>
          <Routes>
            <Route path="/"             element={<Dashboard />} />
            <Route path="/ingest"       element={<IngestComplaint />} />
            <Route path="/lineages"     element={<Lineages />} />
            <Route path="/lineages/:id" element={<LineageDetail />} />
            <Route path="/alerts"       element={<Alerts />} />
            <Route path="/crossbank"    element={<CrossBank />} />
            <Route path="/audit"        element={<AuditTrail />} />
            <Route path="/admin"        element={<AdminConfig />} />
            <Route path="/dataset"      element={<DatasetLoader />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
