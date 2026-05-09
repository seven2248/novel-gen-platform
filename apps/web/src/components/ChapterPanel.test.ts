import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import ChapterPanel from '@/components/ChapterPanel.vue'
import * as api from '@/api/client'

// Mock the API client
vi.mock('@/api/client', () => ({
  getProject: vi.fn()
}))

const mockedGetProject = api.getProject as ReturnType<typeof vi.fn>

const mockChapters = [
  { chapter_id: 'ch1', chapter_number: 1, title: '第一章', state: 'draft', version: 1 },
  { chapter_id: 'ch2', chapter_number: 2, title: '第二章', state: 'review', version: 1 },
  { chapter_id: 'ch3', chapter_number: 3, title: '第三章', state: 'committed', version: 2 }
]

describe('ChapterPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty state when no chapters', async () => {
    mockedGetProject.mockResolvedValueOnce({ project_id: 'p1', title: 'Test', chapters_json: [] })
    const wrapper = mount(ChapterPanel, {
      props: { projectId: 'p1', selectedChapterId: null }
    })
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.el-empty').exists()).toBe(true)
  })

  it('renders chapter list', async () => {
    mockedGetProject.mockResolvedValueOnce({
      project_id: 'p1', title: 'Test', chapters_json: mockChapters
    })
    const wrapper = mount(ChapterPanel, {
      props: { projectId: 'p1', selectedChapterId: null }
    })
    await wrapper.vm.$nextTick()
    const items = wrapper.findAll('.chapter-item')
    expect(items).toHaveLength(3)
  })

  it('emits select-chapter on click', async () => {
    mockedGetProject.mockResolvedValueOnce({
      project_id: 'p1', title: 'Test', chapters_json: mockChapters
    })
    const wrapper = mount(ChapterPanel, {
      props: { projectId: 'p1', selectedChapterId: null }
    })
    await wrapper.vm.$nextTick()
    await wrapper.findAll('.chapter-item')[1].trigger('click')
    expect(wrapper.emitted('select-chapter')).toBeTruthy()
    expect(wrapper.emitted('select-chapter')![0]).toEqual(['ch2'])
  })

  it('highlights selected chapter', async () => {
    mockedGetProject.mockResolvedValueOnce({
      project_id: 'p1', title: 'Test', chapters_json: mockChapters
    })
    const wrapper = mount(ChapterPanel, {
      props: { projectId: 'p1', selectedChapterId: 'ch2' }
    })
    await wrapper.vm.$nextTick()
    const active = wrapper.find('.chapter-item.active')
    expect(active.exists()).toBe(true)
    expect(active.text()).toContain('第二章')
  })

  it('maps state to Chinese labels', async () => {
    mockedGetProject.mockResolvedValueOnce({
      project_id: 'p1', title: 'Test', chapters_json: mockChapters
    })
    const wrapper = mount(ChapterPanel, {
      props: { projectId: 'p1', selectedChapterId: null }
    })
    await wrapper.vm.$nextTick()
    const draft = wrapper.find('.state-draft')
    const review = wrapper.find('.state-review')
    const committed = wrapper.find('.state-committed')
    expect(draft.text()).toContain('草稿')
    expect(review.text()).toContain('审查中')
    expect(committed.text()).toContain('已定稿')
  })
})
