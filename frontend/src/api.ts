export type StepState = 'IDLE' | 'RUNNING' | 'FAILED'
export type ProjectStatus =
  | 'CREATED'
  | 'STYLE_SET'
  | 'CHARACTERS_GENERATED'
  | 'PORTRAITS_GENERATED'
  | 'CHAPTERS_GENERATED'
  | 'DONE'

export interface Character {
  id: string
  name: string
  prompt: string
  portrait_path: string | null
}

export interface Chapter {
  id: string
  name: string
  prompt: string
  illustration_path: string | null
}

export interface Project {
  id: string
  title: string
  status: ProjectStatus
  step_state: StepState
  step_started_at: string | null
  art_style: string | null
  created_at: string
  is_stuck: boolean
  characters: Character[]
  chapters: Chapter[]
}

export interface ProjectSummary {
  id: string
  title: string
  status: ProjectStatus
  step_state: StepState
  created_at: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { credentials: 'include', ...init })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw Object.assign(new Error(body.detail ?? res.statusText), { status: res.status })
  }
  return res.json() as Promise<T>
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export function register(name: string, email: string) {
  return request<{ id: string; name: string; email: string }>('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email }),
  })
}

export function login(email: string) {
  return request<{ id: string; name: string; email: string }>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
}

export function logout() {
  return request<void>('/api/auth/logout', { method: 'POST' })
}

export function getMe() {
  return request<{ id: string; name: string; email: string }>('/api/auth/me')
}

// ── Projects ──────────────────────────────────────────────────────────────────

export function listProjects() {
  return request<ProjectSummary[]>('/api/projects')
}

export function getProject(id: string) {
  return request<Project>(`/api/projects/${id}`)
}

export function createProject(title: string, bookFile: File | null, bookText: string) {
  const fd = new FormData()
  fd.append('title', title)
  if (bookFile) {
    fd.append('book', bookFile)
  } else {
    fd.append('book', new Blob([bookText], { type: 'text/plain' }), 'book.txt')
  }
  return request<{ id: string; title: string; status: string }>('/api/projects', {
    method: 'POST',
    body: fd,
  })
}

// ── Pipeline steps ────────────────────────────────────────────────────────────

export function runStyle(id: string, artStyle: string) {
  return request<{ ok: boolean }>(`/api/projects/${id}/style`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ art_style: artStyle }),
  })
}

export function runCharacters(id: string) {
  return request<{ ok: boolean }>(`/api/projects/${id}/characters`, { method: 'POST' })
}

export function runPortraits(id: string) {
  return request<{ ok: boolean }>(`/api/projects/${id}/portraits`, { method: 'POST' })
}

export function runChapters(id: string) {
  return request<{ ok: boolean }>(`/api/projects/${id}/chapters`, { method: 'POST' })
}

export function runIllustrations(id: string) {
  return request<{ ok: boolean }>(`/api/projects/${id}/illustrations`, { method: 'POST' })
}

export function imageUrl(projectId: string, filename: string) {
  return `/api/projects/${projectId}/images/${filename}`
}
