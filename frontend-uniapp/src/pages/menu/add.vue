<template>
  <view class="menu-add-page">
    <view class="form-content">
      <view class="form-item">
        <text class="label">餐厅名称 *</text>
        <input v-model="form.restaurantName" class="input" placeholder="请输入餐厅名称" />
      </view>

      <view class="form-item">
        <text class="label">位置</text>
        <input v-model="form.location" class="input" placeholder="请输入位置" />
      </view>

      <view class="form-item">
        <text class="label">推荐菜品</text>
        <input v-model="form.dishName" class="input" placeholder="请输入推荐菜品" />
      </view>

      <view class="form-item">
        <text class="label">人均价格</text>
        <input v-model="form.price" class="input" placeholder="如: 100元" />
      </view>

      <view class="form-item">
        <text class="label">用餐状态</text>
        <view class="status-select">
          <view
            v-for="status in statusList"
            :key="status.value"
            class="status-item"
            :class="{ active: form.status === status.value }"
            @click="form.status = status.value"
          >
            {{ status.label }}
          </view>
        </view>
      </view>

      <view class="form-item">
        <text class="label">私密笔记</text>
        <textarea v-model="form.note" class="textarea" placeholder="记录你们的专属回忆..." />
      </view>

      <view class="form-item">
        <text class="label">上传照片</text>
        <view class="upload-list">
          <view v-for="(item, index) in fileList" :key="index" class="upload-item">
            <image :src="item.url" mode="aspectFill" />
            <view class="delete-btn" @click="removeImage(index)">✕</view>
          </view>
          <view class="upload-btn" @click="chooseImage" v-if="fileList.length < 9">
            <text>+</text>
          </view>
        </view>
      </view>

      <button class="submit-btn" :loading="submitting" @click="handleSubmit">保存</button>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { menuApi, uploadApi } from '@/api'

const form = ref({
  restaurantName: '',
  location: '',
  dishName: '',
  price: '',
  note: '',
  status: '0'
})

const statusList = [
  { label: '想去', value: '0' },
  { label: '去过', value: '1' },
  { label: '种草', value: '2' }
]

const fileList = ref([])
const submitting = ref(false)

const chooseImage = async () => {
  uni.chooseImage({
    count: 9 - fileList.value.length,
    success: async (res) => {
      for (const tempFilePath of res.tempFilePaths) {
        uni.showLoading({ title: '上传中...' })
        try {
          const uploadRes = await uploadApi.uploadImage(tempFilePath)
          fileList.value.push({ url: uploadRes.data.url })
        } catch (error) {
          uni.showToast({ title: '上传失败', icon: 'none' })
        } finally {
          uni.hideLoading()
        }
      }
    }
  })
}

const removeImage = (index) => {
  fileList.value.splice(index, 1)
}

const handleSubmit = async () => {
  if (!form.value.restaurantName) {
    uni.showToast({ title: '请输入餐厅名称', icon: 'none' })
    return
  }

  submitting.value = true
  uni.showLoading({ title: '保存中...', mask: true })
  try {
    const data = {
      ...form.value,
      photoUrls: fileList.value.map(f => f.url).join(',')
    }
    await menuApi.addMenu(data)
    uni.hideLoading()
    uni.showToast({ title: '添加成功', icon: 'success' })
    setTimeout(() => {
      uni.navigateBack()
    }, 1500)
  } catch (error) {
    uni.hideLoading()
    uni.showToast({ title: '保存失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss" scoped>
.menu-add-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 24rpx;
}

.form-content {
  .form-item {
    background: #fff;
    border-radius: 16rpx;
    padding: 30rpx;
    margin-bottom: 24rpx;

    .label {
      font-size: 28rpx;
      color: #666;
      margin-bottom: 16rpx;
      display: block;
    }

    .input {
      width: 100%;
      height: 80rpx;
      font-size: 28rpx;
    }

    .textarea {
      width: 100%;
      height: 160rpx;
      background: #f5f5f5;
      border-radius: 12rpx;
      padding: 20rpx;
      font-size: 28rpx;
      box-sizing: border-box;
    }
  }

  .status-select {
    display: flex;
    gap: 20rpx;

    .status-item {
      padding: 16rpx 40rpx;
      background: #f5f5f5;
      border-radius: 40rpx;
      font-size: 28rpx;
      color: #666;

      &.active {
        background: #fff0f3;
        color: #ff4757;
      }
    }
  }

  .upload-list {
    display: flex;
    flex-wrap: wrap;
    gap: 16rpx;

    .upload-item {
      width: 200rpx;
      height: 200rpx;
      border-radius: 12rpx;
      position: relative;

      image {
        width: 100%;
        height: 100%;
        border-radius: 12rpx;
      }

      .delete-btn {
        position: absolute;
        top: -16rpx;
        right: -16rpx;
        width: 40rpx;
        height: 40rpx;
        background: #ff4757;
        color: #fff;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24rpx;
      }
    }

    .upload-btn {
      width: 200rpx;
      height: 200rpx;
      background: #f5f5f5;
      border-radius: 12rpx;
      display: flex;
      align-items: center;
      justify-content: center;

      text {
        font-size: 60rpx;
        color: #999;
      }
    }
  }

  .submit-btn {
    width: 100%;
    height: 96rpx;
    background: linear-gradient(135deg, #ff6b9d, #ff4757);
    color: #fff;
    border-radius: 48rpx;
    font-size: 32rpx;
    margin-top: 40rpx;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style>
