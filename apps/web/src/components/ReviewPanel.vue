<template>
  <div class="review-panel">
    <div class="panel-header">
      <span class="panel-title">审查 & 提交预览</span>
    </div>

    <!-- Tabs: 审查历史 | 提交预览 -->
    <el-tabs v-model="activeTab" class="review-tabs">
      <el-tab-pane label="审查历史" name="review">
        <div class="event-list">
          <div v-for="evt in events" :key="evt.id" class="event-item">
            <div class="event-header">
              <span class="event-type">{{ eventTypeLabel(evt.event_type) }}</span>
              <span class="event-time">{{ formatTime(evt.created_at) }}</span>
            </div>
            <div class="event-payload">{{ truncate(JSON.stringify(evt.payload), 80) }}</div>
          </div>
          <el-empty v-if="events.length === 0" description="暂无审查记录" :image-size="50" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="提交预览" name="commit">
        <div class="commit-preview">
          <template v-if="lastCommittedEvent">
            <div class="commit-block">
              <div class="commit-label">最近提交</div>
              <div class="commit-type">{{ eventTypeLabel(lastCommittedEvent.event_type) }}</div>
              <pre class="commit-payload">{{ JSON.stringify(lastCommittedEvent.payload, null, 2) }}</pre>
            </div>
          </template>
          <el-empty v-else description="暂无提交预览" :image-size="50" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { EventRecord } from '@/api/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
  events: EventRecord[]
}>()

const activeTab = ref<'review' | 'commit'>('review')

const lastCommittedEvent = computed(() =>
  props.events.find(e => e.event_type === 'chapter_committed') ?? null
)

function eventTypeLabel(type: string): string {
  const map: Record<string, string> = {
    chapter_created: '章节创建',
    chapter_draft_generated: '草稿生成',
    chapter_reviewed: '审查完成',
    chapter_revised: '精修完成',
    chapter_committed: '已定稿',
    workflow_started: '工作流开始',
    workflow_completed: '工作流完成'
  }
  return map[type] ?? type
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    })
  } catch {
    return iso
  }
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '…' : s
}
</script>

<style scoped>
.review-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  padding: 16px 14px 12px;
  border-bottom: 1px solid #2a2a26;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #8a8680;
  text-transform: uppercase;
}

.review-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.review-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.review-tabs :deep(.el-tab-pane) {
  height: 100%;
  overflow-y: auto;
}

.event-list {
  padding: 8px 0;
}

.event-item {
  padding: 10px 14px;
  border-bottom: 1px solid #1e1e1b;
}

.event-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.event-type {
  font-size: 12px;
  color: #c9a96e;
}

.event-time {
  font-size: 10px;
  color: #5a5650;
  font-family: monospace;
}

.event-payload {
  font-size: 11px;
  color: #6a6660;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.commit-preview {
  padding: 12px 14px;
}

.commit-block {
  background: #111110;
  border: 1px solid #2a2a26;
  border-radius: 4px;
  padding: 12px;
}

.commit-label {
  font-size: 10px;
  color: #5a5650;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
}

.commit-type {
  font-size: 13px;
  color: #c9a96e;
  margin-bottom: 8px;
}

.commit-payload {
  font-size: 11px;
  color: #8a8680;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}
</style>
