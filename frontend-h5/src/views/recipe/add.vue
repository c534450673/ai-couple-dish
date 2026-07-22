<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { uploadApi } from '@/api'
import { useRecipeStore } from '@/stores/recipe'
import { useUserStore } from '@/stores/user'
import { useDraft } from '@/composables/useDraft'
import { logUiEvent } from '@/composables/useStructuredLog'

const route = useRoute()
const router = useRouter()
const store = useRecipeStore()
const userStore = useUserStore()
const editId = computed(() => (/^[1-9]\d*$/.test(String(route.params.id || '')) ? String(route.params.id) : null))
const isEdit = computed(() => Boolean(editId.value))
const draftStore = useDraft({
  userId: userStore.userInfo?.id,
  resource: 'recipe',
  resourceId: editId.value || undefined
})

const form = reactive({
  title: '', coverUrl: '', description: '', difficulty: 1,
  cookingTime: '', servings: '',
  ingredients: [{ name: '', amount: '' }],
  steps: [{ content: '', imageUrl: '' }]
})
const coverPreview = ref('')
const coverStatus = ref('idle')
const submitting = ref(false)
const dirty = ref(false)
const ready = ref(false)
const restoreAvailable = ref(draftStore.hasDraft.value)

const normalizedList = (value, fallback) => Array.isArray(value)
  ? value.map(item => ({ ...fallback, ...item }))
  : [{ ...fallback }]

const hydrate = (value = {}) => {
  form.title = value.title || ''
  form.coverUrl = value.coverUrl || ''
  form.description = value.description || ''
  form.difficulty = value.difficulty || 1
  form.cookingTime = value.cookingTime ?? ''
  form.servings = value.servings ?? ''
  form.ingredients = normalizedList(value.ingredients, { name: '', amount: '' })
  form.steps = normalizedList(value.steps, { content: '', imageUrl: '' })
  coverPreview.value = form.coverUrl
}

const snapshot = () => ({
  title: form.title,
  coverUrl: form.coverUrl,
  description: form.description,
  difficulty: form.difficulty,
  cookingTime: form.cookingTime,
  servings: form.servings,
  ingredients: form.ingredients.map(item => ({ name: item.name, amount: item.amount })),
  steps: form.steps.map(item => ({ content: item.content, imageUrl: item.imageUrl }))
})

const restoreDraft = () => {
  const value = draftStore.restore()
  if (!value) return
  hydrate(value)
  restoreAvailable.value = false
  dirty.value = true
  logUiEvent('recipe.editor.draft_restored', {
    module: 'recipe_editor', operation: 'restore_draft', result: 'success', durationMs: 0,
    mode: isEdit.value ? 'edit' : 'new'
  })
}

const addIngredient = () => form.ingredients.push({ name: '', amount: '' })
const removeIngredient = index => form.ingredients.splice(index, 1)
const addStep = () => form.steps.push({ content: '', imageUrl: '' })
const removeStep = index => form.steps.splice(index, 1)

const moveItem = (items, index, direction, listType) => {
  const target = index + direction
  if (target < 0 || target >= items.length) return
  const [item] = items.splice(index, 1)
  items.splice(target, 0, item)
  logUiEvent('recipe.editor.list_reordered', {
    module: 'recipe_editor', operation: 'reorder', result: 'success', durationMs: 0,
    listType, direction: direction < 0 ? 'up' : 'down', itemCount: items.length
  })
}

const chooseCover = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!file.type?.startsWith('image/')) {
    showToast('只支持图片文件')
    logUiEvent('recipe.editor.upload', {
      module: 'recipe_editor', operation: 'validate_cover', result: 'rejected', durationMs: 0,
      errorCode: 'INVALID_FILE_TYPE'
    })
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast('封面不能超过 10MB')
    logUiEvent('recipe.editor.upload', {
      module: 'recipe_editor', operation: 'validate_cover', result: 'rejected', durationMs: 0,
      errorCode: 'FILE_TOO_LARGE'
    })
    return
  }
  const startedAt = Date.now()
  if (coverPreview.value?.startsWith('blob:')) URL.revokeObjectURL?.(coverPreview.value)
  coverPreview.value = URL.createObjectURL?.(file) || ''
  coverStatus.value = 'uploading'
  logUiEvent('recipe.editor.upload', {
    module: 'recipe_editor', operation: 'upload_cover', result: 'started', durationMs: 0,
    fileSize: file.size, fileType: file.type || 'unknown'
  })
  try {
    const response = await uploadApi.uploadImage(file)
    form.coverUrl = response?.data?.url || ''
    coverStatus.value = 'success'
    logUiEvent('recipe.editor.upload', {
      module: 'recipe_editor', operation: 'upload_cover', result: 'success',
      durationMs: Date.now() - startedAt, fileSize: file.size
    })
  } catch (error) {
    coverStatus.value = 'error'
    logUiEvent('recipe.editor.upload', {
      module: 'recipe_editor', operation: 'upload_cover', result: 'failed',
      durationMs: Date.now() - startedAt,
      errorCode: String(error?.code || error?.response?.status || 'UPLOAD_FAILED')
    })
    showToast('封面上传失败')
  }
}

