<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { coupleApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'
import { useReducedMotion } from '@/composables/useReducedMotion'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const prefersReducedMotion = useReducedMotion()
const mode = ref('invite')
const codeInfo = ref(null)
const partnerCode = ref('')
const loadingCode = ref(false)
const binding = ref(false)
const bindError = ref('')
const completed = ref(false)

const inviteCode = computed(() => codeInfo.value?.coupleCode || '')
const remainingSeconds = computed(() => Math.max(0, Number(codeInfo.value?.remainingSeconds || 0)))
const expiryProgress = computed(() => Math.min(100, (remainingSeconds.value / (7 * 24 * 60 * 60)) * 100))
const isValidInviteCode = (code) => /^[A-Z0-9]{8}$/.test(code || '')
const normalizedPartnerCode = computed(() => partnerCode.value.trim().toUpperCase())
const canBind = computed(() => isValidInviteCode(normalizedPartnerCode.value) && !binding.value)

const maskedUserId = () => {
  const id = String(userStore.userInfo?.id || '')
  return id ? `${id.slice(0, 2)}***` : 'anonymous'
}

const safeRedirect = (candidate) => {
  if (typeof candidate !== 'string' || !candidate.startsWith('/') || candidate.startsWith('//')) return '/home'
  return router.resolve(candidate)?.matched?.length ? candidate : '/home'
}

const errorMessage = (error) => {
  const code = error?.code || error?.response?.data?.code
  if (code === 2002) return '你已绑定情侣关系，无需重复绑定'
  if (code === 2003) return '情侣码无效或已过期'
  if (code === 2005) return '绑定冲突，请刷新后重试'
  if (error?.message?.includes('系统繁忙')) return '系统繁忙，请稍后再试'
  return error?.message || '绑定失败，请稍后重试'
}

const updateCode = (payload) => {
  const next = typeof payload === 'string' ? { coupleCode: payload } : payload
  if (!isValidInviteCode(next?.coupleCode)) return false
  codeInfo.value = {
    ...next,
    coupleCode: next.coupleCode.toUpperCase(),
    remainingSeconds: next.remainingSeconds ?? 7 * 24 * 60 * 60,
    status: next.status || 'valid',
    expired: Boolean(next.expired),
    expiringSoon: Boolean(next.expiringSoon)
  }
  return true
}

const generateCode = async (operation = 'generate') => {
  if (loadingCode.value) return
  const startedAt = Date.now()
  loadingCode.value = true
  try {
    const response = operation === 'refresh' ? await coupleApi.refreshCode() : await coupleApi.generateCoupleCode()
    if (!updateCode(response.data)) throw new Error('情侣码生成失败，请稍后重试')
    logUiEvent('couple.code.generate', {
      module: 'couple', operation, result: 'success', durationMs: Date.now() - startedAt, userId: maskedUserId()
    })
    showToast(operation === 'refresh' ? '情侣码已重新生成' : '情侣码已生成')
  } catch (error) {
    const message = errorMessage(error)
    showToast(message)
    logUiEvent('couple.code.generate', {
      module: 'couple', operation, result: 'failed', durationMs: Date.now() - startedAt,
      errorCode: error?.code || error?.response?.data?.code || 'UNKNOWN', userId: maskedUserId()
    })
  } finally {
    loadingCode.value = false
  }
}

const loadCode = async () => {
  loadingCode.value = true
  try {
    const response = await coupleApi.getCodeInfo()
    const current = response.data
    if (!current?.expired && current?.status !== 'expired' && updateCode(current)) return
  } catch (error) {
    // 无可用邀请码时转为生成流程，日志仅记录实际生成结果。
  } finally {
    loadingCode.value = false
  }
  await generateCode()
}

const copyCode = async () => {
  if (!inviteCode.value) return
  if (!navigator.clipboard?.writeText) {
    showToast('当前浏览器不支持复制，请手动复制')
    return
  }
  try {
    await navigator.clipboard.writeText(inviteCode.value)
    showToast('情侣码已复制')
  } catch (error) {
    showToast('复制失败，请手动复制')
  }
}

const refreshCode = async () => {
  try {
    await showConfirmDialog({
      title: '重新生成情侣码',
      message: '重新生成后，服务端会将恋爱开始日重置为当天。'
    })
    await generateCode('refresh')
  } catch (error) {
    // 用户取消确认时不需要提示或记录邀请码。
  }
}

const handleBind = async () => {
  if (!canBind.value || binding.value) return
  const startedAt = Date.now()
  binding.value = true
  bindError.value = ''
  try {
    const response = await coupleApi.bindCouple({ coupleCode: normalizedPartnerCode.value })
    if (response.data) userStore.setCoupleInfo(response.data)
    else await userStore.getCoupleInfo()
    completed.value = true
    logUiEvent('couple.bind', {
      module: 'couple', operation: 'bind', result: 'success', durationMs: Date.now() - startedAt, userId: maskedUserId()
    })
    showToast('绑定成功')
    router.replace(safeRedirect(route.query.redirect))
  } catch (error) {
    bindError.value = errorMessage(error)
    logUiEvent('couple.bind', {
      module: 'couple', operation: 'bind', result: 'failed', durationMs: Date.now() - startedAt,
      errorCode: error?.code || error?.response?.data?.code || 'UNKNOWN', userId: maskedUserId()
    })
  } finally {
    binding.value = false
  }
}

onMounted(loadCode)
</script>

<template>
  <main class="bind-page" :class="{ 'bind-complete': completed, 'reduced-motion': prefersReducedMotion }">
    <header class="bind-header">
      <p>Couple Cosmos</p>
      <h1>连接我们的宇宙</h1>
      <span>邀请另一颗星球，或输入 TA 的邀请码</span>
    </header>

    <div class="mode-switch" role="tablist" aria-label="绑定方式">
      <button type="button" :class="{ active: mode === 'invite' }" @click="mode = 'invite'">邀请 TA</button>
      <button type="button" :class="{ active: mode === 'enter-code' }" @click="mode = 'enter-code'">输入情侣码</button>
    </div>

    <section v-if="mode === 'invite'" class="bind-card invite-card">
      <div class="card-heading"><h2>邀请 TA</h2><button data-test="refresh-code" type="button" :disabled="loadingCode" @click="refreshCode">重新生成</button></div>
      <div class="invite-value"><strong data-test="invite-code">{{ inviteCode || '生成中...' }}</strong><button data-test="copy-code" type="button" :disabled="!inviteCode" aria-label="复制情侣码" @click="copyCode">复制</button></div>
      <p class="reset-note">重新生成会将恋爱开始日重置为当天。</p>
      <div class="expiry"><div><span>验证码有效期</span><b>{{ Math.ceil(remainingSeconds / 86400) || 7 }} 天</b></div><div class="progress"><i :style="{ width: `${expiryProgress}%` }"></i></div></div>
    </section>

    <section v-else class="bind-card enter-card">
      <h2>输入情侣码</h2>
      <input v-model="partnerCode" data-test="partner-code-input" class="code-input" maxlength="8" autocomplete="off" placeholder="输入 TA 的 8 位邀请码" @input="bindError = ''">
      <p v-if="bindError" data-test="bind-error" class="bind-error">{{ bindError }}</p>
      <button data-test="bind-submit" class="bind-submit" type="button" :disabled="!canBind" @click="handleBind">{{ binding ? '正在连接...' : '立即加入' }}</button>
      <p class="join-hint">输入后，你们的星球将合并为一个私密空间</p>
    </section>

    <div v-if="completed" class="completion" role="status">双子星已连接</div>
    <p class="bind-footer">Couple Cosmos · 私人银河已加密</p>
  </main>
</template>

<style lang="scss" scoped>
.bind-page { min-height: 100vh; padding: 48px $page-padding 32px; background: radial-gradient(circle at 50% 0, #292044 0, $cosmos-bg 52%); color: $cosmos-text; }
.bind-header { text-align: center; margin-bottom: $space-6; p { color: $cosmos-primary; font-size: $fs-label; font-weight: $fw-semibold; } h1 { margin: $space-2 0; font-size: 28px; line-height: 36px; } span { color: $cosmos-text-muted; font-size: $fs-label; } }
.mode-switch { display: grid; grid-template-columns: 1fr 1fr; padding: 3px; margin-bottom: $space-5; background: rgba(255,255,255,.08); border-radius: 8px; button { min-height: 44px; border: 0; border-radius: 6px; background: transparent; color: $cosmos-text-muted; cursor: pointer; &.active { background: $cosmos-primary; color: #fff; } } }
.bind-card { @include glass(.74); padding: $space-6; border-radius: 8px; box-shadow: $shadow-card; } .card-heading { display: flex; align-items: center; justify-content: space-between; h2 { font-size: $fs-title; } button { min-height: 44px; padding: 0 $space-2; border: 0; color: $cosmos-primary; background: transparent; font: inherit; cursor: pointer; &:disabled { opacity: .5; } } }
.invite-value { display: flex; align-items: center; justify-content: space-between; gap: $space-2; padding: $space-4; margin: $space-5 0 $space-2; background: rgba(6, 11, 28, .55); border: 1px solid rgba(255,255,255,.1); border-radius: 6px; strong { font-size: 23px; letter-spacing: 3px; word-break: break-all; } button { min-width: 44px; min-height: 44px; border: 0; border-radius: 6px; padding: 0 $space-2; background: $cosmos-primary; color: #fff; cursor: pointer; &:disabled { opacity: .5; } } }
.reset-note, .join-hint { color: $cosmos-text-muted; font-size: $fs-caption; line-height: 20px; } .expiry { margin-top: $space-5; > div:first-child { display: flex; justify-content: space-between; color: $cosmos-text-muted; font-size: $fs-label; b { color: $cosmos-text; } } } .progress { height: 6px; margin-top: $space-2; overflow: hidden; border-radius: 6px; background: rgba(255,255,255,.1); i { display: block; height: 100%; border-radius: inherit; background: $cosmos-primary; transition: width $cosmos-duration-base; } }
.enter-card h2 { margin-bottom: $space-5; color: $cosmos-secondary; font-size: $fs-title; } .code-input { width: 100%; min-height: 54px; padding: 0 $space-3; border: 1px solid $cosmos-border; border-radius: 6px; outline: none; background: rgba(6,11,28,.55); color: $cosmos-text; text-align: center; text-transform: uppercase; letter-spacing: 2px; &:focus { border-color: $cosmos-secondary; } } .bind-error { min-height: 20px; margin-top: $space-2; color: $color-error; font-size: $fs-caption; } .bind-submit { width: 100%; min-height: 48px; margin-top: $space-5; border: 0; border-radius: 6px; background: $cosmos-secondary; color: #062421; font-weight: $fw-semibold; cursor: pointer; &:disabled { opacity: .48; cursor: not-allowed; } } .join-hint { margin-top: $space-4; text-align: center; }
.completion { margin-top: $space-5; padding: $space-3; border: 1px solid $cosmos-secondary; border-radius: 6px; color: $cosmos-secondary; text-align: center; animation: completion-in $cosmos-duration-slow $ease-standard both; } .reduced-motion .completion { animation: none; } @keyframes completion-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.bind-footer { margin-top: 44px; color: rgba($cosmos-text-muted, .62); font-size: $fs-caption; text-align: center; }
</style>
