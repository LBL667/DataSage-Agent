import { useEffect, useRef, useState } from 'react'
import { getRagDocuments, ragSearch, uploadDocument } from '../api/client'

const COLLECTIONS = [
  { key: 'metric', label: '业务文档' },
  { key: 'method', label: '分析方法' },
]

export default function RagPanel() {
  const [documents, setDocuments] = useState<Record<string, unknown>[]>([])
  const [query, setQuery] = useState('')
  const [collection, setCollection] = useState('schema')
  const [chunks, setChunks] = useState<Record<string, unknown>[]>([])
  const [searching, setSearching] = useState(false)
  const [uploading, setUploading] = useState('')
  const [message, setMessage] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const [targetCollection, setTargetCollection] = useState('metric')

  function refresh() {
    getRagDocuments().then((r) => setDocuments((r.documents as Record<string, unknown>[]) || []))
  }

  useEffect(() => {
    refresh()
  }, [])

  async function onPickFile() {
    const file = fileRef.current?.files?.[0]
    if (!file) return
    setUploading(file.name)
    setMessage('')
    await uploadDocument(file, targetCollection)
    setUploading('')
    setMessage(`已上传 ${file.name}`)
    setTimeout(() => setMessage(''), 2000)
    refresh()
    if (fileRef.current) fileRef.current.value = ''
  }

  async function onSearch() {
    if (!query.trim()) return
    setSearching(true)
    const r = await ragSearch(query, collection)
    setChunks((r.chunks as Record<string, unknown>[]) || [])
    setSearching(false)
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2>知识库</h2>
        {message && <span className="badge badge-ok">{message}</span>}
      </div>

      {/* 上传 */}
      <div className="card" style={{ padding: 20, marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>上传文档</h3>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select className="input" value={targetCollection} onChange={(e) => setTargetCollection(e.target.value)} style={{ width: 150, flexShrink: 0 }}>
            {COLLECTIONS.map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>
          <input type="file" ref={fileRef} style={{ display: 'none' }} onChange={onPickFile} accept=".md,.txt,.json,.csv" />
          <button className="btn btn-primary" onClick={() => fileRef.current?.click()} disabled={!!uploading}>
            {uploading ? `上传中 ${uploading}…` : '选择文件上传'}
          </button>
        </div>
        <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-muted)' }}>
          业务文档上传到指标口径库，分析方法上传到方法库
        </div>
      </div>

      {/* 检索测试 */}
      <div className="card" style={{ padding: 20, marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>检索测试</h3>
        <div style={{ display: 'flex', gap: 10 }}>
          <select className="input" value={collection} onChange={(e) => setCollection(e.target.value)} style={{ width: 140, flexShrink: 0 }}>
            <option value="schema">schema</option>
            <option value="metric">metric</option>
            <option value="method">method</option>
          </select>
          <input className="input" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && onSearch()} placeholder="输入检索词" style={{ flex: 1 }} />
          <button className="btn btn-primary" onClick={onSearch} disabled={searching || !query.trim()}>检索</button>
        </div>
        {chunks.length > 0 && (
          <div style={{ marginTop: 16 }}>
            {chunks.map((c, i) => (
              <div key={i} className="card" style={{ padding: 14, marginBottom: 10, fontSize: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600 }}>{String((c.metadata as Record<string, unknown> | undefined)?.table || '')}</span>
                  <span className="tabular" style={{ color: 'var(--text-muted)', fontSize: 12 }}>score {(c.score as number)?.toFixed(4)}</span>
                </div>
                <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: 12, whiteSpace: 'pre-wrap' }}>{String(c.content)}</pre>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 文档列表 */}
      <div className="card" style={{ padding: 20 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>已上传文档</h3>
        {documents.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>暂无文档</div>}
        {documents.map((d) => (
          <div key={`${d.collection}-${d.name}`} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)', fontSize: 14 }}>
            <span>{String(d.name)}</span>
            <span style={{ color: 'var(--text-muted)' }}>
              {COLLECTIONS.find((c) => c.key === d.collection)?.label || String(d.collection)} · {String(d.chunks)} 块
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
