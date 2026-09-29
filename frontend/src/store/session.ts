export interface ChatMsg {
  role: 'user' | 'assistant'
  content: string
}

export interface Session {
  id: string
  title: string
  messages: ChatMsg[]
  updatedAt: number
}

const SESSIONS_KEY = 'datasage_sessions'
const CURRENT_KEY = 'datasage_current'

function read(): Session[] {
  try {
    return JSON.parse(localStorage.getItem(SESSIONS_KEY) || '[]') as Session[]
  } catch {
    return []
  }
}

function write(sessions: Session[]) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
}

export function loadSessions(): Session[] {
  return read().sort((a, b) => b.updatedAt - a.updatedAt)
}

export function loadCurrent(): Session {
  const id = localStorage.getItem(CURRENT_KEY)
  const sessions = read()
  if (id) {
    const hit = sessions.find((s) => s.id === id)
    if (hit) return hit
  }
  return newSession()
}

export function newSession(): Session {
  const session: Session = {
    id: `ss_${Date.now().toString(36)}`,
    title: '新会话',
    messages: [],
    updatedAt: Date.now(),
  }
  const sessions = read()
  sessions.unshift(session)
  write(sessions)
  localStorage.setItem(CURRENT_KEY, session.id)
  return session
}

export function saveCurrent(session: Session) {
  session.updatedAt = Date.now()
  const sessions = read()
  const idx = sessions.findIndex((s) => s.id === session.id)
  if (idx >= 0) sessions[idx] = session
  else sessions.unshift(session)
  write(sessions)
  localStorage.setItem(CURRENT_KEY, session.id)
}

export function switchSession(id: string): Session | null {
  const hit = read().find((s) => s.id === id)
  if (!hit) return null
  localStorage.setItem(CURRENT_KEY, id)
  return hit
}

export function deleteSession(id: string) {
  const sessions = read().filter((s) => s.id !== id)
  write(sessions)
  if (localStorage.getItem(CURRENT_KEY) === id) {
    localStorage.setItem(CURRENT_KEY, sessions[0]?.id || '')
  }
}

export function clearSessions() {
  write([])
  localStorage.removeItem(CURRENT_KEY)
}
