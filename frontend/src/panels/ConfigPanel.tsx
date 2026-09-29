import { useEffect, useState } from 'react'
import {
  getWhitelist,
  getBlacklist,
  getCleanRules,
  getDbStatus,
  putDb,
  putWhitelist,
  putBlacklist,
  putCleanRules,
} from '../api/client'

export default function ConfigPanel() {
  const [db, setDb] = useState({ host: '', port: 3306, user: '', password: '', database: '' })
  const [whitelist, setWhitelist] = useState<string[]>([])
  const [blacklist, setBlacklist] = useState<{ columns: string[]; statements: string[] }>({ columns: [], statements: [] })
  const [rules, setRules] = useState<Record<string, unknown>[]>([])
  const [newTable, setNewTable] = useState('')
  const [newColumn, setNewColumn] = useState('')
  const [newStatement, setNewStatement] = useState('')
  const [saved, setSaved] = useState('')

  useEffect(() => {
    getDbStatus().then((d) => setDb({ host: String(d.host || ''), port: Number(d.port || 3306), user: String(d.user || ''), password: '', database: String(d.database || '') }))
    getWhitelist().then((r) => setWhitelist(r.tables || []))
    getBlacklist().then((r) => setBlacklist({ columns: r.columns || [], statements: r.statements || [] }))
    getCleanRules().then((r) => setRules(r.rules || []))
  }, [])

  function flash(msg: string) {
    setSaved(msg)
    setTimeout(() => setSaved(''), 2000)
  }

  async function saveDb() {
    await putDb(db)
    flash('数据库配置已保存，已同步 .env')
  }

  async function saveWhitelist(tables: string[]) {
    setWhitelist(tables)
    await putWhitelist(tables)
  }

  async function saveBlacklist(data: { columns: string[]; statements: string[] }) {
    setBlacklist(data)
    await putBlacklist(data)
  }

  async function saveRules(rules: Record<string, unknown>[]) {
    setRules(rules)
    await putCleanRules(rules)
  }

  function addRule() {
    const id = `R${rules.length + 1}`
    saveRules([...rules, { id, action: 'drop_duplicate', target: ['*'], enabled: true }])
  }

  function toggleRule(i: number) {
    const next = rules.map((r, j) => (j === i ? { ...r, enabled: !r.enabled } : r))
    saveRules(next)
  }

  function removeRule(i: number) {
    saveRules(rules.filter((_, j) => j !== i))
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2>配置</h2>
        {saved && <span className="badge badge-ok">{saved}</span>}
      </div>

      {/* 数据库账号密码 */}
      <div className="card" style={{ padding: 20, marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>MySQL 数据库</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Field label="主机">
            <input className="input" value={db.host} onChange={(e) => setDb({ ...db, host: e.target.value })} />
          </Field>
          <Field label="端口">
            <input className="input" value={db.port} onChange={(e) => setDb({ ...db, port: Number(e.target.value) })} />
          </Field>
          <Field label="账号">
            <input className="input" value={db.user} onChange={(e) => setDb({ ...db, user: e.target.value })} />
          </Field>
          <Field label="密码">
            <input className="input" type="password" value={db.password} placeholder="留空则不修改" onChange={(e) => setDb({ ...db, password: e.target.value })} />
          </Field>
          <Field label="数据库名">
            <input className="input" value={db.database} onChange={(e) => setDb({ ...db, database: e.target.value })} />
          </Field>
        </div>
        <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={saveDb}>
          保存数据库配置
        </button>
      </div>

      {/* 白名单 */}
      <div className="card" style={{ padding: 20, marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>白名单表</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {whitelist.map((t) => (
            <span key={t} className="badge badge-muted tabular" style={{ gap: 6 }}>
              {t}
              <button
                onClick={() => saveWhitelist(whitelist.filter((x) => x !== t))}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: 13, padding: 0, lineHeight: 1 }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <input className="input" value={newTable} onChange={(e) => setNewTable(e.target.value)} placeholder="输入表名" style={{ flex: 1 }} />
          <button
            className="btn btn-ghost"
            onClick={() => {
              if (newTable.trim() && !whitelist.includes(newTable.trim())) {
                saveWhitelist([...whitelist, newTable.trim()])
                setNewTable('')
              }
            }}
          >
            添加
          </button>
        </div>
      </div>

      {/* 黑名单 */}
      <div className="card" style={{ padding: 20, marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>敏感字段黑名单</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {blacklist.columns.map((c) => (
            <span key={c} className="badge" style={{ background: 'var(--danger-soft)', color: 'var(--danger)', gap: 6 }}>
              {c}
              <button
                onClick={() => saveBlacklist({ ...blacklist, columns: blacklist.columns.filter((x) => x !== c) })}
                style={{ background: 'transparent', border: 'none', color: 'var(--danger)', fontSize: 13, padding: 0, lineHeight: 1 }}
              >
                ×
              </button>
            </span>
          ))}
          {blacklist.columns.length === 0 && <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>无</span>}
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <input className="input" value={newColumn} onChange={(e) => setNewColumn(e.target.value)} placeholder="输入敏感字段，如 phone" style={{ flex: 1 }} />
          <button
            className="btn btn-ghost"
            onClick={() => {
              if (newColumn.trim() && !blacklist.columns.includes(newColumn.trim())) {
                saveBlacklist({ ...blacklist, columns: [...blacklist.columns, newColumn.trim()] })
                setNewColumn('')
              }
            }}
          >
            添加
          </button>
        </div>

        <h4 style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '20px 0 12px' }}>审查隔离语句</h4>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {blacklist.statements.map((s) => (
            <span key={s} className="badge" style={{ background: 'var(--danger-soft)', color: 'var(--danger)', gap: 6, fontFamily: 'var(--font-mono)' }}>
              {s}
              <button
                onClick={() => saveBlacklist({ ...blacklist, statements: blacklist.statements.filter((x) => x !== s) })}
                style={{ background: 'transparent', border: 'none', color: 'var(--danger)', fontSize: 13, padding: 0, lineHeight: 1 }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <input className="input" value={newStatement} onChange={(e) => setNewStatement(e.target.value)} placeholder="输入 SQL 语句，如 INTO OUTFILE" style={{ flex: 1 }} />
          <button
            className="btn btn-ghost"
            onClick={() => {
              if (newStatement.trim() && !blacklist.statements.includes(newStatement.trim())) {
                saveBlacklist({ ...blacklist, statements: [...blacklist.statements, newStatement.trim()] })
                setNewStatement('')
              }
            }}
          >
            添加
          </button>
        </div>
      </div>

      {/* 清洗规则 */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ fontSize: 15 }}>清洗规则</h3>
          <button className="btn btn-ghost" onClick={addRule}>添加规则</button>
        </div>
        {rules.map((r, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--border)', fontSize: 14 }}>
            <span className="badge badge-muted tabular">{String(r.id)}</span>
            <input
              className="input"
              style={{ width: 160, height: 32 }}
              value={String(r.action)}
              onChange={(e) => saveRules(rules.map((x, j) => (j === i ? { ...x, action: e.target.value } : x)))}
            />
            <input
              className="input"
              style={{ flex: 1, height: 32 }}
              value={JSON.stringify(r.target || '')}
              onChange={(e) => {
                try {
                  const target = JSON.parse(e.target.value)
                  saveRules(rules.map((x, j) => (j === i ? { ...x, target } : x)))
                } catch {
                  /* 输入中 */
                }
              }}
            />
            <button
              className="btn btn-ghost"
              style={{ height: 32, padding: '0 10px' }}
              onClick={() => toggleRule(i)}
            >
              {r.enabled ? '停用' : '启用'}
            </button>
            <button className="btn btn-ghost" style={{ height: 32, padding: '0 10px' }} onClick={() => removeRule(i)}>
              删除
            </button>
          </div>
        ))}
        {rules.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>无规则</div>}
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
    </div>
  )
}
