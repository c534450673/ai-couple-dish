<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { showToast } from 'vant'
import { streamChat, confirmAction, rejectAction } from '@/api/ai'

const props = defineProps({
  visible: { type: Boolean, default: false }
})
const emit = defineEmits(['update:visible'])

const show = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v)
})

const input = ref('')
const sending = ref(false)
const listening = ref(false)
const sessionId = ref('')
const messages = ref([])
const pendingAction = ref(null)
const listRef = ref(null)

let recognition = null
const speechSupported = typeof window !== 'undefined'
  && (window.SpeechRecognition || window.webkitSpeechRecognition)

const initSpeech = () => {
  if (!speechSupported || recognition) return
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  recognition = new SR()
  recognition.lang = 'zh-CN'
  recognition.interimResults = false
  recognition.maxAlternatives = 1
  recognition.onresult = (e) => {
    input.value = e.results[0][0].transcript
    listening.value = false
  }
  recognition.onerror = () => {
    listening.value = false
    showToast('语音识别失败，请重试')
  }
  recognition.onend = () => {
    listening.value = false
  }
}

const toggleVoice = () => {
  if (!speechSupported) {
    showToast('当前浏览器不支持语音输入')
    return
  }
  initSpeech()
  if (listening.value) {
    recognition.stop()
    listening.value = false
    return
  }
  listening.value = true
  recognition.start()
}

