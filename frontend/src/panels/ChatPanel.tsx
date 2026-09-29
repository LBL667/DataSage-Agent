import { useState, useRef, useEffect } from 'react'
import { startChat, resumeChat, type SSEEvent } from '../api/client'
import { loadCurrent, saveCurrent, type ChatMsg } from '../store/session'

interface Approval {
  node: string
  target: Record<string, unknown>
}

const NODE_LABEL: Record<string, string> = {
  intent_router: '识别意图',
  clarify: '澄清追问',
  rag_retrieve: '检索上下文',
  sql_generate: '生成 SQL',
  risk_assess: '风险评估',
  sql_review: '安全审查',
  readonly_exec: '执行查询',
  quality_check: '质量检查',
  data_clean: '数据清洗',
  analyze: '分析结果',
  self_check: '结果自检',
  chart_advise: '生成图表',
  chart_validate: '校验图表',
  respond: '生成洞察',
}

const CHART_TYPE_LABEL: Record<string, string> = {
  line: '折线图',
  bar: '柱状图',
  scatter: '散点图',
  pie: '饼图',
  table: '表格',
}

export default function ChatPanel() {
  const [session, setSession] = useState(() => loadCurrent())
  const [input, setInput] = useState('')
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState('')
  const [approval, setApproval] = useState<Approval | null>(null)
  const [editComment, setEditComment] = useState('')
  const [clarifyAnswer, setClarifyAnswer] = useState('')
  const threadRef = useRef('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [session.messages, progress])

  function update(messages: ChatMsg[]) {
    setSession((prev) => {
      const next = { ...prev, messages }
      saveCurrent(next)
      return next
    })
  }

  function handleEvent(ev: SSEEvent) {
    if (ev.session_id) threadRef.current = ev.session_id
    if (ev.event === 'node_start') {
      setProgress(ev.node)
    } else if (ev.event === 'node_end') {
      setProgress('')
    } else if (ev.event === 'approval_request') {
      setApproval({ node: ev.node, target: ev.target || {} })
      setRunning(false)
    } else if (ev.event === 'final') {
      const text = (ev.target as { text?: string } | undefined)?.text || ''
      setSession((prev) => {
        const next = { ...prev, messages: [...prev.messages, { role: 'assistant' as const, content: text }] }
        saveCurrent(next)
        return next
      })
      setRunning(false)
      setProgress('')
    } else if (ev.event === 'error') {
      setRunning(false)
      setProgress('')
    }
  }

  async function send() {
    const text = input.trim()
    if (!text || running) return
    setInput('')
    const userMsg = { role: 'user' as const, content: text }
    setSession((prev) => {
      const next = { ...prev, messages: [...prev.messages, userMsg] }
      saveCurrent(next)
      return next
    })
    // 首次发送用输入作为标题
    if (session.title === '新会话' && session.messages.length === 0) {
      const title = text.slice(0, 16)
      setSession((prev) => {
        const next = { ...prev, title }
        saveCurrent(next)
        return next
      })
    }
    setRunning(true)
    await startChat(text, handleEvent)
  }

  async function onApproval(decision: string, comment?: string) {
    if (!approval) return
    setApproval(null)
    setRunning(true)
    if (approval.node === 'clarify') {
      await resumeChat(threadRef.current, 'approve', clarifyAnswer)
      setClarifyAnswer('')
    } else {
      await resumeChat(threadRef.current, decision, comment)
      setEditComment('')
    }
  }

  function compactMemory() {
    const msgs = session.messages
    if (msgs.length <= 6) return
    const kept = msgs.slice(-4)
    const removed = msgs.length - kept.length
    update([{ role: 'assistant', content: `（已压缩更早的 ${removed} 条消息，保留最近上下文）` }, ...kept])
  }

  const approvalTarget = approval?.target as {
    sql?: string
    explain?: string
    reasons?: string[]
    questions?: string[]
    chart_spec?: { chart_type?: string; description?: string; title?: string }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', maxWidth: 820, margin: '0 auto' }}>
      <div style={{ flex: 1, overflow: 'auto', paddingBottom: 16 }}>
        {session.messages.length > 6 && (
          <div style={{ textAlign: 'right', marginBottom: 8 }}>
            <button className="btn btn-ghost" style={{ height: 28, padding: '0 10px', fontSize: 12 }} onClick={compactMemory}>
              压缩记忆
            </button>
          </div>
        )}
        {session.messages.length === 0 && !running && (
          <div style={{ textAlign: 'center', paddingTop: 80, color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)' }}>想问什么数据？</div>
            <div style={{ marginTop: 8, fontSize: 14 }}>例如「查一下各渠道的订单金额总和」</div>
          </div>
        )}

        {session.messages.map((m, i) => (
          <div
            key={i}
            className="fade-up"
            style={{
              marginBottom: 16,
              display: 'flex',
              justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div
              style={{
                maxWidth: '78%',
                padding: '12px 16px',
                borderRadius: 'var(--radius)',
                background: m.role === 'user' ? 'var(--accent)' : 'var(--surface)',
                color: m.role === 'user' ? '#fff' : 'var(--text)',
                border: m.role === 'user' ? 'none' : '1px solid var(--border)',
                fontSize: 14,
                lineHeight: 1.6,
              }}
            >
              {m.content}
            </div>
          </div>
        ))}

        {running && (
          <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '8px 4px' }}>
            <span className="pulse" style={{ display: 'inline-block', marginRight: 8 }}>●</span>
            {progress ? `正在${NODE_LABEL[progress] || progress}…` : '处理中…'}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div style={{ display: 'flex', gap: 10, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="输入你的数据问题…"
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" onClick={send} disabled={running || !input.trim()}>
          发送
        </button>
      </div>

      {approval && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'oklch(24% 0.015 255 / 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 200,
            padding: 24,
          }}
        >
          <div
            className="fade-up"
            style={{
              width: 520,
              maxHeight: '80vh',
              overflow: 'auto',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-lg)',
              padding: 24,
            }}
          >
            {approval.node === 'human_sql_approve' && (
              <>
                <h3 style={{ marginBottom: 4 }}>SQL 审批</h3>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
                  以下 SQL 需要你确认后才会执行
                </p>
                {approvalTarget?.explain && <p style={{ fontSize: 14, marginBottom: 12 }}>{approvalTarget.explain}</p>}
                <div className="code">{approvalTarget?.sql}</div>
                {approvalTarget?.reasons && approvalTarget.reasons.length > 0 && (
                  <div style={{ marginTop: 12, fontSize: 13, color: 'var(--warning)' }}>
                    {approvalTarget.reasons.join('；')}
                  </div>
                )}
                <input
                  className="input"
                  style={{ marginTop: 16 }}
                  value={editComment}
                  onChange={(e) => setEditComment(e.target.value)}
                  placeholder="修改意见（选填）"
                />
                <div style={{ display: 'flex', gap: 10, marginTop: 16, justifyContent: 'flex-end' }}>
                  <button className="btn btn-ghost" onClick={() => onApproval('cancel')}>取消</button>
                  <button className="btn btn-danger" onClick={() => onApproval('edit', editComment)}>修改</button>
                  <button className="btn btn-primary" onClick={() => onApproval('approve')}>同意执行</button>
                </div>
              </>
            )}

            {approval.node === 'human_chart_approve' && (
              <>
                <h3 style={{ marginBottom: 4 }}>图表确认</h3>
                <p style={{ fontSize: 14, marginBottom: 16, color: 'var(--text)' }}>
                  {approvalTarget?.chart_spec?.description || '建议用图表展示分析结果'}
                </p>
                {approvalTarget?.chart_spec?.chart_type && (
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
                    图表类型：{CHART_TYPE_LABEL[approvalTarget.chart_spec.chart_type] || approvalTarget.chart_spec.chart_type}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 10, marginTop: 8, justifyContent: 'flex-end' }}>
                  <button className="btn btn-ghost" onClick={() => onApproval('reject')}>只看文字</button>
                  <button className="btn btn-primary" onClick={() => onApproval('approve')}>确认图表</button>
                </div>
              </>
            )}

            {approval.node === 'clarify' && (
              <>
                <h3 style={{ marginBottom: 4 }}>需要补充</h3>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>为了准确回答，请补充以下信息</p>
                {(approvalTarget?.questions || []).map((q, i) => (
                  <p key={i} style={{ fontSize: 14, marginBottom: 8 }}>· {q}</p>
                ))}
                <input
                  className="input"
                  style={{ marginTop: 8 }}
                  value={clarifyAnswer}
                  onChange={(e) => setClarifyAnswer(e.target.value)}
                  placeholder="补充说明…"
                />
                <div style={{ display: 'flex', gap: 10, marginTop: 16, justifyContent: 'flex-end' }}>
                  <button className="btn btn-primary" onClick={() => onApproval('approve')}>提交</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
