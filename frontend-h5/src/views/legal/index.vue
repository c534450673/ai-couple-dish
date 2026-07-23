<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { logUiEvent } from '@/composables/useStructuredLog'

const router = useRouter()
const actionStates = reactive({ export: 'idle', deletion: 'idle' })
const kindUnavailableCode = 'BACKEND_CAPABILITY_UNAVAILABLE'

const eventName = (kind) => kind === 'export' ? 'legal.export' : 'legal.account.deletion'
const errorCode = (result) => ({
  started: 'NONE',
  cancelled: 'USER_CANCELLED',
  unauthorized: 'AUTH_REQUIRED',
  unavailable: kindUnavailableCode
}[result])

const logAction = (kind, result, startedAt = Date.now()) => {
  logUiEvent(eventName(kind), {
    module: 'legal',
    operation: kind === 'export' ? 'data_export' : 'account_deletion',
    result,
    durationMs: result === 'started' ? 0 : Date.now() - startedAt,
    errorCode: errorCode(result)
  })
}

const startAction = (kind) => {
  actionStates[kind] = 'confirming'
  logAction(kind, 'started')
}

const cancelAction = (kind) => {
  const startedAt = Date.now()
  actionStates[kind] = 'idle'
  logAction(kind, 'cancelled', startedAt)
}

const confirmAction = (kind) => {
  const startedAt = Date.now()
  if (!globalThis.localStorage?.getItem('token')) {
    actionStates[kind] = 'unauthorized'
    logAction(kind, 'unauthorized', startedAt)
    return
  }
  actionStates[kind] = 'unavailable'
  logAction(kind, 'unavailable', startedAt)
}

const resetAction = (kind) => {
  actionStates[kind] = 'idle'
}
</script>

<template>
  <div class="legal-page">
    <header class="legal-header">
      <button
        type="button"
        aria-label="返回"
        @click="router.back()"
      >
        <van-icon name="arrow-left" />
      </button>
      <div>
        <p>Couple Cosmos</p>
        <h1>法律与隐私</h1>
      </div>
    </header>

    <nav
      class="anchor-nav"
      aria-label="文档章节"
    >
      <a href="#privacy">隐私</a>
      <a href="#terms">协议</a>
      <a href="#third-party">第三方</a>
      <a href="#export">导出</a>
      <a href="#deletion">删号</a>
      <a href="#couple-data">情侣数据</a>
    </nav>

    <main class="legal-content">
      <section
        id="privacy"
        class="legal-section"
      >
        <p class="eyebrow">
          Privacy
        </p>
        <h2>隐私政策</h2>
        <p>服务仅在提供账号、情侣协作与内容功能所需范围内处理资料。通知正文、昵称、头像地址和完整账号响应不会写入前端诊断日志。</p>
        <p>登录会话保存在当前设备；退出时清除本地会话，但现有服务端 JWT 不保证被即时吊销。</p>
      </section>

      <section
        id="terms"
        class="legal-section"
      >
        <p class="eyebrow">
          Terms
        </p>
        <h2>服务协议</h2>
        <p>请仅上传和记录你有权使用的内容。网络请求或业务响应失败时，界面不会把未确认操作展示为成功。</p>
      </section>

      <section
        id="third-party"
        class="legal-section"
      >
        <p class="eyebrow">
          Third-party
        </p>
        <h2>第三方服务</h2>
        <p>第三方依赖用于界面、网络与日期等基础能力。具体处理边界以实际部署配置及第三方条款为准，不在此页面虚构额外的数据共享承诺。</p>
      </section>

      <section
        id="export"
        class="legal-section action-section"
      >
        <p class="eyebrow">
          Export
        </p>
        <h2>个人数据导出</h2>
        <p>当前后端没有个人数据导出、任务状态或下载接口。</p>
        <button
          v-if="actionStates.export === 'idle'"
          data-test="export-action"
          type="button"
          @click="startAction('export')"
        >
          检查导出入口
        </button>
        <div
          v-else-if="actionStates.export === 'confirming'"
          class="confirmation"
          data-test="export-confirming"
        >
          <p>确认检查当前账号是否具备数据导出能力？此检查不会创建文件或发起网络请求。</p>
          <div>
            <button
              data-test="export-cancel"
              type="button"
              @click="cancelAction('export')"
            >
              取消
            </button>
            <button
              data-test="export-confirm"
              type="button"
              @click="confirmAction('export')"
            >
              确认检查
            </button>
          </div>
        </div>
        <div
          v-else-if="actionStates.export === 'unauthorized'"
          class="result-panel"
          data-test="export-unauthorized"
          role="status"
        >
          <p>请登录后检查此数据权利入口；未发出网络请求。</p>
          <RouterLink to="/login">
            前往登录
          </RouterLink>
        </div>
        <div
          v-else
          class="result-panel"
          data-test="export-unavailable"
          role="status"
        >
          <p>暂未提供数据导出接口，未生成文件、任务或进度。</p>
          <button
            type="button"
            @click="resetAction('export')"
          >
            返回
          </button>
        </div>
      </section>

      <section
        id="deletion"
        class="legal-section action-section"
      >
        <p class="eyebrow">
          Deletion
        </p>
        <h2>账号删除</h2>
        <p>退出登录和情侣解绑都不等同于删除账号。当前后端没有账号删除接口。</p>
        <button
          v-if="actionStates.deletion === 'idle'"
          data-test="deletion-action"
          type="button"
          @click="startAction('deletion')"
        >
          检查账号删除入口
        </button>
        <div
          v-else-if="actionStates.deletion === 'confirming'"
          class="confirmation"
          data-test="deletion-confirming"
        >
          <p>确认检查当前账号是否具备删除能力？此检查不会注销账号、退出登录或清除数据。</p>
          <div>
            <button
              data-test="deletion-cancel"
              type="button"
              @click="cancelAction('deletion')"
            >
              取消
            </button>
            <button
              data-test="deletion-confirm"
              type="button"
              @click="confirmAction('deletion')"
            >
              确认检查
            </button>
          </div>
        </div>
        <div
          v-else-if="actionStates.deletion === 'unauthorized'"
          class="result-panel"
          data-test="deletion-unauthorized"
          role="status"
        >
          <p>请登录后检查此数据权利入口；未发出网络请求。</p>
          <RouterLink to="/login">
            前往登录
          </RouterLink>
        </div>
        <div
          v-else
          class="result-panel"
          data-test="deletion-unavailable"
          role="status"
        >
          <p>暂未提供账号删除接口，账号和服务端数据没有被删除。</p>
          <button
            type="button"
            @click="resetAction('deletion')"
          >
            返回
          </button>
        </div>
      </section>

      <section
        id="couple-data"
        class="legal-section"
      >
        <p class="eyebrow">
          Couple data
        </p>
        <h2>情侣数据处理</h2>
        <p>设置页只能发起双方解绑申请。对方确认解绑后，情侣关系解除；现有实现保留可恢复数据 30 天。</p>
        <p>申请阶段不会清空本地情侣信息，也不会提交删除选项或承诺即时清除共同数据。</p>
      </section>
    </main>
  </div>
