<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { uploadApi } from '@/api'
import { useMenuStore } from '@/stores/menu'
import { useUserStore } from '@/stores/user'
import { useDraft } from '@/composables/useDraft'
import { logUiEvent } from '@/composables/useStructuredLog'

const route = useRoute()
const router = useRouter()
const store = useMenuStore()
const userStore = useUserStore()
const editId = computed(() => (/^[1-9]\d*$/.test(String(route.params.id || '')) ? String(route.params.id) : null))
const isEdit = computed(() => Boolean(editId.value))
const draftStore = useDraft({
  userId: userStore.userInfo?.id,
  resource: 'menu',
  resourceId: editId.value || undefined
})

const form = reactive({
  restaurantName: '', dishName: '', dishCategory: '', price: '', location: '',
  note: '', rating: '', eaterIds: [], eatenDate: '', status: 0
})
const photos = ref([])
const submitting = ref(false)
const dirty = ref(false)
const ready = ref(false)
const restoreAvailable = ref(draftStore.hasDraft.value)

const hydrate = (value = {}) => {
  Object.keys(form).forEach((key) => {
    if (value[key] !== undefined && value[key] !== null) form[key] = value[key]
  })
  photos.value = Array.isArray(value.photoUrls)
    ? value.photoUrls.map(url => ({ url, status: 'done', localOnly: true }))
    : []
}

const draftSnapshot = () => ({
  ...form,
  photoUrls: photos.value.filter(photo => photo.status === 'done').map(photo => photo.url)
})

const restoreDraft = () => {
  const value = draftStore.restore()
  if (!value) return
  hydrate(value)
  restoreAvailable.value = false
  dirty.value = true
  logUiEvent('menu.editor.draft_restored', {
    module: 'menu_editor', operation: 'restore_draft', result: 'success', durationMs: 0,
    mode: isEdit.value ? 'edit' : 'new'
  })
}

const validateFile = (file) => {
  if (!file.type?.startsWith('image/')) return '只支持图片文件'
  if (file.size > 10 * 1024 * 1024) return '单张图片不能超过 10MB'
  return ''
}

const uploadFile = async (file) => {
  const startedAt = Date.now()
  const preview = typeof URL?.createObjectURL === 'function' ? URL.createObjectURL(file) : ''
  const photo = reactive({ name: file.name, preview, url: '', status: 'uploading', message: '上传中' })
  photos.value.push(photo)
  logUiEvent('menu.editor.upload', {
    module: 'menu_editor', operation: 'upload_image', result: 'started', durationMs: 0,
    fileSize: file.size, fileType: file.type || 'unknown'
  })
  try {
    const response = await uploadApi.uploadImage(file)
    photo.url = response?.data?.url || ''
    photo.status = 'done'
    photo.message = '仅本地预览'
    logUiEvent('menu.editor.upload', {
      module: 'menu_editor', operation: 'upload_image', result: 'success',
      durationMs: Date.now() - startedAt, fileSize: file.size
    })
  } catch (error) {
    photo.status = 'failed'
    photo.message = '上传失败，可删除后重试'
    logUiEvent('menu.editor.upload', {
      module: 'menu_editor', operation: 'upload_image', result: 'failed',
      durationMs: Date.now() - startedAt,
      errorCode: String(error?.code || error?.response?.status || 'UPLOAD_FAILED')
    })
    showToast('图片上传失败')
  }
}

const selectPhotos = async (event) => {
  const selected = [...(event.target.files || [])]
  if (photos.value.length + selected.length > 9) {
    showToast('最多选择 9 张图片')
    event.target.value = ''
    return
  }
  for (const file of selected) {
    const validationError = validateFile(file)
    if (validationError) {
      showToast(validationError)
      logUiEvent('menu.editor.upload', {
        module: 'menu_editor', operation: 'validate_image', result: 'rejected', durationMs: 0,
        errorCode: file.size > 10 * 1024 * 1024 ? 'FILE_TOO_LARGE' : 'INVALID_FILE_TYPE'
      })
      continue
    }
    await uploadFile(file)
  }
  event.target.value = ''
}

const removePhoto = (index) => {
  const [removed] = photos.value.splice(index, 1)
  if (removed?.preview && typeof URL?.revokeObjectURL === 'function') URL.revokeObjectURL(removed.preview)
  logUiEvent('menu.editor.photo_removed', {
    module: 'menu_editor', operation: 'remove_local_photo', result: 'success', durationMs: 0
  })
}

const payload = () => ({
  restaurantName: form.restaurantName.trim(),
  dishName: form.dishName.trim() || null,
  dishCategory: form.dishCategory.trim() || null,
  price: form.price === '' ? null : Number(form.price),
  location: form.location.trim() || null,
  note: form.note.trim() || null,
  rating: form.rating === '' ? null : Number(form.rating),
  eaterIds: form.eaterIds,
  eatenDate: form.eatenDate || null,
  status: Number(form.status),
  photoUrls: photos.value.filter(photo => photo.status === 'done' && photo.url).map(photo => photo.url)
})

