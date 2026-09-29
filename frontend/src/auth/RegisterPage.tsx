import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../api/client'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!username || !password) {
      setError('请填写用户名和密码')
      return
    }
    if (password !== confirm) {
      setError('两次输入的密码不一致')
      return
    }
    setLoading(true)
    setError('')
    const res = await register(username, password, nickname)
    setLoading(false)
    if (!res.ok || !res.user) {
      setError(res.message || '注册失败')
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
          <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em' }}>注册账号</div>
          <div style={{ marginTop: 8, color: 'var(--text-muted)', fontSize: 15 }}>创建一个 DataSage 账号</div>
        </div>

        <form onSubmit={onSubmit} className="fade-up">
          <label className="label">用户名</label>
          <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="用户名" />

          <div style={{ height: 20 }} />
          <label className="label">昵称（选填）</label>
          <input className="input" value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="昵称" />

          <div style={{ height: 20 }} />
          <label className="label">密码</label>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="密码" />

          <div style={{ height: 20 }} />
          <label className="label">确认密码</label>
          <input className="input" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="再次输入密码" />

          {error && <div style={{ marginTop: 16, color: 'var(--danger)', fontSize: 13 }}>{error}</div>}

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', marginTop: 24, height: 44 }}>
            {loading ? '注册中…' : '注册'}
          </button>
        </form>

        <div style={{ marginTop: 24, textAlign: 'center', fontSize: 14 }}>
          <Link to="/login" style={{ color: 'var(--text-muted)' }}>已有账号，返回登录</Link>
        </div>
      </div>
    </div>
  )
}
