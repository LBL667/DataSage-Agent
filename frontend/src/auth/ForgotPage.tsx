import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { resetPassword } from '../api/client'

export default function ForgotPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!username || !newPassword) {
      setError('请填写用户名和新密码')
      return
    }
    setLoading(true)
    setError('')
    setMessage('')
    const res = await resetPassword(username, newPassword)
    setLoading(false)
    if (!res.ok) {
      setError(res.message || '重置失败')
      return
    }
    setMessage('密码已重置，请返回登录')
    setTimeout(() => navigate('/login'), 1200)
  }

  return (
    <div
      style={{
        minHeight: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        padding: 24,
      }}
    >
      <div style={{ width: 360 }}>
        <div style={{ marginBottom: 40 }}>
          <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em' }}>重置密码</div>
          <div style={{ marginTop: 8, color: 'var(--text-muted)', fontSize: 15 }}>
            输入用户名和新密码即可完成重置
          </div>
        </div>

        <form onSubmit={onSubmit} className="fade-up">
          <label className="label" htmlFor="username">
            用户名
          </label>
          <input
            id="username"
            className="input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="admin"
          />

          <div style={{ height: 20 }} />

          <label className="label" htmlFor="new-password">
            新密码
          </label>
          <input
            id="new-password"
            className="input"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="新密码"
          />

          {error && (
            <div style={{ marginTop: 16, color: 'var(--danger)', fontSize: 13 }}>{error}</div>
          )}
          {message && (
            <div style={{ marginTop: 16, color: 'var(--success)', fontSize: 13 }}>{message}</div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', marginTop: 24, height: 44 }}
          >
            {loading ? '提交中…' : '重置密码'}
          </button>
        </form>

        <div style={{ marginTop: 24, textAlign: 'center', fontSize: 14 }}>
          <Link to="/login" style={{ color: 'var(--text-muted)' }}>
            返回登录
          </Link>
        </div>
      </div>
    </div>
  )
}
