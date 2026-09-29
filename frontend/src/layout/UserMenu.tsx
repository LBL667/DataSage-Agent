import { useState, useRef, useEffect } from 'react'
import type { User } from '../api/client'

export default function UserMenu({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const initial = (user.username || 'U').slice(0, 1).toUpperCase()

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          background: 'transparent',
          border: 'none',
          padding: '4px 8px 4px 4px',
          borderRadius: 999,
          transition: 'background 0.15s var(--ease-out)',
        }}
        onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = 'var(--surface-2)')}
        onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
      >
        <span className="avatar">
          {user.avatar ? <img src={user.avatar} alt="" /> : initial}
        </span>
        <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)' }}>
          {user.username}
        </span>
      </button>

      {open && (
        <div
          className="fade-up"
          style={{
            position: 'absolute',
            right: 0,
            top: 44,
            width: 220,
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            boxShadow: 'var(--shadow-lg)',
            padding: 6,
            zIndex: 100,
          }}
        >
          <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{user.nickname || user.username}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {user.username}
            </div>
          </div>
          <button
            onClick={onLogout}
            style={{
              width: '100%',
              textAlign: 'left',
              padding: '9px 12px',
              background: 'transparent',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: 14,
              color: 'var(--text-secondary)',
            }}
            onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = 'var(--surface-2)')}
            onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
          >
            退出登录
          </button>
        </div>
      )}
    </div>
  )
}
