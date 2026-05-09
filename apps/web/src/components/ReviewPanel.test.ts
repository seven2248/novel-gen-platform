import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ReviewPanel from '@/components/ReviewPanel.vue'

const mockEvents = [
  {
    id: 1,
    project_id: 'p1',
    event_type: 'chapter_created',
    actor_type: 'agent',
    correlation_id: 'ch1',
    causation_id: '',
    payload: { chapter_id: 'ch1' },
    created_at: '2026-05-09T10:00:00'
  },
  {
    id: 2,
    project_id: 'p1',
    event_type: 'chapter_committed',
    actor_type: 'agent',
    correlation_id: 'ch1',
    causation_id: '',
    payload: { chapter_id: 'ch1', version: 2 },
    created_at: '2026-05-09T11:00:00'
  }
]

describe('ReviewPanel', () => {
  it('renders empty state when no events', () => {
    const wrapper = mount(ReviewPanel, {
      props: { projectId: 'p1', chapterId: 'ch1', events: [] }
    })
    expect(wrapper.find('.el-empty').exists()).toBe(true)
  })

  it('renders event list', () => {
    const wrapper = mount(ReviewPanel, {
      props: { projectId: 'p1', chapterId: 'ch1', events: mockEvents }
    })
    const items = wrapper.findAll('.event-item')
    expect(items).toHaveLength(2)
  })

  it('switches to commit tab and shows preview', async () => {
    const wrapper = mount(ReviewPanel, {
      props: { projectId: 'p1', chapterId: 'ch1', events: mockEvents }
    })
    await wrapper.findAll('.el-tab-pane')[1].trigger('click')
    await wrapper.vm.$nextTick()
    const block = wrapper.find('.commit-block')
    expect(block.exists()).toBe(true)
    expect(block.text()).toContain('已定稿')
  })

  it('shows commit preview for chapter_committed events', async () => {
    const wrapper = mount(ReviewPanel, {
      props: { projectId: 'p1', chapterId: 'ch1', events: mockEvents }
    })
    // Switch to commit tab
    const tabs = wrapper.findAll('.el-tab-pane')
    await tabs[1].trigger('click')
    await wrapper.vm.$nextTick()
    const block = wrapper.find('.commit-block')
    expect(block.exists()).toBe(true)
  })

  it('eventTypeLabel maps Chinese labels', () => {
    const wrapper = mount(ReviewPanel, {
      props: { projectId: 'p1', chapterId: 'ch1', events: mockEvents }
    })
    const eventTypes = wrapper.findAll('.event-type')
    expect(eventTypes[0].text()).toContain('章节创建')
    expect(eventTypes[1].text()).toContain('已定稿')
  })
})
