<template>
  <div class="menu-add-page">
    <van-nav-bar
      title="添加餐厅"
      left-text="返回"
      left-arrow
      @click-left="$router.back()"
    />

    <div class="form-content">
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
            @click="$router.push('/location-picker')"
            readonly
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
          <div class="section-title">用餐状态</div>
          <van-radio-group v-model="form.status" direction="horizontal">
            <van-radio name="0">想去</van-radio>
            <van-radio name="1">去过</van-radio>
            <van-radio name="2">种草</van-radio>
          </van-radio-group>
        </div>

        <div class="form-section">
          <div class="section-title">上传照片</div>
          <van-uploader
            v-model="fileList"
            :max-count="9"
            :after-read="afterRead"
            @delete="onDelete"
            multiple
          />
        </div>

        <div class="form-actions">
          <van-button block type="primary" native-type="submit" :loading="submitting">
            保存
          </van-button>
        </div>
      </van-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { menuApi, uploadApi } from '@/api'

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

<style lang="scss" scoped>
.menu-add-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.form-content {
  padding: 16px 0;
}

.form-section {
  padding: 16px;
  background: #fff;
  margin-top: 12px;

  .section-title {
    font-size: 14px;
    color: #666;
    margin-bottom: 12px;
  }
}

.form-actions {
  padding: 24px 16px;

  .van-button {
    border-radius: 24px;
    background: linear-gradient(135deg, #ff6b9d 0%, #ff4757 100%);
    border: none;
  }
}
</style>
