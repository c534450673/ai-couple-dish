<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { adminApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'

const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const submit = async () => {
  if (loading.value || !username.value.trim() || !password.value) return
  loading.value = true
  error.value = ''
  const startedAt = Date.now()
  try {
    const response = await adminApi.login({ username: username.value.trim(), password: password.value })
    const token = response?.data?.token
    if (!token) throw new Error('管理员令牌缺失')
    localStorage.setItem('adminToken', token)
    logUiEvent('admin.login', { module: 'admin', operation: 'login', result: 'success', durationMs: Date.now() - startedAt })
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/admin') ? route.query.redirect : '/admin'
    await router.replace(redirect)
  } catch (cause) {
    error.value = cause?.message || '管理员登录失败，请稍后重试'
    showToast(error.value)
    logUiEvent('admin.login', { module: 'admin', operation: 'login', result: 'error', durationMs: Date.now() - startedAt, errorCode: cause?.code || 'ADMIN_LOGIN_FAILED' })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="admin-login">
    <section class="admin-login__card">
      <p class="eyebrow">COUPLE COSMOS / CONTROL ROOM</p>
      <h1>运营指挥台</h1>
      <p class="muted">管理员专用入口，用户会话与后台会话彼此隔离。</p>
      <form @submit.prevent="submit">
        <label>管理员账号<input v-model="username" data-test="admin-username" autocomplete="username" required></label>
        <label>密码<input v-model="password" data-test="admin-password" type="password" autocomplete="current-password" required></label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button type="submit" :disabled="loading">{{ loading ? '正在验证…' : '进入控制室' }}</button>
      </form>
    </section>
  </main>
</template>

<style lang="scss" scoped>
.admin-login { min-height: 100vh; display: grid; place-items: center; padding: $space-6; color: $cosmos-text; background: radial-gradient(circle at 50% 0, #292044, $cosmos-bg 58%); }
.admin-login__card { width: min(100%, 440px); padding: clamp(24px, 6vw, 48px); border: 1px solid $cosmos-border; border-radius: $radius-xl; background: rgba(20, 27, 51, .84); box-shadow: $shadow-card; backdrop-filter: blur(20px); }
.eyebrow { color: $cosmos-secondary; font-size: $fs-caption; letter-spacing: .1em; } h1 { margin: $space-2 0; font-size: clamp(28px, 6vw, 40px); } .muted { color: $cosmos-text-muted; font-size: $fs-label; }
form { display: grid; gap: $space-4; margin-top: $space-6; } label { display: grid; gap: $space-2; color: $cosmos-text-muted; font-size: $fs-label; } input { min-height: 48px; padding: 0 $space-3; border: 1px solid $cosmos-border; border-radius: $radius-md; outline: none; background: rgba(6, 11, 28, .56); color: $cosmos-text; font: inherit; } input:focus { border-color: $cosmos-secondary; } button { min-height: 48px; border: 0; border-radius: $radius-pill; background: $cosmos-primary; color: #fff; font-weight: $fw-semibold; } button:disabled { opacity: .55; } .error { color: $color-error; font-size: $fs-caption; }
</style>
