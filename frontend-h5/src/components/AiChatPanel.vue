<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useAiChatStore } from '@/stores/ai'

defineProps({
  compact: { type: Boolean, default: false }
})

const aiStore = useAiChatStore()
const listRef = ref(null)
const preview = computed(() => aiStore.pendingPreview)
const isBusy = computed(() => aiStore.state === 'streaming' || aiStore.state === 'confirming')

const scrollBottom = async () => {
  await nextTick()
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
}

const send = async () => {
  await aiStore.sendMessage()
  scrollBottom()
}

watch(() => [aiStore.messages.length, aiStore.messages.at(-1)?.content], scrollBottom)
</script>

<template>
  <section
    class="ai-panel"
    :class="{ compact }"
    aria-label="AI 对话"
  >
    <div
      ref="listRef"
      class="message-list"
      aria-live="polite"
    >
      <div
        v-if="!aiStore.messages.length"
        class="welcome-state"
      >
        <van-icon
          name="chat-o"
          size="36"
        />
        <h2>从一句话开始</h2>
        <p>可以查询菜单、菜谱和情侣空间信息；写入操作会先展示确认预览。</p>
      </div>

      <article
        v-for="message in aiStore.messages"
        :key="message.id"
        class="message"
        :class="`message--${message.role}`"
      >
        <p>{{ message.content || (message.streaming ? '正在响应' : '未返回内容') }}</p>
        <span
          v-if="message.streaming"
          class="streaming-dot"
          aria-label="正在生成"
        />
      </article>

      <article
        v-if="preview"
        class="action-preview"
        data-test="ai-action-preview"
      >
        <header>
          <div>
            <p>WRITE PREVIEW</p>
            <h3>{{ preview.title }}</h3>
          </div>
          <span>{{ preview.supported ? '等待确认' : '不可执行' }}</span>
        </header>

        <dl class="preview-meta">
          <div><dt>操作类型</dt><dd>{{ preview.actionType }}</dd></div>
          <div><dt>影响对象</dt><dd>{{ preview.target }}</dd></div>
          <div><dt>来源</dt><dd>{{ preview.source }}</dd></div>
        </dl>

        <section
          class="field-diff"
          aria-label="字段变更"
        >
          <h4>字段变更</h4>
          <div
            v-if="preview.fields.length"
            class="diff-table"
          >
            <div
              v-for="field in preview.fields"
              :key="field.field"
            >
              <strong>{{ field.label }}</strong>
              <span>{{ field.before }}</span>
              <van-icon name="arrow" />
              <b>{{ field.after }}</b>
            </div>
          </div>
          <p v-else>
            没有可展示的字段。
          </p>
        </section>

        <p
          v-if="!preview.supported"
          class="preview-warning"
        >
          此写操作不在可确认范围内，仅支持添加菜单或创建菜谱。
        </p>
        <p
          v-else-if="!aiStore.sessionId"
          class="preview-warning"
        >
          尚未收到会话标识，本次预览不可确认，请重新发起并再次核对。
        </p>
        <p
          v-if="aiStore.confirmationOutcomeUnknown"
          class="preview-warning"
          role="alert"
        >
          确认结果未知，请先刷新相关菜单或菜谱核对，不要重复确认。
        </p>

        <div class="preview-actions">
          <button
            type="button"
            data-test="ai-reject"
            :disabled="!aiStore.canReject"
            @click="aiStore.rejectPending"
          >
            拒绝
          </button>
          <button
            type="button"
            data-test="ai-confirm"
            :disabled="!aiStore.canConfirm"
            @click="aiStore.confirmPending"
          >
            {{ aiStore.state === 'confirming' ? '确认中' : '确认写入' }}
          </button>
        </div>
      </article>

      <div
        v-if="aiStore.state === 'interrupted'"
        class="stream-notice"
        role="status"
      >
        <p>回复已中断，当前片段仅保存在本机，服务端不支持续传。</p>
        <button
          v-if="aiStore.canRetry"
          type="button"
          data-test="ai-retry"
          @click="aiStore.retryLastMessage"
        >
          重新发送
        </button>
      </div>
      <div
        v-else-if="aiStore.state === 'error' && !aiStore.confirmationOutcomeUnknown"
        class="stream-notice"
        role="alert"
      >
        <p>AI 请求失败，输入和已有消息已保留。</p>
        <button
          v-if="aiStore.canRetry"
          type="button"
          data-test="ai-retry"
          @click="aiStore.retryLastMessage"
        >
          重试
        </button>
      </div>
    </div>

    <footer class="composer">
      <textarea
        v-model="aiStore.draft"
        rows="1"
        placeholder="给我们的星球留言"
        :disabled="Boolean(aiStore.pendingAction) || aiStore.state === 'confirming'"
        @keydown.enter.exact.prevent="send"
      />
      <button
        v-if="aiStore.canStop"
        type="button"
        class="stop-button"
        aria-label="停止生成"
        @click="aiStore.stopStreaming"
      >
        <van-icon name="stop-circle-o" />
      </button>
      <button
        v-else
        type="button"
        class="send-button"
        aria-label="发送消息"
        :disabled="!aiStore.canSend || isBusy"
        @click="send"
      >
        <van-icon name="guide-o" />
      </button>
    </footer>
  </section>
