import { useEffect, useState } from 'react'
import { getLogEvents, getApprovals, getStatus, getStatusStats } from '../api/client'

interface Stat {
  node: string
  avg_ms?: number
  max_ms?: number
  calls?: number
  errors?: number
}

export default function LogsPanel() {
  const [total, setTotal] = useState({ events: 0, errors: 0, sessions: 0 })
  const [slowNodes, setSlowNodes] = useState<Stat[]>([])
  const [errors, setErrors] = useState<Stat[]>([])
  const [events, setEvents] = useState<Record<string, unknown>[]>([])
  const [approvals, setApprovals] = useState<Record<string, unknown>[]>([])

  useEffect(() => {
    getStatus().then((r) => setTotal(r.stats))
    getStatusStats().then((r) => {
      setSlowNodes((r.slow_nodes as Stat[]) || [])
      setErrors((r.errors as Stat[]) || [])
    })
    getLogEvents({ limit: '30' }).then((r) => setEvents(r.events as Record<string, unknown>[]))
    getApprovals().then((r) => setApprovals(r.approvals as Record<string, unknown>[]))
  }, [])

  return (
    <div style={{ maxWidth: 860 }}>
      <h2 style={{ marginBottom: 20 }}>日志</h2>

      {/* 概览 */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <MetricCard label="事件总数" value={total.events} />
        <MetricCard label="错误事件" value={total.errors} tone="danger" />
        <MetricCard label="会话数" value={total.sessions} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        {/* 慢节点 */}
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 15, marginBottom: 12 }}>慢节点</h3>
          {slowNodes.length === 0 && <Muted text="暂无耗时数据" />}
          {slowNodes.map((s) => (
            <div
              key={s.node}
              style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 14 }}
            >
              <span>{s.node}</span>
              <span className="tabular" style={{ color: 'var(--text-secondary)' }}>
                {s.max_ms != null ? `${s.max_ms}ms 峰值` : ''}
                {s.calls != null ? ` · ${s.calls} 次` : ''}
              </span>
            </div>
          ))}
        </div>

        {/* 错误分类 */}
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 15, marginBottom: 12 }}>错误分类</h3>
          {errors.length === 0 && <Muted text="暂无错误" />}
          {errors.map((e) => (
            <div
              key={e.node}
              style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 14 }}
            >
              <span>{e.node}</span>
              <span className="badge badge-err tabular">{e.errors} 次</span>
            </div>
          ))}
        </div>
      </div>

      {/* 事件流 */}
      <div className="card" style={{ padding: 20, marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>最近事件</h3>
        <div style={{ maxHeight: 320, overflow: 'auto' }}>
          {events.map((ev, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '8px 0',
                borderBottom: '1px solid var(--border)',
                fontSize: 13,
              }}
            >
              <span
                className="badge"
                style={{
                  background: ev.status === 'error' ? 'var(--danger-soft)' : 'var(--success-soft)',
                  color: ev.status === 'error' ? 'var(--danger)' : 'var(--success)',
                }}
              >
                {String(ev.event)}
              </span>
              <span className="tabular" style={{ color: 'var(--text-muted)', width: 140, flexShrink: 0 }}>
                {new Date(String(ev.ts)).toLocaleTimeString()}
              </span>
              <span style={{ fontWeight: 500 }}>{String(ev.node)}</span>
              {ev.duration_ms != null && (
                <span className="tabular" style={{ color: 'var(--text-muted)' }}>
                  {String(ev.duration_ms)}ms
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 审批 */}
      <div className="card" style={{ padding: 20 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>审批记录</h3>
        {approvals.length === 0 && <Muted text="暂无审批" />}
        {approvals.map((a, i) => (
          <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
            <span className="tabular" style={{ color: 'var(--text-muted)' }}>
              {new Date(String(a.ts)).toLocaleString()}
            </span>{' '}
            · {String(a.node)}
          </div>
        ))}
      </div>
    </div>
  )
}

function MetricCard({ label, value, tone }: { label: string; value: number; tone?: 'danger' }) {
  return (
    <div className="card" style={{ flex: 1, padding: 20 }}>
      <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{label}</div>
      <div
        className="tabular"
        style={{ fontSize: 28, fontWeight: 700, marginTop: 6, color: tone === 'danger' ? 'var(--danger)' : 'var(--text)' }}
      >
        {value}
      </div>
    </div>
  )
}

function Muted({ text }: { text: string }) {
  return <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>{text}</div>
}
