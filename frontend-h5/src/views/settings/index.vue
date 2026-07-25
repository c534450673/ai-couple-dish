<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { coupleApi, uploadApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'
import { logUiEvent, normalizeUiErrorCode } from '@/composables/useStructuredLog'

const NOTIFICATION_PREFERENCE_KEY = 'couple-cosmos:notification-display'
const LEGAL_LINKS = [
  { label: '隐私政策', to: '/legal#privacy' },
  { label: '服务协议', to: '/legal#terms' },
  { label: '第三方服务', to: '/legal#third-party' },
  { label: '数据导出', to: '/legal#export' },
  { label: '账号删除', to: '/legal#deletion' },
  { label: '情侣数据', to: '/legal#couple-data' }
]
const MEMBER_LABELS = { 0: '免费', 1: '黄金', 2: '铂金' }

const router = useRouter()
const userStore = useUserStore()
const themeStore = useThemeStore()

const profileStatus = ref('loading')
const profileInfo = ref(null)
const profileError = ref('')
const editOpen = ref(false)
const editForm = ref({ nickName: '', avatarUrl: '' })
const isSaving = ref(false)
const isUploading = ref(false)
const isLoggingOut = ref(false)
const isUnbinding = ref(false)
const unboundVisible = ref(false)
const unbindRefreshWarning = ref(false)
const memberUnavailable = ref(false)
const notificationDisplayEnabled = ref(
  globalThis.localStorage?.getItem(NOTIFICATION_PREFERENCE_KEY) !== 'disabled'
)

const coupleInfo = computed(() => userStore.coupleInfo)
const memberLabel = computed(() => MEMBER_LABELS[profileInfo.value?.memberLevel] || '未知')
const canSaveProfile = computed(() => Boolean(editForm.value.nickName.trim()) && !isSaving.value && !isUploading.value)

const loadProfile = async () => {
  profileStatus.value = 'loading'
  profileError.value = ''
  if (!userStore.token && !globalThis.localStorage?.getItem('token')) {
    profileStatus.value = 'unauthorized'
    await router.replace('/login')
    return
  }

  try {
    const res = await userStore.fetchUserInfo()
    profileInfo.value = res.data
    profileStatus.value = 'success'
  } catch (error) {
    if (normalizeUiErrorCode(error) === '401') {
      profileStatus.value = 'unauthorized'
      await router.replace('/login')
      return
    }
    profileStatus.value = 'error'
    profileError.value = '暂时无法读取资料，请稍后重试'
  }
}

const openProfileEditor = () => {
  editForm.value = {
    nickName: profileInfo.value?.nickName || '',
    avatarUrl: profileInfo.value?.avatarUrl || ''
  }
  profileError.value = ''
  editOpen.value = true
}

const saveProfile = async () => {
  if (!canSaveProfile.value) return
  isSaving.value = true
  profileError.value = ''
  const payload = {
    nickName: editForm.value.nickName.trim(),
    avatarUrl: editForm.value.avatarUrl
  }
  try {
    await userStore.updateUserInfo(payload)
    profileInfo.value = { ...profileInfo.value, ...payload }
    editOpen.value = false
    showToast('资料已保存')
  } catch (error) {
    profileError.value = '保存失败，编辑内容已保留'
    showToast('保存失败，请重试')
  } finally {
    isSaving.value = false
  }
}

const uploadAvatar = async (event) => {
  const file = event.target?.files?.[0]
  if (!file || isUploading.value) return
  const startedAt = Date.now()
  isUploading.value = true
  logUiEvent('settings.avatar.upload', {
    module: 'settings', operation: 'avatar_upload', result: 'started', durationMs: 0,
    errorCode: 'NONE', itemCount: 1
  })
  try {
    const res = await uploadApi.uploadImage(file)
    editForm.value.avatarUrl = res.data.url
    logUiEvent('settings.avatar.upload', {
      module: 'settings', operation: 'avatar_upload', result: 'success',
      durationMs: Date.now() - startedAt, errorCode: 'NONE', itemCount: 1
    })
    showToast('头像已上传，请保存资料')
  } catch (error) {
    logUiEvent('settings.avatar.upload', {
      module: 'settings', operation: 'avatar_upload', result: 'error',
      durationMs: Date.now() - startedAt, errorCode: normalizeUiErrorCode(error), itemCount: 1
    })
    showToast('头像上传失败')
  } finally {
    isUploading.value = false
    event.target.value = ''
  }
}

const changeTheme = (theme) => {
  themeStore.setTheme(theme)
}

const changeNotificationPreference = (event) => {
  const startedAt = Date.now()
  notificationDisplayEnabled.value = event.target.checked
  const value = event.target.checked ? 'enabled' : 'disabled'
  globalThis.localStorage?.setItem(NOTIFICATION_PREFERENCE_KEY, value)
  logUiEvent('settings.notification.preference', {
    module: 'settings', operation: 'local_notification_display', result: 'success',
    durationMs: Date.now() - startedAt, errorCode: 'NONE', enabled: event.target.checked
  })
}

const showMemberUnavailable = () => {
  memberUnavailable.value = true
  logUiEvent('settings.member.view', {
    module: 'settings', operation: 'membership_entry', result: 'unavailable',
    durationMs: 0, errorCode: 'MEMBERSHIP_API_UNAVAILABLE'
  })
}

const applyUnbind = async () => {
  const startedAt = Date.now()
  unboundVisible.value = false
  unbindRefreshWarning.value = false
  if (!coupleInfo.value) {
    unboundVisible.value = true
    logUiEvent('settings.couple.unbind.apply', {
      module: 'settings', operation: 'unbind_apply', result: 'unbound',
      durationMs: 0, errorCode: 'COUPLE_NOT_BOUND'
    })
    return
  }

  logUiEvent('settings.couple.unbind.apply', {
    module: 'settings', operation: 'unbind_apply', result: 'started',
    durationMs: 0, errorCode: 'NONE'
  })
  try {
    await showConfirmDialog({
      title: '发起解绑申请',
      message: '申请不会立即解绑。对方确认后关系解除，现有可恢复数据保留 30 天。'
    })
  } catch (error) {
    logUiEvent('settings.couple.unbind.apply', {
      module: 'settings', operation: 'unbind_apply', result: 'cancelled',
      durationMs: Date.now() - startedAt, errorCode: 'USER_CANCELLED'
    })
    return
  }

  if (isUnbinding.value) return
  isUnbinding.value = true
  try {
    await coupleApi.applyUnbind({})
    const refreshResult = await userStore.getCoupleInfo()
    if (refreshResult.status === 'error') {
      unbindRefreshWarning.value = true
      logUiEvent('settings.couple.unbind.apply', {
        module: 'settings', operation: 'unbind_apply', result: 'refresh_error',
        durationMs: Date.now() - startedAt, errorCode: refreshResult.errorCode
      })
      showToast('申请已提交，关系状态刷新失败')
      return
    }
    logUiEvent('settings.couple.unbind.apply', {
      module: 'settings', operation: 'unbind_apply', result: 'success',
      durationMs: Date.now() - startedAt, errorCode: 'NONE'
    })
    showToast('已发起申请，等待对方处理')
  } catch (error) {
    logUiEvent('settings.couple.unbind.apply', {
      module: 'settings', operation: 'unbind_apply', result: 'error',
      durationMs: Date.now() - startedAt, errorCode: normalizeUiErrorCode(error)
    })
    showToast('暂时无法发起解绑申请')
  } finally {
    isUnbinding.value = false
  }
}

const logout = async () => {
  const startedAt = Date.now()
  logUiEvent('settings.logout', {
    module: 'settings', operation: 'logout_confirmation', result: 'started',
    durationMs: 0, errorCode: 'NONE', cleanupItemCount: 0
  })
  try {
    await showConfirmDialog({
      title: '退出当前设备',
      message: '将清除当前设备上的登录会话；服务端 JWT 不保证立即吊销。'
    })
  } catch (error) {
    logUiEvent('settings.logout', {
      module: 'settings', operation: 'logout_confirmation', result: 'cancelled',
      durationMs: Date.now() - startedAt, errorCode: 'USER_CANCELLED', cleanupItemCount: 0
    })
    return
  }

  if (isLoggingOut.value) return
  isLoggingOut.value = true
  await userStore.logout()
  await router.replace('/login')
}

onMounted(() => {
  themeStore.initializeTheme()
  loadProfile()
})
</script>

<template>
  <div class="settings-page">
    <header class="settings-header">
      <div>
        <p>Couple Cosmos</p>
        <h1>我们</h1>
      </div>
      <RouterLink
        class="notification-link"
        to="/notifications"
        aria-label="打开通知中心"
      >
        <van-icon name="bell" />
      </RouterLink>
    </header>

    <main class="settings-content">
      <section
        v-if="profileStatus === 'loading'"
        class="state-panel"
        data-test="settings-loading"
        role="status"
      >
        <span
          class="spinner"
          aria-hidden="true"
        />
        <p>正在同步账号资料</p>
      </section>
      <section
        v-else-if="profileStatus === 'unauthorized'"
        class="state-panel"
        data-test="settings-unauthorized"
        role="alert"
      >
        <h2>需要重新登录</h2>
        <p>登录状态不可用，正在返回登录页。</p>
      </section>
      <section
        v-else-if="profileStatus === 'error'"
        class="state-panel"
        role="alert"
      >
        <h2>资料读取失败</h2>
        <p>{{ profileError }}</p>
        <button
          type="button"
          @click="loadProfile"
        >
          重新加载
        </button>
      </section>

      <template v-else>
        <section class="profile-panel">
          <div class="avatar-frame">
            <img
              v-if="profileInfo?.avatarUrl"
              :src="profileInfo.avatarUrl"
              alt="当前头像"
            >
            <van-icon
              v-else
              name="user-o"
              aria-label="未设置头像"
            />
          </div>
          <div class="profile-copy">
            <p>个人资料</p>
            <h2>{{ profileInfo?.nickName || '未设置昵称' }}</h2>
          </div>
          <button
            data-test="profile-edit"
            type="button"
            aria-label="编辑个人资料"
            @click="openProfileEditor"
          >
            <van-icon name="edit" />
          </button>
        </section>

        <section
          v-if="editOpen"
          class="edit-sheet"
          aria-label="编辑个人资料"
        >
          <label for="settings-nickname">昵称</label>
          <input
            id="settings-nickname"
            v-model="editForm.nickName"
            data-test="nickname-input"
            maxlength="30"
          >
          <label
            class="avatar-upload"
            for="settings-avatar"
          >
            <span>{{ isUploading ? '上传中' : '选择新头像' }}</span>
            <input
              id="settings-avatar"
              data-test="avatar-input"
              type="file"
              accept="image/*"
              :disabled="isUploading || isSaving"
              @change="uploadAvatar"
            >
          </label>
          <p
            v-if="profileError"
            class="error-copy"
            data-test="profile-error"
          >
            {{ profileError }}
          </p>
          <div class="sheet-actions">
            <button
              type="button"
              :disabled="isSaving"
              @click="editOpen = false"
            >
              取消
            </button>
            <button
              data-test="profile-save"
              type="button"
              :disabled="!canSaveProfile"
              @click="saveProfile"
            >
              {{ isSaving ? '保存中' : '保存资料' }}
            </button>
          </div>
        </section>

        <section class="settings-section">
          <div class="section-heading">
            <div>
              <p>设备偏好</p>
              <h2>显示与通知</h2>
            </div>
          </div>
          <div class="setting-row setting-row--stacked">
            <div>
              <strong>主题</strong>
              <span>Cosmos 深色或系统高对比</span>
            </div>
            <div
              class="segments"
              aria-label="主题选择"
            >
              <button
                type="button"
                :class="{ active: themeStore.theme === 'cosmos' }"
                @click="changeTheme('cosmos')"
              >
                Cosmos
              </button>
              <button
                type="button"
                :class="{ active: themeStore.theme === 'system-contrast' }"
                @click="changeTheme('system-contrast')"
              >
                高对比
              </button>
            </div>
          </div>
          <label class="setting-row">
            <span>
              <strong>通知列表显示</strong>
              <small>仅影响本机显示，不改变服务端投递</small>
            </span>
            <input
              :checked="notificationDisplayEnabled"
              data-test="notification-preference"
              type="checkbox"
              role="switch"
              @change="changeNotificationPreference"
            >
          </label>
        </section>

        <section class="settings-section">
          <div class="section-heading">
            <div>
              <p>会员</p>
              <h2>当前等级</h2>
            </div>
            <strong data-test="member-level">{{ memberLabel }}</strong>
          </div>
          <p class="contract-copy">
            当前服务暂未提供会员权益、升级、订阅或支付接口。
          </p>
          <button
            class="secondary-action"
            data-test="member-action"
            type="button"
            @click="showMemberUnavailable"
          >
            查看会员入口
          </button>
          <p
            v-if="memberUnavailable"
            class="unavailable-copy"
            data-test="member-unavailable"
          >
            会员与订阅服务暂不可用
          </p>
        </section>

        <section class="settings-section">
          <div class="section-heading">
            <div>
              <p>法律与数据权利</p>
              <h2>透明边界</h2>
            </div>
          </div>
          <nav
            class="legal-links"
            aria-label="法律与数据权利"
          >
            <RouterLink
              v-for="link in LEGAL_LINKS"
              :key="link.to"
              :to="link.to"
              data-test="legal-link"
            >
              <span>{{ link.label }}</span><van-icon name="arrow" />
            </RouterLink>
          </nav>
        </section>

        <section class="settings-section danger-section">
          <div class="section-heading">
            <div>
              <p>情侣关系</p>
              <h2>{{ coupleInfo ? '已绑定' : '未绑定' }}</h2>
            </div>
          </div>
          <p class="contract-copy">
            发起申请不会立即解绑。双方确认后关系解除，现有可恢复数据保留 30 天。
          </p>
          <button
            class="danger-action"
            data-test="unbind-action"
            type="button"
            :disabled="isUnbinding"
            @click="applyUnbind"
          >
            {{ isUnbinding ? '提交中' : '发起解绑申请' }}
          </button>
          <p
            v-if="unboundVisible"
            class="unavailable-copy"
            data-test="unbind-unbound"
          >
            当前没有已绑定的情侣关系，未发送请求。
          </p>
          <p
            v-if="unbindRefreshWarning"
            class="unavailable-copy"
            data-test="unbind-refresh-warning"
          >
            解绑申请已提交，但关系状态暂未确认；当前保留原关系信息。
          </p>
        </section>

        <section class="logout-section">
          <p>仅退出当前设备上的本地会话，不代表所有设备退出或服务端令牌已即时吊销。</p>
          <button
            data-test="logout-action"
            type="button"
            :disabled="isLoggingOut"
            @click="logout"
          >
            {{ isLoggingOut ? '正在退出' : '退出当前设备' }}
          </button>
        </section>
      </template>
    </main>
  </div>
</template>

<style lang="scss" scoped>
.settings-page { min-height: 100vh; padding-bottom: $space-8; color: $cosmos-text; background: $cosmos-bg; }
.settings-header { display: flex; min-height: 72px; padding: $space-4 $page-padding; align-items: center; justify-content: space-between; border-bottom: 1px solid $cosmos-border; background: rgba(11,16,32,.92); }
.settings-header p, .section-heading p { color: $cosmos-secondary; font-size: $fs-caption; font-weight: $fw-semibold; }
.settings-header h1 { margin-top: 2px; font-size: $fs-headline; }
.notification-link, .profile-panel > button { display: grid; width: 44px; height: 44px; place-items: center; border: 1px solid $cosmos-border; border-radius: 50%; background: $cosmos-surface-raised; color: $cosmos-primary; }
.settings-content { display: grid; gap: $space-4; max-width: 720px; margin: 0 auto; padding: $space-5 $page-padding 96px; }
.profile-panel, .settings-section, .edit-sheet { padding: $space-5; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; }
.profile-panel { display: grid; grid-template-columns: 64px minmax(0,1fr) 44px; gap: $space-4; align-items: center; }
.avatar-frame { display: grid; width: 64px; height: 64px; overflow: hidden; place-items: center; border: 2px solid $cosmos-secondary; border-radius: 50%; background: $cosmos-surface-raised; color: $cosmos-secondary; font-size: 28px; }
.avatar-frame img { width: 100%; height: 100%; object-fit: cover; }
.profile-copy { min-width: 0; }
.profile-copy p { color: $cosmos-text-muted; font-size: $fs-caption; }
.profile-copy h2 { overflow: hidden; margin-top: $space-1; text-overflow: ellipsis; white-space: nowrap; font-size: $fs-title; }
.profile-panel > button { padding: 0; cursor: pointer; }
.edit-sheet { display: grid; gap: $space-3; }
.edit-sheet label { color: $cosmos-text-muted; font-size: $fs-label; }
.edit-sheet input:not([type='file']) { min-height: 44px; padding: 0 $space-3; border: 1px solid $cosmos-border; border-radius: 6px; outline: 0; background: $cosmos-surface-raised; color: $cosmos-text; font-size: $fs-body; }
.avatar-upload { display: flex; min-height: 44px; padding: 0 $space-3; align-items: center; border: 1px dashed $cosmos-secondary; border-radius: 6px; color: $cosmos-secondary !important; cursor: pointer; }
.avatar-upload input { position: absolute; width: 1px; height: 1px; overflow: hidden; opacity: 0; }
.sheet-actions { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; }
.sheet-actions button, .secondary-action, .danger-action, .logout-section button, .state-panel button { min-height: 44px; padding: 0 $space-4; border: 1px solid $cosmos-border; border-radius: 6px; background: $cosmos-surface-raised; color: $cosmos-text; font-weight: $fw-semibold; }
.sheet-actions button:last-child { border-color: $cosmos-primary; background: $cosmos-primary; color: #fff; }
button:disabled { cursor: not-allowed; opacity: .5; }
.section-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: $space-4; }
.section-heading h2 { margin-top: 2px; font-size: $fs-title; }
.section-heading > strong { color: $cosmos-gold; }
.setting-row { display: flex; min-height: 64px; margin-top: $space-4; align-items: center; justify-content: space-between; gap: $space-4; border-top: 1px solid $cosmos-border; }
.setting-row--stacked { flex-wrap: wrap; padding-top: $space-4; }
.setting-row strong, .setting-row small, .setting-row span { display: block; }
.setting-row small, .setting-row div > span { margin-top: 2px; color: $cosmos-text-muted; font-size: $fs-caption; }
.setting-row input[type='checkbox'] { width: 42px; height: 24px; accent-color: $cosmos-primary; }
.segments { display: grid; grid-template-columns: 1fr 1fr; gap: $space-1; }
.segments button { min-height: 40px; padding: 0 $space-3; border: 1px solid $cosmos-border; border-radius: 6px; background: transparent; color: $cosmos-text-muted; }
.segments button.active { border-color: $cosmos-secondary; background: rgba(84,232,211,.12); color: $cosmos-secondary; }
.contract-copy, .logout-section p { margin-top: $space-3; color: $cosmos-text-muted; font-size: $fs-caption; line-height: 20px; }
.secondary-action, .danger-action { width: 100%; margin-top: $space-4; }
.danger-section { border-color: rgba(255,130,145,.45); }
.danger-action { border-color: $color-error; background: transparent; color: $color-error; }
.legal-links { display: grid; margin-top: $space-3; }
.legal-links a { display: flex; min-height: 48px; align-items: center; justify-content: space-between; border-top: 1px solid $cosmos-border; color: $cosmos-text; }
.logout-section { padding: $space-2 0; text-align: center; }
.logout-section button { margin-top: $space-3; border-color: transparent; background: transparent; color: $cosmos-text-muted; }
.state-panel { display: grid; min-height: 280px; padding: $space-8; place-items: center; align-content: center; gap: $space-3; text-align: center; }
.state-panel p, .error-copy, .unavailable-copy { color: $cosmos-text-muted; font-size: $fs-label; }
.error-copy { color: $color-error; }
.unavailable-copy { margin-top: $space-3; color: $cosmos-gold; }
.spinner { width: 32px; height: 32px; border: 3px solid $cosmos-border; border-top-color: $cosmos-secondary; border-radius: 50%; animation: cosmos-orbit $cosmos-duration-slow linear infinite; }
@media (max-width: 360px) { .setting-row--stacked { display: grid; } .segments { width: 100%; } }
</style>
