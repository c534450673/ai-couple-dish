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
const phone = ref('')
const verifyCode = ref('')
const agreed = ref(false)
const loading = ref(false)
const sendingCode = ref(false)
const errors = ref({})
const notice = ref('')
const devCode = ref('')
const showAgreementDialog = ref(false)
const showPrivacyDialog = ref(false)

const safeRedirect = (candidate) => {
  if (typeof candidate !== 'string' || !candidate.startsWith('/') || candidate.startsWith('//')) return '/home'
  return router.resolve(candidate)?.matched?.length ? candidate : '/home'
}

const validate = () => {
  errors.value = {
    ...(/^1[3-9]\d{9}$/.test(phone.value.trim()) ? {} : { phone: '请输入正确的手机号' }),
    ...(verifyCode.value.trim() ? {} : { verifyCode: '请输入验证码' }),
    ...(agreed.value ? {} : { agreement: '请先阅读并同意协议' })
  }
  return Object.keys(errors.value).length === 0
}

const sendCode = async () => {
  errors.value = {}
  if (!/^1[3-9]\d{9}$/.test(phone.value.trim())) {
    errors.value = { phone: '请输入正确的手机号' }
    return
  }
  const startedAt = Date.now()
  sendingCode.value = true
  notice.value = ''
  devCode.value = ''
  try {
    const result = await userStore.sendVerifyCode(phone.value.trim())
    devCode.value = result?.data?.devCode || ''
    notice.value = devCode.value ? '测试验证码已生成，请完成验证' : '验证码已发送，请查收短信'
    logUiEvent('auth.send_code', {
      module: 'auth', operation: 'send_verify_code', result: 'success',
      durationMs: Date.now() - startedAt, errorCode: 'NONE', userId: 'anonymous'
    })
  } catch (error) {
    notice.value = error?.message || '验证码发送失败，请稍后再试'
    logUiEvent('auth.send_code', {
      module: 'auth', operation: 'send_verify_code', result: 'failed',
      durationMs: Date.now() - startedAt, errorCode: error?.code || 'UNKNOWN', userId: 'anonymous'
    })
  } finally {
    sendingCode.value = false
  }
}

const submit = async () => {
  if (loading.value || !validate()) return

  const startedAt = Date.now()
  loading.value = true
  notice.value = ''
  const operation = mode.value === 'login' ? 'phone_login' : 'phone_register'
  try {
    const action = mode.value === 'login' ? userStore.loginByPhone : userStore.registerByPhone
    await action.call(userStore, phone.value.trim(), verifyCode.value.trim())
    logUiEvent(`auth.${operation}`, {
      module: 'auth', operation, result: 'success', durationMs: Date.now() - startedAt,
      errorCode: 'NONE', userId: userStore.userInfo?.id || 'anonymous'
    })
    router.push(safeRedirect(route.query.redirect))
  } catch (error) {
    notice.value = error?.message || '暂时无法处理请求，请检查验证码后重试'
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
  notice.value = ''
  errors.value = {}
}
</script>

<template>
  <main class="login-page">
    <section class="login-hero" aria-labelledby="login-title">
      <div class="cosmos-mark" aria-hidden="true"><span></span><i></i></div>
      <p class="eyebrow">Couple Cosmos</p>
      <h1 id="login-title" class="title">登录我们的宇宙</h1>
      <p class="subtitle">用手机号连接只属于你们的星球</p>
    </section>

    <section class="login-panel" aria-label="账号登录">
      <div class="mode-switch" role="tablist" aria-label="认证方式">
        <button :class="{ active: mode === 'login' }" type="button" role="tab" @click="switchMode('login')">登录</button>
        <button :class="{ active: mode === 'register' }" type="button" role="tab" @click="switchMode('register')">注册</button>
      </div>

      <label class="field-label" for="phone">手机号</label>
      <input id="phone" v-model.trim="phone" data-test="phone-input" class="auth-input" inputmode="tel" autocomplete="tel" maxlength="11" placeholder="输入手机号" :aria-invalid="Boolean(errors.phone)">
      <p v-if="errors.phone" data-test="phone-error" class="field-error">{{ errors.phone }}</p>

      <label class="field-label" for="verify-code">验证码</label>
      <div class="code-row">
        <input id="verify-code" v-model.trim="verifyCode" data-test="verify-code-input" class="auth-input" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="输入验证码" :aria-invalid="Boolean(errors.verifyCode)">
        <button data-test="send-code" class="send-code" type="button" :disabled="sendingCode" @click="sendCode">{{ sendingCode ? '发送中...' : '获取验证码' }}</button>
      </div>
      <p v-if="errors.verifyCode" data-test="verify-code-error" class="field-error">{{ errors.verifyCode }}</p>
      <p v-if="devCode" data-test="dev-code" class="dev-code">测试验证码：{{ devCode }}</p>

      <label class="agreement-row">
        <input v-model="agreed" data-test="agreement-input" type="checkbox">
        <span>我已阅读并同意 <button type="button" @click="showAgreementDialog = true">用户协议</button> 与 <button type="button" @click="showPrivacyDialog = true">隐私政策</button></span>
      </label>
      <p v-if="errors.agreement" class="field-error">{{ errors.agreement }}</p>

      <button data-test="auth-submit" class="auth-submit" type="button" :disabled="loading" @click="submit">
        {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
      </button>
      <p v-if="notice" data-test="auth-notice" class="unavailable" role="status">{{ notice }}</p>
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
.code-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: $space-2; align-items: start; }
.send-code { min-height: 48px; padding: 0 $space-3; border: 1px solid $cosmos-secondary; border-radius: 6px; background: transparent; color: $cosmos-secondary; white-space: nowrap; cursor: pointer; &:disabled { opacity: .58; cursor: not-allowed; } }
.field-error { min-height: 18px; margin-top: $space-1; color: $color-error; font-size: $fs-caption; }
.agreement-row { display: flex; gap: $space-2; align-items: flex-start; margin-top: $space-5; color: $cosmos-text-muted; font-size: $fs-caption; line-height: 20px; input { margin-top: 3px; accent-color: $cosmos-primary; } button { border: 0; padding: 0; color: $cosmos-primary; background: transparent; font: inherit; } }
.auth-submit { width: 100%; min-height: 48px; margin-top: $space-5; border: 0; border-radius: 6px; background: $cosmos-primary; color: #fff; font-size: $fs-body; font-weight: $fw-semibold; cursor: pointer; &:disabled { opacity: .58; cursor: not-allowed; } }
.unavailable { margin-top: $space-3; color: $cosmos-gold; font-size: $fs-label; line-height: 20px; }
.dev-code { margin-top: $space-1; color: $cosmos-secondary; font-size: $fs-caption; }
.login-footer { margin-top: auto; padding-top: 28px; text-align: center; }
@media (max-width: 380px) { .code-row { grid-template-columns: 1fr; } .send-code { width: 100%; } }
</style>
