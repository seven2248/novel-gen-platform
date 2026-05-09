<template>
  <div class="chapter-panel">
    <div class="panel-header">
      <span class="panel-title">章节状态</span>
      <el-button size="small" @click="loadChapters" :loading="loading" circle>
        <span>&#8635;</span>
      </el-button>
    </div>

    <div class="chapter-list" v-loading="loading">
      <div
        v-for="ch in chapters"
        :key="ch.chapter_id"
        class="chapter-item"
        :class="{ active: ch.chapter_id === selectedChapterId }"
        @click="$emit('select-chapter', ch.chapter_id)"
      >
        <span class="chapter-num">第{{ ch.chapter_number }}章</span>
        <span class="chapter-title">{{ ch.title || '无标题' }}</span>
        <span class="chapter-state" :class="'state-' + ch.state">{{ stateLabel(ch.state) }}</span>
      </div>

      <el-empty v-if="!loading && loadError" description="加载失败" :image-size="60" />
      <el-empty v-else-if="!loading && chapters.length === 0 && !loadError" description="暂无章节" :image-size="60" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getProject } from '@/api/client'
import type { ChapterSummary } from '@/api/types'

const props = defineProps<{
  projectId: string
  selectedChapterId: string | null
}>()

defineEmits<{
  (e: 'select-chapter', chapterId: string): void
}>()

const chapters = ref<ChapterSummary[]>([])
const loading = ref(false)
const loadError = ref<string | null>(null)

async function loadChapters() {
  loading.value = true
  loadError.value = null
  try {
    const proj = await getProject(props.projectId)
    chapters.value = proj.chapters_json || []
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : '加载失败'
    chapters.value = []
  } finally {
    loading.value = false
  }
}

function stateLabel(state: string): string {
  const map: Record<string, string> = {
    draft: '草稿',
    review: '审查中',
    revised: '已精修',
    committed: '已定稿'
  }
  return map[state] ?? state
}

watch(() => props.projectId, () => loadChapters())

onMounted(loadChapters)
</script>

<style scoped>
.chapter-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.chapter-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.chapter-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: background 0.12s, border-color 0.12s;
}

.chapter-item:hover {
  background: #222220;
}

.chapter-item.active {
  background: #1e1e1b;
  border-left-color: #c9a96e;
}

.chapter-num {
  font-size: 11px;
  color: #6a6660;
  flex-shrink: 0;
  font-family: monospace;
}

.chapter-title {
  font-size: 13px;
  color: #c8c4be;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chapter-state {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}

.state-draft { background: #2a2a26; color: #8a8a82; }
.state-review { background: #2e2a18; color: #c9a96e; }
.state-revised { background: #182e1e; color: #6ec98a; }
.state-committed { background: #1e2832; color: #6a9ec9; }
</style>
