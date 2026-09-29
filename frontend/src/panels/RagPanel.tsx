import { useEffect, useState } from 'react'
import { getRagDocuments, ragSearch } from '../api/client'

export default function RagPanel() {
  const [documents, setDocuments] = useState<Record<string, unknown>[]>([])
  const [query, setQuery] = useState('')
  const [collection, setCollection] = useState('schema')
  const [chunks, setChunks] = useState<Record<string, unknown>[]>([])
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    getRagDocuments().then((r) => setDocuments((r.documents as Record<string, unknown>[]) || []))
  }, [])

  async function onSearch() {
    if (!query.trim()) return
    setSearching(true)
    const r = await ragSearch(query, collection)
    setChunks((r.chunks as Record<string, unknown>[]) || [])
    setSearching(false)
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <h2 style={{ marginBottom: 20 }}>知识库</h2>

      <div className="card" style={{ padding: 20, marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>检索测试</h3>
        <div style={{ display: 'flex', gap: 10 }}>
          <select
            className="input"
            value={collection}
            onChange={(e) => setCollection(e.target.value)}
            style={{ width: 140, flexShrink: 0 }}
          >
            <option value="schema">schema</option>
            <option value="metric">metric</option>
            <option value="method">method</option>
          </select>
          <input
            className="input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onSearch()}
            placeholder="输入检索词，如「各渠道订单」"
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" onClick={onSearch} disabled={searching || !query.trim()}>
            检索
          </button>
        </div>

        {chunks.length > 0 && (
          <div style={{ marginTop: 16 }}>
            {chunks.map((c, i) => (
              <div
                key={i}
                className="card"
                style={{ padding: 14, marginBottom: 10, fontSize: 14 }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600 }}>
                    {String((c.metadata as Record<string, unknown> | undefined)?.table || '')}
                  </span>
                  <span className="tabular" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                    score {(c.score as number)?.toFixed(4)}
                  </span>
                </div>
                <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: 12, whiteSpace: 'pre-wrap' }}>
                  {String(c.content)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card" style={{ padding: 20 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>文档</h3>
        {documents.length === 0 && (
          <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>暂无文档</div>
        )}
        {documents.map((d) => (
          <div
            key={String(d.doc_id || d.id)}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '10px 0',
              borderBottom: '1px solid var(--border)',
              fontSize: 14,
            }}
          >
            <span>{String(d.name || d.doc_id || d.id)}</span>
            <span style={{ color: 'var(--text-muted)' }}>{String(d.collection || '')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
