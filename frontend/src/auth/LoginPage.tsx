import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../api/client'

export default function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!username || !password) {
      setError('请输入用户名和密码')
      return
    }
    setLoading(true)
    setError('')
    const res = await login(username, password)
    setLoading(false)
    if (!res.ok || !res.user) {
      setError(res.message || '登录失败')
      return
    }
    localStorage.setItem('datasage_user', JSON.stringify(res.user))
    navigate('/')
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
          <div
            style={{
              fontSize: 30,
              fontWeight: 700,
              letterSpacing: '-0.02em',
              color: 'var(--text)',
            }}
          >
            DataSage
          </div>
          <div style={{ marginTop: 8, color: 'var(--text-muted)', fontSize: 15 }}>
            用自然语言问数据，一句话拿到分析
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
            autoComplete="username"
            placeholder="admin"
          />

          <div style={{ height: 20 }} />

          <label className="label" htmlFor="password">
            密码
          </label>
          <input
            id="password"
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            placeholder="••••••••"
          />

          {error && (
            <div style={{ marginTop: 16, color: 'var(--danger)', fontSize: 13 }}>{error}</div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', marginTop: 24, height: 44 }}
          >
            {loading ? '登录中…' : '登录'}
          </button>
        </form>

        <div style={{ marginTop: 24, textAlign: 'center', fontSize: 14 }}>
          <Link to="/forgot" style={{ color: 'var(--text-muted)' }}>
            忘记密码？
          </Link>
        </div>
      </div>
    </div>
  )
}
