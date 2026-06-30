<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { useUserStore } from '@/stores/user'
import { userApi, uploadApi, coupleApi } from '@/api'
import AppTabbar from '@/components/AppTabbar.vue'

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
  setTimeout(() => {
    isLoading.value = false
  }, 300)
})
</script>

<template>
  <div class="settings-page">
    <header class="settings-topbar">
      <h1 class="page-title">
        我的
      </h1>
    </header>

    <div class="settings-body">
      <!-- 用户信息 -->
      <div class="user-card">
        <i class="deco" />
        <div
          v-if="isLoading"
          class="user-info skeleton"
        >
          <div class="sk sk-avatar" />
          <div class="detail">
            <div class="sk sk-line sk-name" />
            <div class="sk sk-line sk-code" />
          </div>
        </div>
        <div
          v-else
          class="user-info"
          @click="showEditDialog = true"
        >
          <img
            :src="userInfo?.avatarUrl || defaultAvatar"
            class="avatar"
          >
          <div class="detail">
            <div class="name">
              {{ userInfo?.nickName || '未设置昵称' }}
            </div>
            <div class="code">
              <van-icon
                name="friends-o"
                size="13"
              />
              {{ coupleInfo?.coupleNickname || coupleInfo?.partnerName ? (coupleInfo?.coupleNickname || '已绑定 TA') : ('情侣码: ' + (coupleInfo?.coupleCode || '未绑定')) }}
            </div>
          </div>
          <van-icon
            name="arrow"
            color="#d6c1c5"
          />
        </div>
      </div>

      <!-- 设置列表 -->
      <van-cell-group inset>
        <van-cell
          title="修改昵称"
          is-link
          @click="showEditDialog = true"
        />
        <van-cell
          title="修改头像"
          is-link
          @click="handleChangeAvatar"
        />
        <van-cell
          title="修改手机号"
          is-link
          @click="showPhoneDialog = true"
        />
        <van-cell
          title="口味偏好"
          is-link
          @click="showTasteDialog = true"
        />
        <van-cell
          title="忌口设置"
          is-link
          @click="showDietDialog = true"
        />
      </van-cell-group>

      <div class="group-title">
        情侣设置
      </div>
      <van-cell-group inset>
        <van-cell
          title="TA的信息"
          is-link
          :value="coupleInfo?.partnerName || '未绑定'"
        />
        <van-cell
          title="恋爱日期"
          is-link
          :value="coupleInfo?.startDate || '未设置'"
          @click="showDateDialog = true"
        />
        <van-cell
          title="解除绑定"
          is-link
          @click="handleUnbind"
        />
      </van-cell-group>

      <div class="group-title">
        其他设置
      </div>
      <van-cell-group inset>
        <van-cell title="消息通知">
          <template #right-icon>
            <van-switch
              v-model="notifyEnabled"
              size="20"
            />
          </template>
        </van-cell>
        <van-cell
          title="隐私政策"
          is-link
          url="/privacy"
        />
        <van-cell
          title="用户协议"
          is-link
          url="/agreement"
        />
        <van-cell
          title="关于我们"
          is-link
          url="/about"
        />
      </van-cell-group>

      <div class="logout-section">
        <button
          class="logout-btn"
          @click="handleLogout"
        >
          退出登录
        </button>
      </div>
    </div>

    <van-dialog
      v-model:show="showEditDialog"
      title="修改信息"
      show-cancel-button
      @confirm="handleSaveEdit"
    >
      <van-field
        v-model="editForm.nickName"
        label="昵称"
        placeholder="请输入昵称"
      />
      <div class="avatar-upload">
        <van-uploader
          :after-read="onAvatarRead"
          :max-count="1"
        >
          <img
            v-if="editForm.avatarUrl"
            :src="editForm.avatarUrl"
            class="avatar-preview"
          >
          <van-icon
            v-else
            name="photograph"
            size="32"
            color="#999"
          />
        </van-uploader>
      </div>
    </van-dialog>

    <van-dialog
      v-model:show="showPhoneDialog"
      title="修改手机号"
      show-cancel-button
      @confirm="handleSavePhone"
    >
      <van-field
        v-model="phoneForm.phone"
        type="tel"
        label="手机号"
        placeholder="请输入手机号"
      />
      <div class="verify-code">
        <van-field
          v-model="phoneForm.verifyCode"
          type="digit"
          label="验证码"
          placeholder="请输入验证码"
        />
        <van-button
          size="small"
          type="primary"
          :disabled="countdown > 0"
          @click="sendVerifyCode"
        >
          {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
        </van-button>
      </div>
    </van-dialog>

    <app-tabbar />
  </div>
</template>

<style lang="scss" scoped>
.settings-page {
  min-height: 100vh;
  background: $color-background;
  padding-bottom: 96px;
}

.settings-topbar {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  @include glass(0.7);

  .page-title { font-size: $fs-title; font-weight: $fw-semibold; color: $color-on-surface; }
}

.settings-body {
  padding: $space-4 0 0;
}

.user-card {
  position: relative;
  overflow: hidden;
  margin: 0 $page-padding $space-5;
  @include card($radius-xl, $space-5);

  .deco {
    position: absolute;
    top: -30px;
    right: -30px;
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: $gradient-peach;
    opacity: 0.25;
  }

  .user-info {
    position: relative;
    display: flex;
    align-items: center;

    .avatar {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      object-fit: cover;
      margin-right: $space-4;
      border: 2px solid $color-surface-lowest;
      box-shadow: $shadow-card;
    }

    .detail {
      flex: 1;
      .name { font-size: $fs-title; font-weight: $fw-semibold; color: $color-on-surface; }
      .code {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: $fs-caption;
        color: $color-on-surface-variant;
        margin-top: $space-1;
      }
    }
  }
}

.group-title {
  font-size: $fs-caption;
  color: $color-on-surface-variant;
  padding: $space-4 $page-padding $space-2;
}

.logout-section {
  padding: $space-8 $page-padding;

  .logout-btn {
    width: 100%;
    height: 48px;
    border: 1px solid $color-outline-variant;
    border-radius: $radius-pill;
    background: $color-surface-lowest;
    color: $color-error;
    font-size: $fs-body;
    font-weight: $fw-medium;
    cursor: pointer;

    &:active { background: $color-error-container; }
  }
}

.avatar-upload {
  display: flex;
  justify-content: center;
  padding: 20px;

  .avatar-preview { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; }
}

.verify-code {
  display: flex;
  align-items: center;
  padding: 0 $space-4 $space-2;
  gap: $space-2;

  :deep(.van-field) { flex: 1; }
}

// 骨架屏
.skeleton {
  .sk {
    background: linear-gradient(90deg, $color-surface-high 25%, $color-surface-low 50%, $color-surface-high 75%);
    background-size: 200% 100%;
    animation: sk-loading 1.5s infinite;
  }
  .sk-avatar { width: 60px; height: 60px; border-radius: 50%; margin-right: $space-4; }
  .detail { flex: 1; }
  .sk-line { border-radius: 4px; }
  .sk-name { width: 100px; height: 16px; margin-bottom: 8px; }
  .sk-code { width: 140px; height: 12px; }
}

@keyframes sk-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
