<template>
  <div class="bind-page">
    <div class="bind-header">
      <h1>绑定TA</h1>
      <p>和亲爱的TA开始私密美食之旅</p>
    </div>

    <div class="bind-content">
      <!-- 我的情侣码 -->
      <div class="my-code card">
        <div class="code-label">我的情侣码</div>
        <div class="code-value" v-if="myCoupleCode">{{ myCoupleCode }}</div>
        <div class="code-value loading" v-else>生成中...</div>
        <div class="code-desc">让TA扫码绑定，或告诉TA这个码</div>
        <van-button type="primary" size="small" @click="generateCode" :loading="generating">
          {{ myCoupleCode ? '重新生成' : '生成情侣码' }}
        </van-button>
      </div>

      <div class="divider">
        <span>或</span>
      </div>

      <!-- 绑定TA -->
      <div class="bind-form card">
        <div class="form-title">绑定TA的情侣码</div>
        <van-field
          v-model="partnerCode"
          placeholder="请输入TA的情侣码"
          maxlength="8"
          :disabled="binding"
        />
        <van-button
          type="primary"
          block
          :loading="binding"
          :disabled="!partnerCode || partnerCode.length < 6"
          @click="handleBind"
        >
          绑定
        </van-button>
      </div>
    </div>

    <div class="bind-tip">
      <van-icon name="info-o" />
      <span>绑定后你们可以看到彼此的私密菜单和美食笔记</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { useUserStore } from '@/stores/user'
import { coupleApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()

const myCoupleCode = ref('')
const partnerCode = ref('')
const generating = ref(false)
const binding = ref(false)

const generateCode = async () => {
  generating.value = true
  try {
    const res = await coupleApi.generateCoupleCode()
    myCoupleCode.value = res.data.coupleCode
    showToast('情侣码已生成')
  } catch (error) {
    showToast('生成失败')
  } finally {
    generating.value = false
  }
}

const handleBind = async () => {
  if (!partnerCode.value || partnerCode.value.length < 6) {
    showToast('请输入正确的情侣码')
    return
  }

  binding.value = true
  showLoadingToast({ message: '绑定中...', forbidClick: true })
  try {
    await coupleApi.bindCouple({ coupleCode: partnerCode.value })
    await userStore.getCoupleInfo()
    closeToast()
    showToast('绑定成功')
    router.replace('/home')
  } catch (error) {
    closeToast()
    showToast(error.message || '绑定失败')
  } finally {
    binding.value = false
  }
}

onMounted(() => {
  generateCode()
})
</script>

<style lang="scss" scoped>
.bind-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20px 16px;
}

.bind-header {
  text-align: center;
  margin-bottom: 32px;

  h1 {
    font-size: 24px;
    font-weight: 600;
    color: #333;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: #999;
  }
}

.my-code {
  text-align: center;
  padding: 24px;

  .code-label {
    font-size: 14px;
    color: #999;
    margin-bottom: 12px;
  }

  .code-value {
    font-size: 36px;
    font-weight: 700;
    color: #ff4757;
    letter-spacing: 4px;
    margin-bottom: 8px;

    &.loading {
      font-size: 16px;
      color: #999;
    }
  }

  .code-desc {
    font-size: 12px;
    color: #999;
    margin-bottom: 16px;
  }
}

.divider {
  text-align: center;
  margin: 24px 0;
  position: relative;

  &::before,
  &::after {
    content: '';
    position: absolute;
    top: 50%;
    width: 40%;
    height: 1px;
    background: #ddd;
  }

  &::before { left: 0; }
  &::after { right: 0; }

  span {
    background: #f5f5f5;
    padding: 0 16px;
    color: #999;
    font-size: 12px;
    position: relative;
    z-index: 1;
  }
}

.bind-form {
  .form-title {
    font-size: 14px;
    color: #666;
    margin-bottom: 16px;
  }

  :deep(.van-field) {
    margin-bottom: 16px;
    background: #f5f5f5;
    border-radius: 8px;
  }
}

.bind-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 24px;
  font-size: 12px;
  color: #999;
}
</style>