const scrollBottom = async () => {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

const sendMessage = async () => {
  const text = input.value.trim()
  if (!text || sending.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  sending.value = true

  const assistantMsg = { role: 'assistant', content: '', streaming: true }
  messages.value.push(assistantMsg)
  await scrollBottom()

  try {
    await streamChat(
      { message: text, sessionId: sessionId.value || undefined },
      {
        onToken: (token) => {
          assistantMsg.content += token
          scrollBottom()
        },
        onPending: (action) => {
          pendingAction.value = action
        },
        onSession: (sid) => {
          sessionId.value = sid
        },
        onDone: () => {
          assistantMsg.streaming = false
        },
        onError: (err) => {
          assistantMsg.content += `\n[错误: ${err}]`
          assistantMsg.streaming = false
          showToast('AI 回复失败')
        }
      }
    )
  } catch (e) {
    assistantMsg.content = '发送失败，请稍后重试'
    assistantMsg.streaming = false
    showToast(e.message || '发送失败')
  } finally {
    sending.value = false
    assistantMsg.streaming = false
    await scrollBottom()
  }
}

const handleConfirm = async () => {
  if (!sessionId.value) return
  try {
    const res = await confirmAction(sessionId.value)
    if (res.code === 200) {
      showToast('操作已确认执行')
      messages.value.push({
        role: 'assistant',
        content: `✅ ${res.data?.message || '操作成功'}（ID: ${res.data?.resourceId}）`
      })
      pendingAction.value = null
    } else {
      showToast(res.message || '确认失败')
    }
  } catch {
    showToast('确认失败')
  }
}

const handleReject = async () => {
  if (sessionId.value) {
    await rejectAction(sessionId.value)
  }
  pendingAction.value = null
  showToast('已取消')
}

watch(show, (v) => {
  if (v) scrollBottom()
})
</script>

<template>
  <van-popup
    v-model:show="show"
    position="bottom"
    round
    :style="{ height: '78vh' }"
    class="ai-chat-popup"
  >
    <div class="ai-chat">
      <header class="ai-chat__header">
        <div>
          <h3>AI 恋爱助手</h3>
          <p>菜单 · 菜谱 · 情侣，一句话搞定</p>
        </div>
        <van-icon
          name="cross"
          size="20"
          @click="show = false"
        />
      </header>

      <div
        ref="listRef"
        class="ai-chat__messages"
      >
        <div
          v-if="messages.length === 0"
          class="ai-chat__empty"
        >
          <van-icon
            name="chat-o"
            size="40"
          />
          <p>试试说：</p>
          <ul>
            <li>「帮我查一下菜单里有没有火锅」</li>
            <li>「添加一家川菜馆，叫XX，想去」</li>
            <li>「帮我写一份番茄炒蛋菜谱」</li>
          </ul>
        </div>

        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="ai-chat__bubble"
          :class="msg.role"
        >
          <div class="content">
            {{ msg.content }}<span
              v-if="msg.streaming"
              class="cursor"
            >|</span>
          </div>
        </div>

        <div
          v-if="pendingAction"
          class="ai-chat__pending"
        >
          <div class="pending-title">
            {{ pendingAction.title }}
          </div>
          <div class="pending-summary">
            {{ pendingAction.summary }}
          </div>
          <div class="pending-actions">
            <van-button
              size="small"
              type="primary"
              round
              @click="handleConfirm"
            >
              确认执行
            </van-button>
            <van-button
              size="small"
              plain
              round
              @click="handleReject"
            >
              取消
            </van-button>
          </div>
        </div>
      </div>

      <footer class="ai-chat__footer">
        <button
          class="voice-btn"
          :class="{ active: listening }"
          type="button"
          :title="listening ? '停止录音' : '语音输入'"
          @click="toggleVoice"
        >
          <van-icon :name="listening ? 'stop-circle-o' : 'audio'" />
        </button>
        <van-field
          v-model="input"
          placeholder="说点什么…"
          :border="false"
          @keyup.enter="sendMessage"
        />
        <van-button
          type="primary"
          round
          size="small"
          :loading="sending"
          :disabled="!input.trim()"
          @click="sendMessage"
        >
          发送
        </van-button>
      </footer>
    </div>
  </van-popup>
</template>

<style lang="scss" scoped>
.ai-chat-popup {
  background: $color-background;
}

.ai-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ai-chat__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px 20px 12px;
  border-bottom: 1px solid $color-outline-variant;

  h3 {
    margin: 0;
    font-size: 18px;
    color: $color-primary;
  }

  p {
    margin: 4px 0 0;
    font-size: 12px;
    color: $color-on-surface-variant;
  }
}

.ai-chat__messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.ai-chat__empty {
  text-align: center;
  color: $color-on-surface-variant;
  padding: 24px 12px;

  p { margin: 12px 0 8px; }

  ul {
    text-align: left;
    font-size: 13px;
    line-height: 1.8;
    padding-left: 20px;
  }
}

.ai-chat__bubble {
  display: flex;
  margin-bottom: 12px;

  &.user {
    justify-content: flex-end;

    .content {
      background: $color-primary;
      color: $color-on-primary;
      border-radius: 16px 16px 4px 16px;
    }
  }

  &.assistant {
    justify-content: flex-start;

    .content {
      background: $color-surface-lowest;
      color: $color-on-surface;
      border-radius: 16px 16px 16px 4px;
      box-shadow: 0 2px 8px rgba($color-primary, 0.08);
    }
  }

  .content {
    max-width: 85%;
    padding: 10px 14px;
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .cursor {
    animation: blink 1s step-end infinite;
  }
}

@keyframes blink {
  50% { opacity: 0; }
}

.ai-chat__pending {
  background: $color-primary-container;
  border-radius: $radius-lg;
  padding: 14px;
  margin-top: 8px;

  .pending-title {
    font-weight: 600;
    color: $color-on-primary-container;
  }

  .pending-summary {
    font-size: 13px;
    margin: 6px 0 12px;
    color: $color-on-primary-container;
  }

  .pending-actions {
    display: flex;
    gap: 8px;
  }
}

.ai-chat__footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 16px;
  border-top: 1px solid $color-outline-variant;
  background: $color-surface-lowest;

  :deep(.van-field) {
    flex: 1;
    background: $color-surface-container;
    border-radius: 24px;
    padding: 4px 12px;
  }
}

.voice-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: $color-surface-container;
  color: $color-primary;
  display: flex;
  align-items: center;
  justify-content: center;

  &.active {
    background: $color-primary;
    color: $color-on-primary;
    animation: pulse 1.2s ease-in-out infinite;
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.06); }
}
</style>
