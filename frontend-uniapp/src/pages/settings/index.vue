<template>
  <view class="settings-page">
    <!-- 用户信息 -->
    <view class="user-section" @click="showEditDialog = true">
      <image :src="userInfo?.avatarUrl || defaultAvatar" class="avatar" mode="aspectFill" />
      <view class="user-detail">
        <text class="user-name">{{ userInfo?.nickName || '未设置昵称' }}</text>
        <text class="user-code">情侣码: {{ coupleInfo?.coupleCode || '未绑定' }}</text>
      </view>
      <text class="arrow">›</text>
    </view>

    <!-- 设置列表 -->
    <view class="settings-group">
      <view class="settings-item" @click="showEditDialog = true">
        <text class="item-icon">👤</text>
        <text class="item-label">修改昵称</text>
        <text class="arrow">›</text>
      </view>
      <view class="settings-item" @click="handleChangeAvatar">
        <text class="item-icon">📷</text>
        <text class="item-label">修改头像</text>
        <text class="arrow">›</text>
      </view>
      <view class="settings-item" @click="showPhoneDialog = true">
        <text class="item-icon">📱</text>
        <text class="item-label">修改手机号</text>
        <text class="arrow">›</text>
      </view>
    </view>

    <view class="settings-group">
      <view class="settings-item">
        <text class="item-icon">👥</text>
        <text class="item-label">TA的信息</text>
        <text class="item-value">{{ coupleInfo?.partnerName || '未绑定' }}</text>
      </view>
      <view class="settings-item">
        <text class="item-icon">📅</text>
        <text class="item-label">恋爱日期</text>
        <text class="item-value">{{ coupleInfo?.startDate || '未设置' }}</text>
      </view>
      <view class="settings-item" @click="handleUnbind">
        <text class="item-icon">💔</text>
        <text class="item-label">解除绑定</text>
        <text class="arrow text-red">›</text>
      </view>
    </view>

    <view class="settings-group">
      <view class="settings-item">
        <text class="item-icon">🔔</text>
        <text class="item-label">消息通知</text>
        <switch :checked="notifyEnabled" @change="onNotifyChange" color="#ff4757" />
      </view>
      <view class="settings-item" @click="goPage('/pages/privacy')">
        <text class="item-icon">📜</text>
        <text class="item-label">隐私政策</text>
        <text class="arrow">›</text>
      </view>
      <view class="settings-item" @click="goPage('/pages/agreement')">
        <text class="item-icon">📝</text>
        <text class="item-label">用户协议</text>
        <text class="arrow">›</text>
      </view>
    </view>

    <view class="logout-section">
      <button class="logout-btn" @click="handleLogout">退出登录</button>
    </view>

    <!-- 修改信息弹窗 -->
    <view class="dialog" v-if="showEditDialog" @click="showEditDialog = false">
      <view class="dialog-content" @click.stop>
        <view class="dialog-header">
          <text>修改信息</text>
          <text class="close" @click="showEditDialog = false">✕</text>
        </view>
        <view class="avatar-upload" @click="handleChangeAvatar">
          <image v-if="editForm.avatarUrl" :src="editForm.avatarUrl" class="avatar-preview" />
          <text v-else class="upload-icon">📷</text>
        </view>
        <input v-model="editForm.nickName" class="nickname-input" placeholder="请输入昵称" />
        <button class="save-btn" @click="handleSaveEdit">保存</button>
      </view>
    </view>

    <!-- 修改手机号弹窗 -->
    <view class="dialog" v-if="showPhoneDialog" @click="showPhoneDialog = false">
      <view class="dialog-content" @click.stop>
        <view class="dialog-header">
          <text>修改手机号</text>
          <text class="close" @click="showPhoneDialog = false">✕</text>
        </view>
        <input v-model="phoneForm.phone" class="phone-input" type="tel" placeholder="请输入手机号" maxlength="11" />
        <view class="verify-code-row">
          <input v-model="phoneForm.verifyCode" class="code-input" type="digit" placeholder="请输入验证码" maxlength="6" />
          <button class="send-code-btn" @click="sendVerifyCode">
            {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
          </button>
        </view>
        <button class="save-btn" @click="handleSavePhone">保存</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { userApi, coupleApi, uploadApi } from '@/api'

const userStore = useUserStore()

const defaultAvatar = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4Fbnqp6Hf4nNOvcriabISB5JpLxI1N0icm4qYiag/0'
const notifyEnabled = ref(true)
const showEditDialog = ref(false)
const showPhoneDialog = ref(false)
const countdown = ref(0)

const editForm = ref({ nickName: '', avatarUrl: '' })
const phoneForm = ref({ phone: '', verifyCode: '' })

let countdownTimer = null

const userInfo = computed(() => userStore.userInfo)
const coupleInfo = computed(() => userStore.coupleInfo)

const goPage = (url) => uni.navigateTo({ url })

const handleLogout = async () => {
  const res = await uni.showModal({
    title: '确认退出',
    content: '确定要退出登录吗？'
  })

  if (res.confirm) {
    userStore.logout()
    uni.reLaunch({ url: '/pages/index/index' })
  }
}

const handleSaveEdit = async () => {
  try {
    await userStore.updateUserInfo(editForm.value)
    uni.showToast({ title: '保存成功', icon: 'success' })
    showEditDialog.value = false
  } catch (error) {
    uni.showToast({ title: '保存失败', icon: 'none' })
  }
}

const handleChangeAvatar = async () => {
  uni.chooseImage({
    count: 1,
    success: async (res) => {
      const tempFilePath = res.tempFilePaths[0]
      try {
        const uploadRes = await uploadApi.uploadImage(tempFilePath)
        editForm.value.avatarUrl = uploadRes.data.url
        uni.showToast({ title: '上传成功', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: '上传失败', icon: 'none' })
      }
    }
  })
}

const sendVerifyCode = async () => {
  if (countdown.value > 0) return
  if (!phoneForm.value.phone || phoneForm.value.phone.length !== 11) {
    uni.showToast({ title: '请输入正确的手机号', icon: 'none' })
    return
  }

  try {
    await userApi.sendVerifyCode(phoneForm.value.phone)
    uni.showToast({ title: '验证码已发送', icon: 'success' })
    countdown.value = 60
    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(countdownTimer)
    }, 1000)
  } catch (error) {
    uni.showToast({ title: '发送失败', icon: 'none' })
  }
}

