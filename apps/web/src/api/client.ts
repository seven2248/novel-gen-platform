import type { ChapterSummary, EventRecord, ProjectDetail, CreateChapterPayload, PatchChapterPayload } from './types'

const BASE = ''

const DEFAULT_TIMEOUT_MS = 30000

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)
  try {
    const res = await fetch(`${BASE}${path}`, {
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...opts?.headers },
      ...opts
    })
    clearTimeout(timer)
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error((body as { detail?: string }).detail || `HTTP ${res.status}`)
    }
    return res.json() as Promise<T>
  } catch (err) {
    clearTimeout(timer)
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error(`请求超时（${DEFAULT_TIMEOUT_MS / 1000}秒）`)
    }
    throw err
  }
}

// Projects
export function getProject(projectId: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/projects/${projectId}`)
}

export function createProject(projectId: string, payload: { title?: string; genre?: string; style?: string }) {
  return request<ProjectDetail>(`/projects/${projectId}`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

// Chapters
export function getChapter(projectId: string, chapterId: string) {
  return request<ChapterSummary>(`/projects/${projectId}/chapters/${chapterId}`)
}

export function createChapter(projectId: string, payload: CreateChapterPayload) {
  return request<ChapterSummary>(`/projects/${projectId}/chapters`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function patchChapterState(projectId: string, chapterId: string, payload: PatchChapterPayload) {
  return request<ChapterSummary>(`/projects/${projectId}/chapters/${chapterId}/state`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })
}

// Events
export function getEvents(projectId: string, correlationId?: string) {
  const params = new URLSearchParams({ project_id: projectId })
  if (correlationId) params.set('correlation_id', correlationId)
  return request<EventRecord[]>(`/events?${params}`)
}

// Agent runs
interface MainFlowPayload {
  story_state: Record<string, unknown>
  chapter_goal: string
  chapter_id?: string
  chapter_num?: number
}

export function triggerMainFlow(payload: MainFlowPayload) {
  return request<{ result: string }>(`/agent-runs/main-flow`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}
