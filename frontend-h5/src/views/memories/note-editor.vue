<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { useMemoriesStore } from '@/stores/memories'
import { useUserStore } from '@/stores/user'
import { useDraft } from '@/composables/useDraft'
import { uploadApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'

const props = defineProps({
  noteId: { type: [String, Number], default: null },
  initialNote: { type: Object, default: null }
})
const emit = defineEmits(['saved', 'cancel'])
const router = useRouter()
const memoriesStore = useMemoriesStore()
const userStore = useUserStore()
const resourceId = props.noteId ? String(props.noteId) : null
const draftStore = useDraft({ userId: userStore.userInfo?.id, resource: 'note', resourceId })
const form = reactive({
  title: props.initialNote?.title || '',
  content: props.initialNote?.content || '',
  location: props.initialNote?.location || '',
  latitude: props.initialNote?.latitude ?? null,
  longitude: props.initialNote?.longitude ?? null,
  isAnniversaryLinked: props.initialNote?.isAnniversaryLinked ? 1 : 0,
  anniversaryId: props.initialNote?.anniversaryId ?? null,
  photoUrls: Array.isArray(props.initialNote?.photoUrls) ? [...props.initialNote.photoUrls] : []
})
const dirty = ref(false)
const uploading = ref(false)
const uploadRequestId = ref(0)
const submitting = computed(() => memoriesStore.mutationStatus === 'loading')
const canSubmit = computed(() => form.title.trim() && form.content.trim() && !submitting.value && !uploading.value)

const snapshot = () => ({ ...form, photoUrls: [...form.photoUrls] })
const markDirty = () => {
  dirty.value = true
  draftStore.save(snapshot())
}
const restoreDraft = () => {
  const saved = draftStore.restore()
  if (saved) {
    Object.assign(form, saved, { photoUrls: Array.isArray(saved.photoUrls) ? [...saved.photoUrls] : [] })
    dirty.value = true
  }
}
const uploadPhoto = async (event) => {
  const file = event.target.files?.[0]
  if (!file || uploading.value) return
  const startedAt = Date.now()
  const requestId = ++uploadRequestId.value
  uploading.value = true
  logUiEvent('memories.note.photo_upload', {
    module: 'note_editor', operation: 'upload_photo', result: 'loading', durationMs: 0, requestId
  })
  try {
    const response = await uploadApi.uploadImage(file)
    const url = response?.data?.url || response?.data
    if (typeof url === 'string' && url) form.photoUrls.push(url)
    markDirty()
    logUiEvent('memories.note.photo_upload', {
      module: 'note_editor', operation: 'upload_photo', result: 'success',
      durationMs: Date.now() - startedAt, requestId, itemCount: 1
    })
  } catch (error) {
    logUiEvent('memories.note.photo_upload', {
      module: 'note_editor', operation: 'upload_photo', result: 'error',
      durationMs: Date.now() - startedAt, requestId, errorCode: String(error?.code || 'UNKNOWN')
    })
    showToast('图片上传失败，草稿已保留')
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}
const submit = async () => {
  if (!canSubmit.value) return
  const payload = {
    title: form.title.trim(),
    content: form.content.trim(),
    location: form.location.trim(),
    latitude: form.latitude,
    longitude: form.longitude,
    isAnniversaryLinked: Number(form.isAnniversaryLinked) ? 1 : 0,
    anniversaryId: Number(form.isAnniversaryLinked) ? form.anniversaryId : null,
    photoUrls: [...form.photoUrls]
  }
  try {
    const saved = await memoriesStore.saveNote(resourceId, payload)
    draftStore.clear()
    dirty.value = false
    emit('saved', saved)
    if (!props.noteId) router.replace(`/memories/notes/${saved.id}`)
  } catch (error) {
    draftStore.save(snapshot())
    showToast('保存失败，草稿仍在本机')
  }
}

onBeforeRouteLeave(async () => {
  if (!dirty.value || submitting.value) return true
  try {
    await showConfirmDialog({ title: '保留草稿并离开？', message: '当前笔记尚未保存。' })
    return true
  } catch (error) {
    return false
  }
})
</script>

<template>
  <main class="note-editor">
    <header class="editor-header">
      <button type="button" aria-label="返回" @click="props.noteId ? emit('cancel') : router.back()">
        <van-icon name="arrow-left" />
      </button>
      <h1>{{ props.noteId ? '编辑味觉故事' : '记录味觉故事' }}</h1>
      <span />
    </header>

    <button v-if="draftStore.hasDraft.value" class="restore-draft" type="button" data-test="restore-note-draft" @click="restoreDraft">
      恢复本机草稿
    </button>

    <form @submit.prevent="submit">
      <section class="photo-panel">
        <div v-if="form.photoUrls.length" class="photo-grid">
          <figure v-for="(url, index) in form.photoUrls" :key="`${url}:${index}`">
            <img :src="url" alt="笔记照片">
            <button type="button" :aria-label="`删除第 ${index + 1} 张照片`" @click="form.photoUrls.splice(index, 1); markDirty()">
              <van-icon name="cross" />
            </button>
          </figure>
        </div>
        <label class="photo-picker">
          <van-icon name="photograph" />
          <span>{{ uploading ? '上传中…' : '添加照片' }}</span>
          <input type="file" accept="image/*" :disabled="uploading || submitting" @change="uploadPhoto">
        </label>
      </section>

      <label class="field-label" for="note-title">标题</label>
      <input id="note-title" v-model="form.title" data-test="note-title" maxlength="80" placeholder="给这段回忆起个名字" @input="markDirty">

      <label class="field-label" for="note-content">味觉故事</label>
      <textarea id="note-content" v-model="form.content" data-test="note-content" maxlength="2000" rows="8" placeholder="写下当时的味道和心情" @input="markDirty" />

      <label class="field-label" for="note-location">位置（可选）</label>
      <input id="note-location" v-model="form.location" data-test="note-location" maxlength="120" placeholder="只会提交你填写的位置" @input="markDirty">

      <label class="anniversary-link">
        <input v-model="form.isAnniversaryLinked" type="checkbox" :true-value="1" :false-value="0" @change="markDirty">
        <span>关联纪念日</span>
      </label>
      <input v-if="form.isAnniversaryLinked" v-model.number="form.anniversaryId" inputmode="numeric" min="1" type="number" placeholder="纪念日 ID" @input="markDirty">

      <p class="contract-note">菜谱关联暂不可用；图片使用真实 photoUrls[] 合同。</p>
      <button class="submit-button" data-test="note-submit" type="submit" :disabled="!canSubmit">
        {{ submitting ? '正在保存…' : '保存到回忆' }}
      </button>
    </form>
  </main>
</template>

<style lang="scss" scoped>
.note-editor { min-height: 100%; padding: $space-4 $page-padding $space-8; color: $cosmos-text; }
.editor-header { display: grid; min-height: 52px; grid-template-columns: 44px 1fr 44px; align-items: center; }
.editor-header h1 { font-size: $fs-title; text-align: center; }.editor-header button { width: 44px; height: 44px; border: 0; background: transparent; color: $cosmos-text; }
.restore-draft { width: 100%; min-height: 40px; margin: $space-3 0; border: 1px solid $cosmos-secondary; border-radius: $radius-sm; background: rgba(84, 232, 211, 0.1); color: $cosmos-secondary; }
form { display: flex; flex-direction: column; gap: $space-3; }
.photo-panel { min-height: 150px; padding: $space-3; border: 1px solid $cosmos-border; border-radius: $radius-md; background: $cosmos-surface-elevated; }
.photo-grid { display: grid; margin-bottom: $space-3; grid-template-columns: repeat(3, 1fr); gap: $space-2; }.photo-grid figure { position: relative; margin: 0; aspect-ratio: 1; }.photo-grid img { width: 100%; height: 100%; border-radius: $radius-sm; object-fit: cover; }
.photo-grid button { position: absolute; top: 4px; right: 4px; width: 32px; height: 32px; border: 0; border-radius: 50%; background: rgba(11, 16, 32, 0.8); color: white; }
.photo-picker { display: flex; min-height: 48px; align-items: center; justify-content: center; gap: $space-2; border: 1px dashed $cosmos-border; border-radius: $radius-sm; color: $cosmos-secondary; }.photo-picker input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.field-label { margin-top: $space-2; color: $cosmos-gold; font-size: $fs-label; }
input, textarea { width: 100%; padding: $space-3; border: 1px solid $cosmos-border; border-radius: $radius-sm; outline: none; background: rgba(255, 255, 255, 0.05); color: $cosmos-text; font: inherit; }.note-editor textarea { resize: vertical; }
input:focus, textarea:focus { border-color: $cosmos-secondary; }.anniversary-link { display: flex; min-height: 44px; align-items: center; gap: $space-3; }.anniversary-link input { width: 20px; }
.contract-note { color: $cosmos-text-muted; font-size: $fs-caption; }.submit-button { min-height: 52px; margin-top: $space-2; border: 0; border-radius: $radius-md; background: $cosmos-primary; color: white; font-size: $fs-body; font-weight: $fw-semibold; }.submit-button:disabled { cursor: not-allowed; opacity: 0.5; }
</style>
