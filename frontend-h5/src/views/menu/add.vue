<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { menuApi, uploadApi } from '@/api'
import { generateForm } from '@/api/ai'

const router = useRouter()

const form = ref({
  restaurantName: '',
  location: '',
  latitude: '',
  longitude: '',
  dishName: '',
  price: '',
  note: '',
  status: '0'
})

const fileList = ref([])
const submitting = ref(false)
const aiLoading = ref(false)
const aiPrompt = ref('')
const showAiDialog = ref(false)
const uploadedUrls = ref([])

const afterRead = async (file) => {
  file.status = 'uploading'
  file.message = '上传中...'

  try {
    const res = await uploadApi.uploadImage(file.file)
    file.url = res.data.url
    file.status = 'done'
    uploadedUrls.value.push(res.data.url)
  } catch (error) {
    file.status = 'failed'
    file.message = '上传失败'
    showToast('图片上传失败')
  }
}

const onDelete = (file) => {
  const index = uploadedUrls.value.findIndex(url => url === file.url)
  if (index > -1) {
    uploadedUrls.value.splice(index, 1)
  }
}

const handleAiFill = async () => {
  if (!aiPrompt.value.trim()) {
    showToast('请先描述餐厅或用餐经历')
    return
  }
  aiLoading.value = true
  showLoadingToast({ message: 'AI 生成中...', forbidClick: true })
  try {
    const res = await generateForm('menu', aiPrompt.value.trim())
    closeToast()
    if (res.code === 200 && res.data?.data) {
      const d = res.data.data
      if (d.restaurantName) form.value.restaurantName = String(d.restaurantName)
      if (d.dishName) form.value.dishName = String(d.dishName)
      if (d.location) form.value.location = String(d.location)
      if (d.price != null) form.value.price = String(d.price)
      if (d.note) form.value.note = String(d.note)
      if (d.status != null) form.value.status = String(d.status)
      showAiDialog.value = false
      showToast('已填入表单，请核对后保存')
    } else {
      showToast(res.message || 'AI 生成失败')
    }
  } catch {
    closeToast()
    showToast('AI 生成失败')
  } finally {
    aiLoading.value = false
  }
}

const handleSubmit = async () => {
  if (!form.value.restaurantName) {
    showToast('请输入餐厅名称')
    return
  }

  submitting.value = true
  showLoadingToast({ message: '保存中...', forbidClick: true })

  try {
    const data = {
      ...form.value,
      photoUrls: uploadedUrls.value.join(',')
    }

    await menuApi.addMenu(data)
    closeToast()
    showToast('添加成功')
    router.back()
  } catch (error) {
    closeToast()
    showToast('保存失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="menu-add-page">
    <header class="page-topbar">
      <button
        class="back"
        @click="$router.back()"
      >
        <van-icon
          name="arrow-left"
          size="20"
        />
      </button>
      <span class="title">添加餐厅</span>
      <i class="placeholder" />
    </header>

    <div class="form-content">
      <div class="ai-fill-bar">
        <van-button
          size="small"
          round
          plain
          type="primary"
          icon="fire-o"
          @click="showAiDialog = true"
        >
          AI 帮填
        </van-button>
      </div>

      <van-form @submit="handleSubmit">
        <van-cell-group inset>
          <van-field
            v-model="form.restaurantName"
            name="restaurantName"
            label="餐厅名称"
            placeholder="请输入餐厅名称"
            :rules="[{ required: true, message: '请输入餐厅名称' }]"
          />

          <van-field
            v-model="form.location"
            name="location"
            label="位置"
            placeholder="请输入位置"
            readonly
            @click="$router.push('/map')"
          >
            <template #button>
              <van-icon name="location-o" />
            </template>
          </van-field>

          <van-field
            v-model="form.dishName"
            name="dishName"
            label="推荐菜品"
            placeholder="请输入推荐菜品"
          />

          <van-field
            v-model="form.price"
            name="price"
            label="人均价格"
            placeholder="如: 100元"
            type="text"
          />

          <van-field
            v-model="form.note"
            name="note"
            label="私密笔记"
            type="textarea"
            placeholder="记录你们的专属回忆..."
            rows="3"
            autosize
          />
        </van-cell-group>

        <div class="form-section">
          <div class="section-title">
            用餐状态
          </div>
          <van-radio-group
            v-model="form.status"
            direction="horizontal"
          >
            <van-radio name="0">
              想去
            </van-radio>
            <van-radio name="1">
              去过
            </van-radio>
            <van-radio name="2">
              种草
            </van-radio>
          </van-radio-group>
        </div>

        <div class="form-section">
          <div class="section-title">
            上传照片
          </div>
          <van-uploader
            v-model="fileList"
            :max-count="9"
            :after-read="afterRead"
            multiple
            @delete="onDelete"
          />
        </div>

        <div class="form-actions">
          <van-button
            block
            round
            type="primary"
            native-type="submit"
            :loading="submitting"
          >
            保存
          </van-button>
        </div>
      </van-form>
    </div>

    <van-dialog
      v-model:show="showAiDialog"
      title="AI 帮填菜单"
      show-cancel-button
      confirm-button-text="生成"
      :before-close="(action) => action !== 'confirm' || !aiLoading"
      @confirm="handleAiFill"
    >
      <van-field
        v-model="aiPrompt"
        type="textarea"
        rows="3"
        placeholder="描述一下，例如：昨天和 TA 去了海底捞，点了番茄锅和毛肚，人均120，很满意"
        style="padding: 12px 16px"
      />
    </van-dialog>
  </div>
</template>

<style lang="scss" scoped>
.menu-add-page {
  min-height: 100vh;
  background: $color-background;
}

.page-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $page-padding;
  @include glass(0.7);

  .back,
  .placeholder { width: 32px; }
  .back {
    border: none;
    background: transparent;
    color: $color-on-surface;
    display: flex;
    align-items: center;
    cursor: pointer;
  }
  .title { font-size: $fs-title; font-weight: $fw-semibold; color: $color-on-surface; }
}

.form-content {
  padding: $space-4 0 $space-8;
}

.ai-fill-bar {
  padding: 0 $page-padding $space-3;
  display: flex;
  justify-content: flex-end;
}

.form-section {
  margin: $space-4 $page-padding 0;
  padding: $space-5;
  background: $color-surface-lowest;
  border-radius: $radius-lg;
  box-shadow: $shadow-card;

  .section-title {
    font-size: $fs-caption;
    color: $color-on-surface-variant;
    margin-bottom: $space-4;
  }

  :deep(.van-radio) { margin-right: $space-5; }
}

.form-actions {
  padding: $space-8 $page-padding 0;
}
</style>
