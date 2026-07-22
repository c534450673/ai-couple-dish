<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { useMemoriesStore } from '@/stores/memories'
import NoteEditor from './note-editor.vue'

const route = useRoute()
const router = useRouter()
const store = useMemoriesStore()
const id = String(route.params.id || '')
const validId = /^[1-9]\d*$/.test(id)
const note = ref(null)
const status = ref(validId ? 'loading' : 'invalid')
const editing = ref(false)

const load = async () => {
  if (!validId) return
  status.value = 'loading'
  try {
    note.value = await store.fetchNoteDetail(id)
    status.value = note.value ? 'success' : 'empty'
  } catch (error) {
    status.value = 'error'
  }
}
const remove = async () => {
  try {
    await showConfirmDialog({ title: '删除这篇笔记？', message: '删除后无法恢复。' })
    await store.removeNote(id)
    router.replace('/memories?type=note')
  } catch (error) {
    if (error) showToast('删除未完成')
  }
}
const saved = (value) => {
  note.value = { ...note.value, ...value }
  editing.value = false
}

onMounted(load)
</script>

<template>
  <NoteEditor v-if="editing" :note-id="id" :initial-note="note" @saved="saved" @cancel="editing = false" />
  <main v-else class="note-detail">
    <header>
      <button type="button" aria-label="返回" @click="router.back()"><van-icon name="arrow-left" /></button>
      <span>味觉故事</span><span />
    </header>
    <section v-if="status === 'invalid'" class="detail-state" data-test="invalid-note-id">
      <p>笔记 ID 无效。</p>
      <button data-test="back-memories" type="button" @click="router.replace('/memories?type=note')">返回回忆</button>
    </section>
    <section v-else-if="status === 'loading'" class="detail-state">正在读取笔记…</section>
    <section v-else-if="status === 'error'" class="detail-state" role="alert">
      <p>笔记暂时无法加载。</p><button type="button" @click="load">重试</button>
    </section>
    <section v-else-if="status === 'empty'" class="detail-state">没有找到这篇笔记。</section>
    <article v-else class="note-content">
      <div v-if="note.photoUrls?.length" class="note-photos">
        <img v-for="(url, index) in note.photoUrls" :key="`${url}:${index}`" :data-test="`note-photo-${index}`" :src="url" :alt="`笔记照片 ${index + 1}`">
      </div>
      <p class="note-author">{{ note.authorName || '共同记录' }} · {{ note.createTime || '日期待补充' }}</p>
      <h1>{{ note.title }}</h1>
      <p class="note-body">{{ note.content }}</p>
      <dl>
        <div><dt>位置</dt><dd>{{ note.location || '未记录' }}</dd></div>
        <div><dt>关联纪念日</dt><dd>{{ note.isAnniversaryLinked ? (note.anniversaryName || '已关联') : '未关联' }}</dd></div>
        <div><dt>关联菜谱</dt><dd>菜谱关联暂不可用</dd></div>
      </dl>
      <div v-if="note.isAuthor" class="author-actions">
        <button data-test="note-edit" type="button" @click="editing = true"><van-icon name="edit" /> 编辑</button>
        <button type="button" @click="remove"><van-icon name="delete-o" /> 删除</button>
      </div>
      <p class="contract-note">评论流暂不可用；现有后端只提供评论计数，没有评论实体。</p>
    </article>
  </main>
</template>

<style lang="scss" scoped>
.note-detail { min-height: 100%; padding: $space-4 $page-padding $space-8; color: $cosmos-text; }.note-detail > header { display: grid; min-height: 52px; grid-template-columns: 44px 1fr 44px; align-items: center; text-align: center; }.note-detail > header button { width: 44px; height: 44px; border: 0; background: transparent; color: inherit; }
.detail-state { display: flex; min-height: 320px; flex-direction: column; align-items: center; justify-content: center; gap: $space-3; color: $cosmos-text-muted; text-align: center; }.detail-state button { min-height: 44px; padding: 0 $space-4; border: 0; border-radius: $radius-pill; background: $cosmos-primary; color: white; }
.note-photos { display: grid; margin: 0 calc(-1 * $page-padding) $space-5; grid-auto-columns: 82%; grid-auto-flow: column; gap: $space-2; overflow-x: auto; scroll-snap-type: x mandatory; }.note-photos img { width: 100%; aspect-ratio: 4 / 5; object-fit: cover; scroll-snap-align: start; }
.note-author { color: $cosmos-secondary; font-size: $fs-caption; }.note-content h1 { margin-top: $space-2; font-size: $fs-display; }.note-body { margin-top: $space-5; color: $cosmos-text; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
dl { margin-top: $space-6; border-top: 1px solid $cosmos-border; }dl div { display: grid; min-height: 52px; grid-template-columns: 96px minmax(0, 1fr); align-items: center; border-bottom: 1px solid $cosmos-border; }dt { color: $cosmos-text-muted; }dd { margin: 0; overflow-wrap: anywhere; }
.author-actions { display: grid; margin-top: $space-5; grid-template-columns: 1fr 1fr; gap: $space-3; }.author-actions button { min-height: 44px; border: 1px solid $cosmos-border; border-radius: $radius-sm; background: $cosmos-surface-elevated; color: $cosmos-text; }.contract-note { margin-top: $space-5; color: $cosmos-text-muted; font-size: $fs-caption; }
</style>