const submit = async () => {
  if (submitting.value) return
  if (!form.restaurantName.trim()) {
    showToast('请填写餐厅名称')
    return
  }
  const startedAt = Date.now()
  submitting.value = true
  logUiEvent('menu.editor.submit', {
    module: 'menu_editor', operation: isEdit.value ? 'update' : 'create', result: 'started',
    durationMs: 0, photoCount: photos.value.length
  })
  try {
    const result = isEdit.value
      ? await store.update(editId.value, payload())
      : await store.create(payload())
    draftStore.clear()
    dirty.value = false
    const createdId = typeof result === 'object' ? result?.id : result
    logUiEvent('menu.editor.submit', {
      module: 'menu_editor', operation: isEdit.value ? 'update' : 'create', result: 'success',
      durationMs: Date.now() - startedAt, photoCount: photos.value.length
    })
    showToast(isEdit.value ? '已更新餐厅' : '已添加餐厅')
    router.replace(isEdit.value ? `/menu/${editId.value}` : (createdId ? `/menu/${createdId}` : '/menu'))
  } catch (error) {
    logUiEvent('menu.editor.submit', {
      module: 'menu_editor', operation: isEdit.value ? 'update' : 'create', result: 'failed',
      durationMs: Date.now() - startedAt,
      errorCode: String(error?.code || error?.response?.status || 'SUBMIT_FAILED')
    })
    showToast('保存失败，草稿已保留')
  } finally {
    submitting.value = false
  }
}

