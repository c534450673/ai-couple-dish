<template>
  <div class="settings-page">
    <van-nav-bar title="设置" />

    <!-- 用户信息 -->
    <div class="user-section card">
      <!-- 骨架屏 -->
      <div v-if="isLoading" class="user-info skeleton-user">
        <div class="skeleton-avatar"></div>
        <div class="skeleton-detail">
          <div class="skeleton-name"></div>
          <div class="skeleton-code"></div>
        </div>
      </div>
      <div v-else class="user-info" @click="showEditDialog = true">
        <img :src="userInfo?.avatarUrl || defaultAvatar" class="avatar" />
        <div class="user-detail">
          <div class="user-name">{{ userInfo?.nickName || '未设置昵称' }}</div>
          <div class="user-code">情侣码: {{ coupleInfo?.coupleCode || '未绑定' }}</div>
        </div>
        <van-icon name="arrow" color="#ccc" />
      </div>
    </div>

    <!-- 设置列表 -->
    <van-cell-group inset>
      <van-cell title="修改昵称" is-link @click="showEditDialog = true" />
      <van-cell title="修改头像" is-link @click="handleChangeAvatar" />
      <van-cell title="修改手机号" is-link @click="showPhoneDialog = true" />
      <van-cell title="口味偏好" is-link @click="showTasteDialog = true" />
      <van-cell title="忌口设置" is-link @click="showDietDialog = true" />
    </van-cell-group>

    <van-cell-group inset title="情侣设置">
      <van-cell title="TA的信息" is-link :value="coupleInfo?.partnerName || '未绑定'" />
      <van-cell title="恋爱日期" is-link :value="coupleInfo?.startDate || '未设置'" @click="showDateDialog = true" />
      <van-cell title="解除绑定" is-link @click="handleUnbind" />
    </van-cell-group>

    <van-cell-group inset title="其他设置">
      <van-cell title="消息通知" is-link>
        <template #right-icon>
          <van-switch v-model="notifyEnabled" size="20" />
        </template>
      </van-cell>
      <van-cell title="隐私政策" is-link url="/privacy" />
      <van-cell title="用户协议" is-link url="/agreement" />
      <van-cell title="关于我们" is-link url="/about" />
    </van-cell-group>

    <div class="logout-section">
      <van-button block type="default" @click="handleLogout">退出登录</van-button>
    </div>

    <van-dialog v-model:show="showEditDialog" title="修改信息" show-cancel-button @confirm="handleSaveEdit">
      <van-field v-model="editForm.nickName" label="昵称" placeholder="请输入昵称" />
      <div class="avatar-upload">
        <van-uploader :after-read="onAvatarRead" :max-count="1">
          <img v-if="editForm.avatarUrl" :src="editForm.avatarUrl" class="avatar-preview" />
          <van-icon v-else name="photograph" size="32" color="#999" />
        </van-uploader>
      </div>
    </van-dialog>

    <van-dialog v-model:show="showPhoneDialog" title="修改手机号" show-cancel-button @confirm="handleSavePhone">
      <van-field v-model="phoneForm.phone" type="tel" label="手机号" placeholder="请输入手机号" />
      <div class="verify-code">
        <van-field v-model="phoneForm.verifyCode" type="digit" label="验证码" placeholder="请输入验证码" />
        <van-button size="small" type="primary" :disabled="countdown > 0" @click="sendVerifyCode">
          {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
        </van-button>
      </div>
    </van-dialog>

    <van-tabbar route>
      <van-tabbar-item to="/home" icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/menu" icon="shop-o">餐厅</van-tabbar-item>
      <van-tabbar-item to="/feed" icon="gift-o">投喂</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="setting-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { useUserStore } from '@/stores/user'
import { userApi, uploadApi, coupleApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()

const defaultAvatar = 'https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg'
const notifyEnabled = ref(true)
const isLoading = ref(true)
const showEditDialog = ref(false)
const showPhoneDialog = ref(false)
const showDateDialog = ref(false)
const showTasteDialog = ref(false)
const showDietDialog = ref(false)
const countdown = ref(0)

const editForm = ref({ nickName: '', avatarUrl: '' })
const phoneForm = ref({ phone: '', verifyCode: '' })

let countdownTimer = null

const userInfo = computed(() => userStore.userInfo)
const coupleInfo = computed(() => userStore.coupleInfo)

const handleLogout = async () => {
  try {
    await showConfirmDialog({ title: '确认退出', message: '确定要退出登录吗？' })
    userStore.logout()
    router.replace('/login')
  } catch (error) {
    // 用户取消
  }
}

const handleSaveEdit = async () => {
  try {
    await userApi.updateUserInfo(editForm.value)
    await userStore.updateUserInfo(editForm.value)
    showToast('保存成功')
  } catch (error) {
    showToast('保存失败')
  }
}

const onAvatarRead = async (file) => {
  try {
    const res = await uploadApi.uploadImage(file.file)
    editForm.value.avatarUrl = res.data.url
  } catch (error) {
    showToast('上传失败')
  }
}

const sendVerifyCode = async () => {
  if (!phoneForm.value.phone || phoneForm.value.phone.length !== 11) {
    showToast('请输入正确的手机号')
    return
  }

  try {
    await userApi.sendVerifyCode(phoneForm.value.phone)
    showToast('验证码已发送')
    countdown.value = 60
    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(countdownTimer)
    }, 1000)
  } catch (error) {
    showToast('发送失败')
  }
}

const handleSavePhone = async () => {
  showToast('手机号修改开发中')
}

const handleChangeAvatar = () => {
  showEditDialog.value = true
}

const handleUnbind = async () => {
  try {
    await showConfirmDialog({ title: '确认解除', message: '确定要解除情侣绑定吗？' })
    await coupleApi.applyUnbind({ coupleId: coupleInfo.value.id })
    showToast('已申请解绑，等待对方确认')
    // 刷新情侣信息，不要直接登出
    await userStore.getCoupleInfo()
  } catch (error) {
    if (error !== 'cancel') showToast('操作失败')
  }
}

onMounted(() => {
  editForm.value = {
    nickName: userInfo.value?.nickName || '',
    avatarUrl: userInfo.value?.avatarUrl || ''
  }
  // 延迟关闭骨架屏，让用户看到加载效果
  setTimeout(() => {
    isLoading.value = false
  }, 300)
})
</script>

<style lang="scss" scoped>
.settings-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: 70px;
}

.user-section {
  margin: 12px 16px;
  padding: 16px;

  .user-info {
    display: flex;
    align-items: center;

    .avatar {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      margin-right: 12px;
    }

    .user-detail {
      flex: 1;

      .user-name {
        font-size: 16px;
        font-weight: 600;
        color: #333;
      }

      .user-code {
        font-size: 12px;
        color: #999;
        margin-top: 4px;
      }
    }
  }
}

.logout-section {
  padding: 24px 16px;
  margin-top: 24px;

  .van-button {
    border-radius: 24px;
  }
}

.avatar-upload {
  display: flex;
  justify-content: center;
  padding: 20px;

  .avatar-preview {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
  }
}

.verify-code {
  display: flex;
  align-items: center;
  padding: 0 16px;

  :deep(.van-field) {
    flex: 1;
  }
}

// 骨架屏样式
.skeleton-user {
  display: flex;
  align-items: center;

  .skeleton-avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    margin-right: 12px;
  }

  .skeleton-detail {
    flex: 1;

    .skeleton-name {
      width: 100px;
      height: 16px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
      margin-bottom: 8px;
    }

    .skeleton-code {
      width: 120px;
      height: 12px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: 4px;
    }
  }
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