const payload = publish => ({
  title: form.title.trim(),
  coverUrl: form.coverUrl || null,
  description: form.description.trim() || null,
  ingredients: form.ingredients.map(item => ({ name: item.name.trim(), amount: item.amount.trim() })),
  steps: form.steps.map(item => ({ content: item.content.trim(), imageUrl: item.imageUrl || null })),
  difficulty: Number(form.difficulty),
  cookingTime: form.cookingTime === '' ? null : Number(form.cookingTime),
  servings: form.servings === '' ? null : Number(form.servings),
  publish
})

const submit = async (publish) => {
  if (submitting.value) return
  if (!form.title.trim()) {
    showToast('请填写菜谱标题')
    return
  }
  const startedAt = Date.now()
  submitting.value = true
  const operation = isEdit.value ? 'update' : (publish ? 'create_publish' : 'create_draft')
  logUiEvent('recipe.editor.submit', {
    module: 'recipe_editor', operation, result: 'started', durationMs: 0,
    ingredientCount: form.ingredients.length, stepCount: form.steps.length
  })
  try {
    const result = isEdit.value
      ? await store.update(editId.value, payload(publish))
      : await store.create(payload(publish))
    if (isEdit.value && publish && store.detail?.status === 0) await store.publish(editId.value)
    draftStore.clear()
    dirty.value = false
    const createdId = typeof result === 'object' ? result?.id : result
    logUiEvent('recipe.editor.submit', {
      module: 'recipe_editor', operation, result: 'success', durationMs: Date.now() - startedAt,
      ingredientCount: form.ingredients.length, stepCount: form.steps.length
    })
    showToast(publish ? '菜谱已发布' : '草稿已保存')
    router.replace(isEdit.value ? `/recipes/${editId.value}` : (createdId ? `/recipes/${createdId}` : '/recipes'))
  } catch (error) {
    logUiEvent('recipe.editor.submit', {
      module: 'recipe_editor', operation, result: 'failed', durationMs: Date.now() - startedAt,
      errorCode: String(error?.code || error?.response?.status || 'SUBMIT_FAILED')
    })
    showToast('保存失败，本地草稿已保留')
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

watch(form, () => {
  if (!ready.value) return
  dirty.value = true
  draftStore.save(snapshot())
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
  if (coverPreview.value?.startsWith('blob:')) URL.revokeObjectURL?.(coverPreview.value)
})
</script>

<template>
  <main class="recipe-editor">
    <header class="editor-header">
      <button type="button" aria-label="返回" @click="router.back()"><van-icon name="arrow-left" /></button>
      <div><p>RECIPE STUDIO</p><h1>{{ isEdit ? '编辑菜谱' : '新建菜谱' }}</h1></div>
      <span aria-hidden="true" />
    </header>

    <aside v-if="restoreAvailable" class="restore-banner">
      <div><strong>发现本地草稿</strong><p>草稿按当前用户与菜谱 ID 隔离。</p></div>
      <button data-test="restore-draft" type="button" @click="restoreDraft">恢复</button>
    </aside>

    <form @submit.prevent>
      <section class="form-section basic-fields">
        <h2>基本信息</h2>
        <label>菜谱标题 <em>必填</em><input data-test="recipe-title" v-model="form.title" maxlength="100"></label>
        <label>菜谱简介<textarea v-model="form.description" rows="3" maxlength="1000" /></label>
        <div class="three-columns">
          <label>难度<select v-model="form.difficulty"><option :value="1">简单</option><option :value="2">中等</option><option :value="3">困难</option></select></label>
          <label>烹饪时间<input v-model="form.cookingTime" type="number" min="1" placeholder="分钟"></label>
          <label>份数<input v-model="form.servings" type="number" min="1" placeholder="人份"></label>
        </div>
        <div class="cover-editor">
          <div class="cover-frame">
            <img v-if="coverPreview" :src="coverPreview" alt="菜谱封面预览">
            <div v-else class="cover-placeholder cosmos-media cosmos-media--food" />
          </div>
          <label class="upload-button"><van-icon name="photograph" /> {{ coverStatus === 'uploading' ? '上传中' : '选择封面' }}<input type="file" accept="image/*" :disabled="coverStatus === 'uploading'" @change="chooseCover"></label>
          <p v-if="coverStatus === 'error'" class="field-error">封面上传失败，请重试。</p>
        </div>
      </section>

      <section class="form-section">
        <div class="section-heading"><div><h2>食材</h2><p>按实际使用顺序排列</p></div><button data-test="add-ingredient" type="button" @click="addIngredient"><van-icon name="plus" /> 添加</button></div>
        <div class="sortable-list">
          <article v-for="(ingredient, index) in form.ingredients" :key="index" class="sortable-row">
            <span class="drag-index">{{ index + 1 }}</span>
            <div class="row-fields">
              <input :data-test="`ingredient-name-${index}`" v-model="ingredient.name" :aria-label="`食材 ${index + 1} 名称`" placeholder="食材名称">
              <input v-model="ingredient.amount" :aria-label="`食材 ${index + 1} 用量`" placeholder="用量">
            </div>
            <div class="row-actions">
              <button :data-test="`ingredient-move-up-${index}`" type="button" aria-label="上移食材" :disabled="index === 0" @click="moveItem(form.ingredients, index, -1, 'ingredient')"><van-icon name="arrow-up" /></button>
              <button type="button" aria-label="下移食材" :disabled="index === form.ingredients.length - 1" @click="moveItem(form.ingredients, index, 1, 'ingredient')"><van-icon name="arrow-down" /></button>
              <button :data-test="`ingredient-remove-${index}`" type="button" aria-label="删除食材" @click="removeIngredient(index)"><van-icon name="delete-o" /></button>
            </div>
          </article>
        </div>
      </section>

      <section class="form-section">
        <div class="section-heading"><div><h2>制作步骤</h2><p>顺序将原样提交给后端</p></div><button type="button" @click="addStep"><van-icon name="plus" /> 添加</button></div>
        <div class="sortable-list">
          <article v-for="(step, index) in form.steps" :key="index" class="sortable-row step-row">
            <span class="drag-index">{{ index + 1 }}</span>
            <textarea v-model="step.content" :aria-label="`步骤 ${index + 1} 内容`" rows="3" placeholder="描述这个步骤" />
            <div class="row-actions">
              <button type="button" aria-label="上移步骤" :disabled="index === 0" @click="moveItem(form.steps, index, -1, 'step')"><van-icon name="arrow-up" /></button>
              <button type="button" aria-label="下移步骤" :disabled="index === form.steps.length - 1" @click="moveItem(form.steps, index, 1, 'step')"><van-icon name="arrow-down" /></button>
              <button :data-test="`step-remove-${index}`" type="button" aria-label="删除步骤" @click="removeStep(index)"><van-icon name="delete-o" /></button>
            </div>
          </article>
        </div>
      </section>

      <footer class="submit-actions">
        <button data-test="recipe-save-draft" type="button" :disabled="submitting" @click="submit(false)">{{ submitting ? '保存中…' : '保存草稿' }}</button>
        <button data-test="recipe-publish" type="button" :disabled="submitting" @click="submit(true)">{{ submitting ? '提交中…' : '发布菜谱' }}</button>
      </footer>
    </form>
  </main>
</template>

<style lang="scss" scoped>
.recipe-editor { min-height: 100vh; padding: $space-5 $page-padding 128px; color: $cosmos-text; background: $cosmos-bg; }
.editor-header { display: grid; grid-template-columns: 44px 1fr 44px; gap: $space-3; align-items: center; margin-bottom: $space-5; text-align: center; }
.editor-header > button { min-width: 44px; min-height: 44px; border: 1px solid $cosmos-border; border-radius: 50%; background: $cosmos-surface-raised; color: $cosmos-text; }
.editor-header p { color: $cosmos-secondary; font-size: $fs-caption; }
.editor-header h1 { margin-top: $space-1; font-size: $fs-title; }
.restore-banner { display: flex; gap: $space-4; align-items: center; justify-content: space-between; margin-bottom: $space-5; padding: $space-4; border: 1px solid $cosmos-secondary; border-radius: 8px; background: rgba(84,232,211,.08); }
.restore-banner p { margin-top: $space-1; color: $cosmos-text-muted; font-size: $fs-caption; }
.restore-banner button, .section-heading > button { min-height: 40px; padding: 0 $space-4; border: 1px solid $cosmos-secondary; border-radius: 6px; background: transparent; color: $cosmos-secondary; }
.form-section { padding: $space-5 0; border-top: 1px solid $cosmos-border; }
.form-section h2 { font-size: $fs-title; }
.basic-fields > label, .three-columns label { display: grid; gap: $space-2; margin-top: $space-4; color: $cosmos-text-muted; font-size: $fs-label; }
em { color: $cosmos-primary; font-style: normal; font-size: $fs-caption; }
input, select, textarea { width: 100%; min-height: 46px; padding: $space-3; border: 1px solid $cosmos-border; border-radius: 6px; outline: 0; background: $cosmos-surface-raised; color: $cosmos-text; font: inherit; }
textarea { resize: vertical; }
input:focus, select:focus, textarea:focus { border-color: $cosmos-secondary; }
.three-columns { display: grid; grid-template-columns: repeat(3,1fr); gap: $space-3; }
.cover-editor { margin-top: $space-5; }
.cover-frame { overflow: hidden; width: 100%; aspect-ratio: 16 / 9; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface-raised; }
.cover-frame img, .cover-placeholder { width: 100%; height: 100%; object-fit: cover; }
.upload-button { display: inline-flex; min-height: 44px; gap: $space-2; align-items: center; margin-top: $space-3; padding: 0 $space-4; border: 1px solid $cosmos-secondary; border-radius: 6px; color: $cosmos-secondary; cursor: pointer; }
.upload-button input { display: none; }
.field-error { margin-top: $space-2; color: $color-error; font-size: $fs-caption; }
.section-heading { display: flex; gap: $space-3; align-items: center; justify-content: space-between; }
.section-heading p { margin-top: $space-1; color: $cosmos-text-muted; font-size: $fs-caption; }
.sortable-list { display: grid; gap: $space-3; margin-top: $space-4; }
.sortable-row { display: grid; grid-template-columns: 32px minmax(0,1fr) auto; gap: $space-3; align-items: center; padding: $space-3; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; }
.drag-index { display: grid; width: 30px; height: 30px; place-items: center; border: 1px solid $cosmos-secondary; border-radius: 50%; color: $cosmos-secondary; }
.row-fields { display: grid; grid-template-columns: minmax(0,2fr) minmax(90px,1fr); gap: $space-2; }
.row-actions { display: flex; gap: $space-1; }
.row-actions button { width: 40px; height: 40px; padding: 0; border: 1px solid $cosmos-border; border-radius: 50%; background: $cosmos-surface-raised; color: $cosmos-text; }
.row-actions button:last-child { color: $cosmos-primary; }
.row-actions button:disabled { opacity: .3; }
.step-row textarea { min-height: 88px; }
.submit-actions { position: fixed; z-index: 3; right: 0; bottom: 64px; left: 0; display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; padding: $space-3 $page-padding; border-top: 1px solid $cosmos-border; background: rgba(13,17,42,.94); backdrop-filter: blur(18px); }
.submit-actions button { min-height: 50px; border: 1px solid $cosmos-primary; border-radius: 6px; background: transparent; color: $cosmos-primary; font-weight: $fw-semibold; }
.submit-actions button:last-child { background: $cosmos-primary; color: #fff; }
.submit-actions button:disabled { opacity: .5; }
@media (min-width: 760px) { .recipe-editor { max-width: 820px; margin: 0 auto; } .submit-actions { right: 50%; left: 50%; width: 820px; transform: translateX(-50%); } }
@media (max-width: 600px) { .three-columns { grid-template-columns: 1fr; } .sortable-row { grid-template-columns: 30px minmax(0,1fr); } .row-fields, .step-row textarea { grid-column: 2; } .row-fields { grid-template-columns: 1fr; } .row-actions { grid-column: 2; justify-content: flex-end; } }
</style>