const beforeUnload = (event) => {
  if (!dirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

onBeforeRouteLeave((_to, _from, next) => {
  if (!dirty.value || globalThis.confirm?.('当前修改尚未保存，确定离开吗？')) next()
  else next(false)
})

watch([form, photos], () => {
  if (!ready.value) return
  dirty.value = true
  draftStore.save(draftSnapshot())
}, { deep: true })

onMounted(async () => {
  globalThis.addEventListener?.('beforeunload', beforeUnload)
  if (isEdit.value) {
    try {
      await store.fetchDetail(editId.value)
      if (store.detail) hydrate(store.detail)
    } catch (_) {
      showToast('详情加载失败，可恢复本地草稿后继续')
    }
  }
  ready.value = true
})

onBeforeUnmount(() => {
  globalThis.removeEventListener?.('beforeunload', beforeUnload)
  photos.value.forEach(photo => {
    if (photo.preview && typeof URL?.revokeObjectURL === 'function') URL.revokeObjectURL(photo.preview)
  })
})
</script>

<template>
  <main class="menu-editor">
    <header class="editor-header">
      <button type="button" aria-label="返回" @click="router.back()"><van-icon name="arrow-left" /></button>
      <div><p>COUPLE COSMOS</p><h1>{{ isEdit ? '编辑餐厅' : '添加餐厅' }}</h1></div>
      <span aria-hidden="true" />
    </header>

    <aside v-if="restoreAvailable" class="restore-banner">
      <div><strong>发现本地草稿</strong><p>仅恢复当前用户与当前餐厅的内容。</p></div>
      <button type="button" data-test="restore-menu-draft" @click="restoreDraft">恢复</button>
    </aside>

    <form @submit.prevent="submit">
      <section class="form-section">
        <h2>餐厅信息</h2>
        <label>餐厅名称 <em>必填</em><input data-test="restaurant-name" v-model="form.restaurantName" maxlength="100" autocomplete="off"></label>
        <div class="two-columns">
          <label>推荐菜<input v-model="form.dishName" maxlength="100"></label>
          <label>菜品分类<input v-model="form.dishCategory" maxlength="50"></label>
        </div>
        <div class="two-columns">
          <label>人均价格<input v-model="form.price" type="number" min="0" step="0.01"></label>
          <label>评分<input v-model="form.rating" type="number" min="0" max="5" step="0.5"></label>
        </div>
        <label>状态<select v-model="form.status"><option :value="0">想去</option><option :value="1">去过</option><option :value="2">种草</option></select></label>
        <label>地址<input v-model="form.location" maxlength="255" autocomplete="street-address"></label>
        <label>我们的记录<textarea v-model="form.note" rows="4" maxlength="1000" /></label>
      </section>

      <section class="form-section">
        <div class="section-heading"><div><h2>图片预览</h2><p>最多 9 张，单张不超过 10MB</p></div><label class="upload-button"><van-icon name="photograph" /> 选择图片<input type="file" accept="image/*" multiple @change="selectPhotos"></label></div>
        <p class="contract-warning">后端图片合同缺失：图片仅保留在本地草稿与本次预览，刷新后的列表和详情仍显示占位。</p>
        <div v-if="photos.length" class="photo-grid">
          <figure v-for="(photo, index) in photos" :key="`${photo.name || 'draft'}-${index}`">
            <img v-if="photo.preview || photo.url" :src="photo.preview || photo.url" alt="待提交餐厅图片预览">
            <div v-else class="photo-fallback"><van-icon name="photo-o" /></div>
            <figcaption>{{ photo.message || '仅本地预览' }}</figcaption>
            <button type="button" aria-label="删除本地图片" @click="removePhoto(index)"><van-icon name="delete-o" /></button>
          </figure>
        </div>
      </section>

      <button data-test="menu-submit" class="submit-button" type="submit" :disabled="submitting">
        {{ submitting ? '保存中…' : (isEdit ? '保存修改' : '添加到美食库') }}
      </button>
    </form>
  </main>
</template>

<style lang="scss" scoped>
.menu-editor { min-height: 100vh; padding: $space-5 $page-padding 112px; color: $cosmos-text; background: $cosmos-bg; }
.editor-header { display: grid; grid-template-columns: 44px 1fr 44px; gap: $space-3; align-items: center; margin-bottom: $space-5; text-align: center; }
.editor-header > button { min-width: 44px; min-height: 44px; border: 1px solid $cosmos-border; border-radius: 50%; background: $cosmos-surface-raised; color: $cosmos-text; }
.editor-header p { color: $cosmos-secondary; font-size: $fs-caption; }
.editor-header h1 { margin-top: $space-1; font-size: $fs-title; }
.restore-banner { display: flex; gap: $space-4; align-items: center; justify-content: space-between; margin-bottom: $space-5; padding: $space-4; border: 1px solid $cosmos-secondary; border-radius: 8px; background: rgba(84, 232, 211, .08); }
.restore-banner p { margin-top: $space-1; color: $cosmos-text-muted; font-size: $fs-caption; }
.restore-banner button { min-height: 40px; padding: 0 $space-4; border: 0; border-radius: 6px; background: $cosmos-secondary; color: #052c27; }
.form-section { padding: $space-5 0; border-top: 1px solid $cosmos-border; }
.form-section h2 { font-size: $fs-title; }
.form-section > label, .two-columns label { display: grid; gap: $space-2; margin-top: $space-4; color: $cosmos-text-muted; font-size: $fs-label; }
em { color: $cosmos-primary; font-style: normal; font-size: $fs-caption; }
input, select, textarea { width: 100%; min-height: 46px; padding: $space-3; border: 1px solid $cosmos-border; border-radius: 6px; outline: 0; background: $cosmos-surface-raised; color: $cosmos-text; font: inherit; }
textarea { resize: vertical; }
input:focus, select:focus, textarea:focus { border-color: $cosmos-secondary; }
.two-columns { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; }
.section-heading { display: flex; gap: $space-3; align-items: flex-start; justify-content: space-between; }
.section-heading p { margin-top: $space-1; color: $cosmos-text-muted; font-size: $fs-caption; }
.upload-button { display: flex; min-height: 44px; gap: $space-2; align-items: center; padding: 0 $space-3; border: 1px solid $cosmos-secondary; border-radius: 6px; color: $cosmos-secondary; cursor: pointer; }
.upload-button input { display: none; }
.contract-warning { margin-top: $space-4; padding: $space-3; border-left: 3px solid $cosmos-gold; background: rgba(255, 200, 87, .08); color: $cosmos-text-muted; font-size: $fs-caption; line-height: 20px; }
.photo-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: $space-3; margin-top: $space-4; }
.photo-grid figure { position: relative; overflow: hidden; aspect-ratio: 1; border: 1px solid $cosmos-border; border-radius: 6px; background: $cosmos-surface-raised; }
.photo-grid img, .photo-fallback { width: 100%; height: 100%; object-fit: cover; }
.photo-fallback { display: grid; place-items: center; }
.photo-grid figcaption { position: absolute; right: 0; bottom: 0; left: 0; padding: $space-1; overflow: hidden; background: rgba(8,12,37,.78); color: $cosmos-text; text-overflow: ellipsis; white-space: nowrap; font-size: 10px; }
.photo-grid button { position: absolute; top: $space-1; right: $space-1; width: 36px; height: 36px; border: 0; border-radius: 50%; background: rgba(8,12,37,.82); color: $cosmos-primary; }
.submit-button { position: fixed; z-index: 3; right: $page-padding; bottom: 76px; left: $page-padding; min-height: 50px; border: 0; border-radius: 6px; background: $cosmos-primary; color: #fff; font-size: $fs-body; font-weight: $fw-semibold; }
.submit-button:disabled { opacity: .55; }
@media (min-width: 720px) { .menu-editor { max-width: 760px; margin: 0 auto; } .submit-button { right: 50%; left: 50%; width: 712px; transform: translateX(-50%); } }
@media (max-width: 420px) { .two-columns { grid-template-columns: 1fr; } .photo-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
