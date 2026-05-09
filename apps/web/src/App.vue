<template>
  <el-container class="workspace-shell">
    <!-- Left: Chapter State -->
    <el-aside class="panel panel-left" :width="leftWidth + 'px'">
      <ChapterPanel
        :project-id="projectId"
        :selected-chapter-id="selectedChapterId"
        @select-chapter="onSelectChapter"
      />
    </el-aside>

    <!-- Resizer -->
    <div class="resizer" @mousedown="startResize('left', $event)"></div>

    <!-- Center: Workspace -->
    <el-main class="panel panel-center">
      <div class="workspace-placeholder">
        <p class="workspace-hint">选择左侧章节开始工作</p>
      </div>
    </el-main>

    <!-- Resizer -->
    <div class="resizer" @mousedown="startResize('right', $event)"></div>

    <!-- Right: Review + Commit Preview -->
    <el-aside class="panel panel-right" :width="rightWidth + 'px'">
      <ReviewPanel
        :project-id="projectId"
        :chapter-id="selectedChapterId"
        :events="chapterEvents"
      />
    </el-aside>
  </el-container>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import ChapterPanel from '@/components/ChapterPanel.vue'
import ReviewPanel from '@/components/ReviewPanel.vue'
import { getEvents } from '@/api/client'
import type { EventRecord } from '@/api/types'

const projectId = ref('default-project')
const selectedChapterId = ref<string | null>(null)
const chapterEvents = ref<EventRecord[]>([])

const leftWidth = ref(280)
const rightWidth = ref(360)

function onSelectChapter(chapterId: string) {
  selectedChapterId.value = chapterId
  loadChapterEvents(chapterId)
}

async function loadChapterEvents(chapterId: string) {
  try {
    chapterEvents.value = await getEvents(projectId.value, chapterId)
  } catch {
    chapterEvents.value = []
  }
}

// Resize logic
let resizeTarget: 'left' | 'right' | null = null
let resizeStartX = 0
let resizeStartW = 0

function startResize(target: 'left' | 'right', e: MouseEvent) {
  resizeTarget = target
  resizeStartX = e.clientX
  resizeStartW = target === 'left' ? leftWidth.value : rightWidth.value
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', stopResize)
}

function onResizeMove(e: MouseEvent) {
  if (!resizeTarget) return
  const dx = e.clientX - resizeStartX
  if (resizeTarget === 'left') {
    leftWidth.value = Math.max(200, Math.min(500, resizeStartW + dx))
  } else {
    rightWidth.value = Math.max(240, Math.min(600, resizeStartW + dx))
  }
}

function stopResize() {
  resizeTarget = null
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', stopResize)
}

onUnmounted(stopResize)
</script>

<style>
html, body, #app {
  height: 100%;
  overflow: hidden;
}

.workspace-shell {
  height: 100vh;
  background: #111110;
}

.panel {
  background: #181816;
  border-right: 1px solid #2a2a26;
  overflow: hidden;
}

.panel-left {
  /* border-right handled by .panel */
}

.panel-center {
  background: #0f0f0e;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.panel-right {
  border-left: 1px solid #2a2a26;
  border-right: none;
}

.resizer {
  width: 4px;
  background: #2a2a26;
  cursor: col-resize;
  flex-shrink: 0;
  transition: background 0.15s;
}

.resizer:hover {
  background: #4a4a44;
}

.workspace-placeholder {
  text-align: center;
  color: #4a4a44;
}

.workspace-hint {
  font-size: 15px;
  letter-spacing: 0.05em;
}

/* Element Plus dark overrides */
.el-aside {
  --el-aside-bg-color: #181816;
}
</style>
