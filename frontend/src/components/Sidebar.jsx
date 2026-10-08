import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquareWarning, GitBranch,
  BellRing, ShieldCheck, Building2, Settings, Database, Radar
} from 'lucide-react'

const navItems = [
  { to: '/',           icon: LayoutDashboard,       label: 'Dashboard' },
  { to: '/ingest',     icon: MessageSquareWarning,  label: 'Ingest Complaint' },
  { to: '/lineages',   icon: GitBranch,             label: 'Lineage Tree' },
  { to: '/alerts',     icon: BellRing,              label: 'Early Warnings' },
  { to: '/crossbank',  icon: Building2,             label: 'Cross-Bank Intel' },
  { to: '/audit',      icon: ShieldCheck,           label: 'Audit Trail' },
  { to: '/admin',      icon: Settings,              label: 'Admin Config' },
  { to: '/dataset',    icon: Database,              label: 'Dataset Loader' },
]

export default function Sidebar() {
  return (
    <aside style={{
      width: 220,
      minHeight: '100vh',
      background: '#0d1526',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      position: 'fixed',
      top: 0, left: 0, bottom: 0,
      zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{
        padding: '20px 20px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10
      }}>
        <div style={{
          width: 34, height: 34,
          background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
          borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Radar size={18} color="#fff" />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: '#e2e8f0' }}>ScamRadar</div>
          <div style={{ fontSize: 10, color: '#64748b', letterSpacing: '0.5px' }}>GENOMIC SURVEILLANCE</div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 8px' }}>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '9px 12px',
              borderRadius: 6,
              marginBottom: 2,
              fontSize: 13,
              fontWeight: isActive ? 600 : 400,
              color: isActive ? '#60a5fa' : '#94a3b8',
              background: isActive ? 'rgba(59,130,246,0.12)' : 'transparent',
              transition: 'all 0.1s',
              textDecoration: 'none',
            })}
            onMouseEnter={e => {
              if (!e.currentTarget.classList.contains('active'))
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
            }}
            onMouseLeave={e => {
              if (!e.currentTarget.classList.contains('active'))
                e.currentTarget.style.background = 'transparent'
            }}
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)' }}>
        <div style={{ fontSize: 10, color: '#475569' }}>RBI FREE-AI Compliant</div>
        <div style={{ fontSize: 10, color: '#334155', marginTop: 2 }}>Audit trail enabled</div>
      </div>
    </aside>
  )
}