const handleSavePhone = () => {
  uni.showToast({ title: '手机号修改开发中', icon: 'none' })
}

const handleUnbind = async () => {
  const res = await uni.showModal({
    title: '确认解除',
    content: '确定要解除情侣绑定吗？'
  })

  if (res.confirm) {
    try {
      await coupleApi.applyUnbind({ coupleId: coupleInfo.value.id })
      uni.showToast({ title: '已申请解绑', icon: 'success' })
      userStore.logout()
      uni.reLaunch({ url: '/pages/index/index' })
    } catch (error) {
      uni.showToast({ title: '操作失败', icon: 'none' })
    }
  }
}

const onNotifyChange = (e) => {
  notifyEnabled.value = e.detail.value
}

onMounted(() => {
  editForm.value = {
    nickName: userInfo.value?.nickName || '',
    avatarUrl: userInfo.value?.avatarUrl || ''
  }
})
</script>

<style lang="scss" scoped>
.settings-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 40rpx;
}

.user-section {
  display: flex;
  align-items: center;
  margin: 24rpx;
  padding: 32rpx;
  background: #fff;
  border-radius: 24rpx;

  .avatar {
    width: 112rpx;
    height: 112rpx;
    border-radius: 50%;
    margin-right: 24rpx;
  }

  .user-detail {
    flex: 1;
    display: flex;
    flex-direction: column;

    .user-name {
      font-size: 32rpx;
      font-weight: 600;
      color: #333;
    }

    .user-code {
      font-size: 24rpx;
      color: #999;
      margin-top: 8rpx;
    }
  }

  .arrow {
    font-size: 40rpx;
    color: #ccc;
  }
}

.settings-group {
  margin: 0 24rpx 24rpx;
  background: #fff;
  border-radius: 24rpx;
  overflow: hidden;

  .settings-item {
    display: flex;
    align-items: center;
    padding: 32rpx;
    border-bottom: 1px solid #f5f5f5;

    &:last-child {
      border-bottom: none;
    }

    .item-icon {
      font-size: 40rpx;
      margin-right: 20rpx;
    }

    .item-label {
      flex: 1;
      font-size: 28rpx;
      color: #333;
    }

    .item-value {
      font-size: 28rpx;
      color: #999;
    }

    .arrow {
      font-size: 36rpx;
      color: #ccc;
      margin-left: 16rpx;
    }

    .text-red {
      color: #ff4757;
    }
  }
}

.logout-section {
  margin: 60rpx 24rpx 0;

  .logout-btn {
    width: 100%;
    height: 96rpx;
    background: #fff;
    color: #ff4757;
    border-radius: 48rpx;
    font-size: 32rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
  }
}

.dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;

  .dialog-content {
    width: 600rpx;
    background: #fff;
    border-radius: 24rpx;
    padding: 40rpx;

    .dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 40rpx;

      text {
        font-size: 36rpx;
        font-weight: 600;
      }

      .close {
        font-size: 40rpx;
        color: #999;
      }
    }

    .avatar-upload {
      width: 160rpx;
      height: 160rpx;
      background: #f5f5f5;
      border-radius: 50%;
      margin: 0 auto 30rpx;
      display: flex;
      align-items: center;
      justify-content: center;

      .avatar-preview {
        width: 100%;
        height: 100%;
        border-radius: 50%;
      }

      .upload-icon {
        font-size: 60rpx;
      }
    }

    .nickname-input,
    .phone-input {
      width: 100%;
      height: 96rpx;
      background: #f5f5f5;
      border-radius: 16rpx;
      padding: 0 30rpx;
      font-size: 28rpx;
      box-sizing: border-box;
      margin-bottom: 20rpx;
    }

    .verify-code-row {
      display: flex;
      gap: 20rpx;

      .code-input {
        flex: 1;
        height: 96rpx;
        background: #f5f5f5;
        border-radius: 16rpx;
        padding: 0 30rpx;
        font-size: 28rpx;
      }

      .send-code-btn {
        width: 240rpx;
        height: 96rpx;
        background: linear-gradient(135deg, #ff6b9d, #ff4757);
        color: #fff;
        border-radius: 16rpx;
        font-size: 26rpx;
        display: flex;
        align-items: center;
        justify-content: center;
        border: none;
      }
    }

    .save-btn {
      width: 100%;
      height: 96rpx;
      background: linear-gradient(135deg, #ff6b9d, #ff4757);
      color: #fff;
      border-radius: 48rpx;
      font-size: 32rpx;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-top: 30rpx;
      border: none;
    }
  }
}
</style>