</template>

<style lang="scss" scoped>
.legal-page { min-height: 100vh; padding-bottom: $space-8; color: $cosmos-text; background: $cosmos-bg; scroll-behavior: smooth; }
.legal-header { display: flex; min-height: 72px; padding: $space-3 $page-padding; align-items: center; gap: $space-3; border-bottom: 1px solid $cosmos-border; background: rgba(11,16,32,.94); }
.legal-header > button { display: grid; width: 44px; height: 44px; padding: 0; place-items: center; border: 1px solid $cosmos-border; border-radius: 50%; background: $cosmos-surface-raised; color: $cosmos-secondary; }
.legal-header p, .eyebrow { color: $cosmos-secondary; font-size: $fs-caption; font-weight: $fw-semibold; text-transform: uppercase; }
.legal-header h1 { margin-top: 2px; font-size: $fs-title; }
.anchor-nav { position: sticky; z-index: 3; top: 0; display: flex; padding: $space-2 $page-padding; gap: $space-2; overflow-x: auto; border-bottom: 1px solid $cosmos-border; background: rgba(11,16,32,.92); }
.anchor-nav a { min-height: 36px; padding: 8px $space-3; border-radius: 999px; color: $cosmos-text-muted; white-space: nowrap; font-size: $fs-caption; }
.legal-content { display: grid; gap: $space-5; max-width: 760px; margin: 0 auto; padding: $space-5 $page-padding; }
.legal-section { padding: $space-5; scroll-margin-top: 64px; border-left: 3px solid $cosmos-secondary; background: $cosmos-surface; }
.legal-section:nth-child(even) { border-left-color: $cosmos-gold; }
.legal-section h2 { margin: $space-1 0 $space-3; font-size: $fs-title; }
.legal-section > p:not(.eyebrow), .confirmation p, .result-panel p { margin-top: $space-2; color: $cosmos-text-muted; line-height: 24px; }
.action-section > button, .confirmation button, .result-panel button, .result-panel a { display: inline-grid; min-height: 44px; margin-top: $space-4; padding: 0 $space-4; place-items: center; border: 1px solid $cosmos-border; border-radius: 6px; background: $cosmos-surface-raised; color: $cosmos-text; }
.confirmation { margin-top: $space-4; padding: $space-4 0 0; border-top: 1px solid $cosmos-border; }
.confirmation > div { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; }
.confirmation button:last-child { border-color: $cosmos-primary; background: $cosmos-primary; color: #fff; }
.result-panel { margin-top: $space-4; padding: $space-4; border: 1px solid $cosmos-gold; border-radius: 6px; background: rgba(255,200,87,.08); }
@media (max-width: 360px) { .confirmation > div { grid-template-columns: 1fr; } }
</style>
