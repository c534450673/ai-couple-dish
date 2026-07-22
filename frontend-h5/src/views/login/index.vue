<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { logUiEvent } from '@/composables/useStructuredLog'
import AgreementDialog from '@/components/AgreementDialog.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const mode = ref('login')
const account = ref('')
const password = ref('')
const agreed = ref(false)
const loading = ref(false)
const errors = ref({})
const unavailable = ref('')
const showAgreementDialog = ref(false)
const showPrivacyDialog = ref(false)

const safeRedirect = (candidate) => {
  if (typeof candidate !== 'string' || !candidate.startsWith('/') || candidate.startsWith('//')) return '/home'
  return router.resolve(candidate)?.matched?.length ? candidate : '/home'
}

const validate = () => {
  errors.value = {
    ...(account.value.trim() ? {} : { account: '请输入账号' }),
    ...(password.value ? {} : { password: '请输入密码' }),
    ...(agreed.value ? {} : { agreement: '请先阅读并同意协议' })
  }
  return Object.keys(errors.value).length === 0
}

const submit = async () => {
  if (loading.value || !validate()) return

  const startedAt = Date.now()
  loading.value = true
  unavailable.value = ''
  const operation = mode.value === 'login' ? 'login' : 'register'
  try {
    const result = await userStore[operation]({ account: account.value.trim(), password: password.value })
    if (result.status === 'unavailable' && result.reason === 'PASSWORD_AUTH_NOT_SUPPORTED') {
      unavailable.value = '密码登录/注册暂不可用，当前服务端未提供该认证能力'
      logUiEvent(`auth.${operation}`, {
        module: 'auth',
        operation,
        result: 'unavailable',
        durationMs: Date.now() - startedAt,
        errorCode: result.reason,
        userId: 'anonymous'
      })
      return
    }

    if (result.status === 'authenticated') {
      router.push(safeRedirect(route.query.redirect))
      return
    }

    logUiEvent(`auth.${operation}`, {
      module: 'auth', operation, result: 'unexpected_result', durationMs: Date.now() - startedAt, userId: 'anonymous'
    })
  } catch (error) {
    unavailable.value = '暂时无法处理请求，请稍后再试'
    logUiEvent(`auth.${operation}`, {
      module: 'auth', operation, result: 'failed', durationMs: Date.now() - startedAt,
      errorCode: error?.code || 'UNKNOWN', userId: 'anonymous'
    })
  } finally {
    loading.value = false
  }
}

const switchMode = (nextMode) => {
  mode.value = nextMode
  unavailable.value = ''
  errors.value = {}
}
</script>

