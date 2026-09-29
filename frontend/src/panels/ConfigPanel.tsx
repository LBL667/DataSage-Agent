import { useEffect, useState } from 'react'
import {
  getWhitelist,
  getBlacklist,
  getCleanRules,
  getThresholds,
  getDbStatus,
} from '../api/client'

export default function ConfigPanel() {
  const [whitelist, setWhitelist] = useState<string[]>([])
  const [blacklist, setBlacklist] = useState<{ columns: string[]; statements: string[] }>({ columns: [], statements: [] })
  const [rules, setRules] = useState<Record<string, unknown>[]>([])
  const [thresholds, setThresholds] = useState<Record<string, unknown>>({})
  const [db, setDb] = useState<Record<string, unknown>>({})

  useEffect(() => {
    getWhitelist().then((r) => setWhitelist(r.tables || []))
    getBlacklist().then((r) => setBlacklist({ columns: r.columns || [], statements: r.statements || [] }))
    getCleanRules().then((r) => setRules(r.rules || []))
    getThresholds().then((r) => setThresholds(r as unknown as Record<string, unknown>))
    getDbStatus().then(setDb)
  }, [])

  return (
    <div style={{ maxWidth: 720 }}>
      <h2 style={{ marginBottom: 20 }}>配置</h2>

      <Section title="数据库">
        <KV k="主机" v={String(db.host || '—')} />
        <KV k="数据库" v={String(db.database || '—')} />
        <KV k="账号" v={String(db.user || '—')} />
      </Section>

      <Section title="白名单表">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {whitelist.map((t) => (
            <span key={t} className="badge badge-muted tabular">
              {t}
            </span>
          ))}
        </div>
      </Section>

      <Section title="敏感字段黑名单">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {blacklist.columns.map((c) => (
            <span key={c} className="badge badge-warn tabular">
              {c}
            </span>
          ))}
          {blacklist.columns.length === 0 && <Muted text="无" />}
        </div>
      </Section>

      <Section title="清洗规则">
        {rules.length === 0 && <Muted text="无" />}
        {rules.map((r) => (
          <div
            key={String(r.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '10px 0',
              borderBottom: '1px solid var(--border)',
              fontSize: 14,
            }}
          >
            <span className="badge badge-muted tabular">{String(r.id)}</span>
            <span style={{ fontWeight: 500 }}>{String(r.action)}</span>
            <span style={{ color: 'var(--text-muted)' }}>{JSON.stringify(r.target || r.key)}</span>
          </div>
        ))}
      </Section>

      <Section title="阈值">
        {Object.entries(thresholds).map(([k, v]) => (
          <KV key={k} k={k} v={String(v)} />
        ))}
      </Section>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ padding: 20, marginBottom: 16 }}>
      <h3 style={{ fontSize: 15, marginBottom: 12 }}>{title}</h3>
      {children}
    </div>
  )
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 14 }}>
      <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
      <span className="tabular">{v}</span>
    </div>
  )
}

function Muted({ text }: { text: string }) {
  return <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>{text}</span>
}
