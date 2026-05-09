// API types matching FastAPI backend

export interface ChapterSummary {
  chapter_id: string
  chapter_number: number
  title: string
  state: string
  version: number
}

export interface ProjectDetail {
  project_id: string
  title: string
  genre: string
  style: string
  chapters_json: ChapterSummary[]
}

export interface EventRecord {
  id: number
  project_id: string
  correlation_id: string | null
  event_type: string
  actor_type: string | null
  causation_id: string | null
  payload: Record<string, unknown>
  created_at: string
}
  id: number
  project_id: string
  correlation_id: string | null
  event_type: string
  agent_id: string | null
  payload: Record<string, unknown>
  created_at: string
}

export interface CreateChapterPayload {
  chapter_id: string
  chapter_number: number
  title?: string
}

export interface PatchChapterPayload {
  state: string
  version?: number
}