</template>

<style lang="scss" scoped>
.ai-panel { display: flex; min-height: 0; flex: 1; flex-direction: column; }
.message-list { flex: 1; overflow-y: auto; padding: $space-5 0; }
.welcome-state { display: grid; max-width: 360px; min-height: 300px; place-items: center; align-content: center; gap: $space-3; margin: auto; color: $cosmos-text-muted; text-align: center; }
.welcome-state h2 { color: $cosmos-text; font-size: $fs-title; }
.message { display: flex; align-items: flex-end; width: fit-content; max-width: min(86%, 620px); min-height: 44px; margin-bottom: $space-3; padding: $space-3 $space-4; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; white-space: pre-wrap; overflow-wrap: anywhere; }
.message--user { margin-left: auto; border-color: rgba(255,93,115,.6); background: $cosmos-primary; color: #fff; }
.message--assistant { margin-right: auto; }
.streaming-dot { width: 7px; height: 7px; margin: 0 0 5px $space-2; border-radius: 50%; background: $cosmos-secondary; animation: pulse $cosmos-duration-base infinite alternate; }
.action-preview { margin: $space-5 0; padding: $space-4; border: 1px solid rgba(84,232,211,.55); border-radius: 8px; background: rgba(84,232,211,.06); }
.action-preview header { display: flex; gap: $space-3; align-items: flex-start; justify-content: space-between; }
.action-preview header p { color: $cosmos-secondary; font-size: $fs-caption; }
.action-preview header h3 { margin-top: $space-1; font-size: $fs-title; }
.action-preview header > span { padding: $space-1 $space-2; border-radius: 4px; background: $cosmos-secondary; color: #062421; font-size: $fs-caption; white-space: nowrap; }
.preview-meta { display: grid; gap: $space-2; margin-top: $space-4; }
.preview-meta div { display: grid; grid-template-columns: 84px minmax(0,1fr); gap: $space-2; }
.preview-meta dt { color: $cosmos-text-muted; }
.preview-meta dd { overflow-wrap: anywhere; }
.field-diff { margin-top: $space-4; padding-top: $space-4; border-top: 1px solid $cosmos-border; }
.field-diff h4 { margin-bottom: $space-2; color: $cosmos-gold; }
.diff-table { display: grid; gap: $space-2; }
.diff-table > div { display: grid; grid-template-columns: minmax(70px,.7fr) minmax(64px,1fr) 18px minmax(64px,1fr); gap: $space-2; align-items: center; font-size: $fs-caption; }
.diff-table span { color: $cosmos-text-muted; }
.diff-table b { overflow-wrap: anywhere; color: $cosmos-secondary; }
.preview-warning, .stream-notice { margin-top: $space-3; color: $cosmos-gold; font-size: $fs-caption; }
.preview-actions { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3; margin-top: $space-4; }
.preview-actions button, .stream-notice button { min-height: 44px; border: 1px solid $cosmos-primary; border-radius: 6px; background: transparent; color: $cosmos-primary; }
.preview-actions button:last-child { background: $cosmos-primary; color: #fff; }
button:disabled { opacity: .42; cursor: not-allowed; }
.stream-notice { padding: $space-3; border-left: 3px solid $cosmos-gold; background: rgba(255,200,87,.06); }
.stream-notice button { margin-top: $space-2; padding: 0 $space-4; }
.composer { display: grid; grid-template-columns: minmax(0,1fr) 48px; gap: $space-2; padding: $space-3; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface-raised; }
.composer textarea { min-width: 0; max-height: 120px; padding: $space-2; resize: vertical; border: 0; outline: 0; background: transparent; color: $cosmos-text; font: inherit; }
.composer button { display: grid; width: 48px; height: 48px; place-items: center; border: 0; border-radius: 50%; color: #fff; }
.send-button { background: $cosmos-primary; }
.stop-button { background: $color-error; }
@keyframes pulse { to { opacity: .2; } }
@media (prefers-reduced-motion: reduce) { .streaming-dot { animation: none; } }
</style>
