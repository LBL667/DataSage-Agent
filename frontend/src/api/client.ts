export interface User {
  id: number
  username: string
  nickname: string
  avatar: string
  email: string
}

export interface SSEEvent {
  ts: string
  trace_id: string
  session_id: string
  node: string
  event: string
  tool?: string | null
  target?: Record<string, unknown> | null
  duration_ms?: number | null
  status?: string
}

const BASE = '/api'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return (await res.json()) as T
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  return (await res.json()) as T
}

export async function login(username: string, password: string): Promise<{ ok: boolean; user?: User; message?: string }> {
  return post('/auth/login', { username, password })
}

export async function resetPassword(username: string, newPassword: string): Promise<{ ok: boolean; message?: string }> {
  return post('/auth/reset-password', { username, new_password: newPassword })
}

export async function fetchMe(username: string): Promise<{ ok: boolean; user?: User; message?: string }> {
  return get(`/auth/me?username=${encodeURIComponent(username)}`)
}

export function startChat(
  message: string,
  onEvent: (ev: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  return fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
    signal,
  }).then(async (res) => {
    if (!res.body) return
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            onEvent(JSON.parse(line.slice(6)) as SSEEvent)
          } catch {
            /* ignore malformed */
          }
        }
      }
    }
  })
}

export function resumeChat(threadId: string, decision: string, comment?: string): Promise<void> {
  return fetch(`${BASE}/chat/${threadId}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, comment }),
  }).then(() => undefined)
}

export function getDashboardResults(): Promise<{ results: unknown[] }> {
  return get('/dashboard/results')
}

export function getDashboardData(ref: string): Promise<{ columns: string[]; rows: unknown[][]; total: number }> {
  return get(`/dashboard/data/${ref}`)
}

export function getLogEvents(params: Record<string, string> = {}): Promise<{ events: unknown[] }> {
  const qs = new URLSearchParams(params).toString()
  return get(`/logs/events${qs ? `?${qs}` : ''}`)
}

export function getApprovals(): Promise<{ approvals: unknown[] }> {
  return get('/logs/approvals')
}

export function getStatus(): Promise<{ stats: { events: number; errors: number; sessions: number }; graph_loaded: boolean }> {
  return get('/status')
}

export function getStatusStats(): Promise<{ slow_nodes: unknown[]; errors: unknown[] }> {
  return get('/status/stats')
}

export function getWhitelist(): Promise<{ tables: string[] }> {
  return get('/config/whitelist')
}

export function getBlacklist(): Promise<{ columns: string[]; column_patterns: string[]; statements: string[] }> {
  return get('/config/blacklist')
}

export function getCleanRules(): Promise<{ rules: Record<string, unknown>[] }> {
  return get('/config/clean-rules')
}

export function getThresholds(): Promise<{ max_scan_rows: number; sql_timeout_s: number; grant_ttl_s: number }> {
  return get('/config/thresholds')
}

export function getDbStatus(): Promise<Record<string, unknown>> {
  return get('/config/db')
}

export function getRagDocuments(): Promise<{ documents: Record<string, unknown>[] }> {
  return get('/rag/documents')
}

export function ragSearch(query: string, collection: string, topK = 10): Promise<{ chunks: Record<string, unknown>[] }> {
  return post('/rag/search', { query, collection, top_k: topK })
}