<template>
  <main class="login-page">
    <section class="login-hero" aria-labelledby="login-title">
      <div class="cosmos-mark" aria-hidden="true"><span></span><i></i></div>
      <p class="eyebrow">Couple Cosmos</p>
      <h1 id="login-title" class="title">登录我们的宇宙</h1>
      <p class="subtitle">用已开通的账号连接只属于你们的星球</p>
    </section>

    <section class="login-panel" aria-label="账号登录">
      <div class="mode-switch" role="tablist" aria-label="认证方式">
        <button :class="{ active: mode === 'login' }" type="button" role="tab" @click="switchMode('login')">登录</button>
        <button :class="{ active: mode === 'register' }" type="button" role="tab" @click="switchMode('register')">注册</button>
      </div>

      <label class="field-label" for="account">账号</label>
      <input id="account" v-model.trim="account" data-test="account-input" class="auth-input" autocomplete="username" placeholder="输入账号" :aria-invalid="Boolean(errors.account)">
      <p v-if="errors.account" data-test="account-error" class="field-error">{{ errors.account }}</p>

      <label class="field-label" for="password">密码</label>
      <input id="password" v-model="password" data-test="password-input" class="auth-input" type="password" autocomplete="current-password" placeholder="输入密码" :aria-invalid="Boolean(errors.password)">
      <p v-if="errors.password" data-test="password-error" class="field-error">{{ errors.password }}</p>

      <label class="agreement-row">
        <input v-model="agreed" data-test="agreement-input" type="checkbox">
        <span>我已阅读并同意 <button type="button" @click="showAgreementDialog = true">用户协议</button> 与 <button type="button" @click="showPrivacyDialog = true">隐私政策</button></span>
      </label>
      <p v-if="errors.agreement" class="field-error">{{ errors.agreement }}</p>

      <button data-test="auth-submit" class="auth-submit" type="button" :disabled="loading" @click="submit">
        {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
      </button>
      <p v-if="unavailable" data-test="auth-unavailable" class="unavailable" role="status">{{ unavailable }}</p>
    </section>

    <p class="login-footer">Couple Cosmos · 私人银河已加密</p>
    <AgreementDialog v-model:show="showAgreementDialog" type="agreement" />
    <AgreementDialog v-model:show="showPrivacyDialog" type="privacy" />
  </main>
</template>

<style lang="scss" scoped>
.login-page { min-height: 100vh; padding: 52px $page-padding 32px; display: flex; flex-direction: column; background: radial-gradient(circle at 50% 0, #292044 0, $cosmos-bg 48%); color: $cosmos-text; }
.login-hero { text-align: center; margin: 24px 0 36px; }
.cosmos-mark { position: relative; width: 88px; height: 88px; margin: 0 auto 20px; border: 1px solid rgba(255,255,255,.18); border-radius: 50%; .span, span, i { position: absolute; display: block; border-radius: 50%; } span { width: 28px; height: 28px; top: 18px; left: 18px; background: $cosmos-primary; box-shadow: 0 0 26px rgba(255,93,115,.55); } i { width: 23px; height: 23px; right: 17px; bottom: 19px; background: $cosmos-secondary; box-shadow: 0 0 24px rgba(84,232,211,.48); } }
.eyebrow { color: $cosmos-primary; font-size: $fs-label; font-weight: $fw-semibold; margin-bottom: $space-2; }
.title { font-size: 28px; line-height: 36px; margin: 0 0 $space-2; }
.subtitle, .login-footer { color: $cosmos-text-muted; font-size: $fs-label; }
.login-panel { @include glass(.74); padding: $space-6; border-radius: 8px; box-shadow: $shadow-card; }
.mode-switch { display: grid; grid-template-columns: 1fr 1fr; margin-bottom: $space-6; padding: 3px; border-radius: 8px; background: rgba(255,255,255,.07); button { min-height: 44px; border: 0; border-radius: 6px; background: transparent; color: $cosmos-text-muted; font-size: $fs-body; cursor: pointer; &.active { background: $cosmos-primary; color: #fff; } } }
.field-label { display: block; margin: $space-4 0 $space-2; font-size: $fs-label; color: $cosmos-text-muted; }
.auth-input { width: 100%; min-height: 48px; padding: 0 $space-3; color: $cosmos-text; background: rgba(8, 13, 30, .58); border: 1px solid $cosmos-border; border-radius: 6px; outline: none; &:focus { border-color: $cosmos-secondary; } &[aria-invalid='true'] { border-color: $color-error; } }
.field-error { min-height: 18px; margin-top: $space-1; color: $color-error; font-size: $fs-caption; }
.agreement-row { display: flex; gap: $space-2; align-items: flex-start; margin-top: $space-5; color: $cosmos-text-muted; font-size: $fs-caption; line-height: 20px; input { margin-top: 3px; accent-color: $cosmos-primary; } button { border: 0; padding: 0; color: $cosmos-primary; background: transparent; font: inherit; } }
.auth-submit { width: 100%; min-height: 48px; margin-top: $space-5; border: 0; border-radius: 6px; background: $cosmos-primary; color: #fff; font-size: $fs-body; font-weight: $fw-semibold; cursor: pointer; &:disabled { opacity: .58; cursor: not-allowed; } }
.unavailable { margin-top: $space-3; color: $cosmos-gold; font-size: $fs-label; line-height: 20px; }
.login-footer { margin-top: auto; padding-top: 28px; text-align: center; }
</style>
