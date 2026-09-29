import { useState } from 'react'
import { Routes, Route, NavLink, useNavigate, useLocation } from 'react-router-dom'
import type { User } from '../api/client'
import { loadSessions, newSession, switchSession, deleteSession, type Session } from '../store/session'
import UserMenu from './UserMenu'
import ChatPanel from '../panels/ChatPanel'
import ConfigPanel from '../panels/ConfigPanel'
import DashboardPanel from '../panels/DashboardPanel'
import RagPanel from '../panels/RagPanel'
import LogsPanel from '../panels/LogsPanel'

const NAV = [
  { path: '/chat', label: '对话', icon: ChatIcon },
  { path: '/config', label: '配置', icon: GearIcon },
  { path: '/dashboard', label: '仪表盘', icon: ChartIcon },
  { path: '/rag', label: '知识库', icon: BookIcon },
  { path: '/logs', label: '日志', icon: ListIcon },
]

function getTitle(pathname: string) {
  const hit = NAV.find((n) => pathname.startsWith(n.path))
  return hit ? hit.label : 'DataSage'
}

export default function AppShell() {
  const user = JSON.parse(localStorage.getItem('datasage_user') || '{}') as User
  const navigate = useNavigate()
  const location = useLocation()
  const [sessions, setSessions] = useState<Session[]>(() => loadSessions())
  const [version, setVersion] = useState(0)

  function refresh() {
    setSessions(loadSessions())
    setVersion((v) => v + 1)
  }

  function logout() {
    localStorage.removeItem('datasage_user')
    navigate('/login')
  }

  function onNewSession() {
    newSession()
    refresh()
    navigate('/chat')
  }

  function onSwitch(id: string) {
    switchSession(id)
    refresh()
    navigate('/chat')
  }

  function onDelete(id: string) {
    deleteSession(id)
    refresh()
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* 侧边栏 */}
      <aside
        style={{
          width: 240,
          flexShrink: 0,
          borderRight: '1px solid var(--border)',
          background: 'var(--surface)',
          display: 'flex',
          flexDirection: 'column',
          padding: '20px 12px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            fontSize: 20,
            fontWeight: 700,
            letterSpacing: '-0.02em',
            padding: '4px 12px 12px',
            color: 'var(--text)',
          }}
        >
          DataSage
        </div>

        <button className="btn btn-primary" onClick={onNewSession} style={{ margin: '0 8px 16px' }}>
          + 新建会话
        </button>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 2, flexShrink: 0 }}>
          {NAV.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '9px 12px',
                borderRadius: 'var(--radius-sm)',
                fontSize: 14,
                fontWeight: isActive ? 600 : 500,
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-soft)' : 'transparent',
                transition: 'background 0.15s var(--ease-out), color 0.15s var(--ease-out)',
              })}
            >
              <item.icon />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* 历史会话 */}
        <div
          style={{
            marginTop: 16,
            fontSize: 12,
            fontWeight: 600,
            color: 'var(--text-muted)',
            padding: '0 12px 8px',
            flexShrink: 0,
          }}
        >
          历史会话
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {sessions.map((s) => (
            <div
              key={s.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '6px 12px',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                fontSize: 13,
                color: 'var(--text-secondary)',
                transition: 'background 0.15s var(--ease-out)',
              }}
              onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = 'var(--surface-2)')}
              onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
              onClick={() => onSwitch(s.id)}
            >
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s.title}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete(s.id)
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: 14,
                  padding: '0 2px',
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* 主区 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <header
          style={{
            height: 60,
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
            borderBottom: '1px solid var(--border)',
            background: 'var(--surface)',
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 600 }}>{getTitle(location.pathname)}</div>
          <UserMenu user={user} onLogout={logout} />
        </header>

        <main style={{ flex: 1, overflow: 'auto', padding: 24 }}>
          <Routes>
            <Route path="/chat" element={<ChatPanel />} />
            <Route path="/config" element={<ConfigPanel />} />
            <Route path="/dashboard" element={<DashboardPanel />} />
            <Route path="/rag" element={<RagPanel />} />
            <Route path="/logs" element={<LogsPanel />} />
            <Route path="/" element={<ChatPanel />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function ChatIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

function GearIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

function ChartIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <rect x="7" y="12" width="3" height="6" rx="0.5" />
      <rect x="12" y="8" width="3" height="10" rx="0.5" />
      <rect x="17" y="5" width="3" height="13" rx="0.5" />
    </svg>
  )
}

function BookIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  )
}

function ListIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 6h13M8 12h13M8 18h13" />
      <path d="M3 6h.01M3 12h.01M3 18h.01" />
    </svg>
  )
}
