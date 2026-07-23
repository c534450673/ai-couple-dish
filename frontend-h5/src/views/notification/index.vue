<script setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import AppHeader from '@/components/cosmos/AppHeader.vue'
import AsyncState from '@/components/cosmos/AsyncState.vue'
import { useNotificationStore, NOTIFICATION_FILTERS } from '@/stores/notification'

const FILTER_LABELS = {
  all: '全部',
  interaction: '互动',
  system: '系统',
  ai: 'AI'
}
const TYPE_LABELS = { 1: '系统', 2: '互动', 3: '提醒' }

const notificationStore = useNotificationStore()
const {
  items,
  filter,
  hasMore,
  status,
  errorCode,
  unreadCount,
  unreadStatus,
  isFilterUnavailable,
  readAllPending,
  pendingReadIds
} = storeToRefs(notificationStore)

const formatTime = (value) => {
  if (!value) return '时间未知'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return '时间未知'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  }).format(parsed)
}

onMounted(async () => {
  await Promise.all([
    notificationStore.loadPage({ reset: true }),
    notificationStore.loadUnreadCount()
  ])
})
</script>

<template>
  <div class="notification-page">
    <AppHeader
      title="星际消息"
      subtitle="通知按账号隔离，不提供实时轮询"
    >
      <template #actions>
        <button
          class="read-all"
          data-test="read-all"
          type="button"
          :disabled="readAllPending || items.length === 0"
          @click="notificationStore.markAllAsRead"
        >
          <van-icon name="passed" />
          <span>{{ readAllPending ? '处理中' : '全部已读' }}</span>
        </button>
      </template>
    </AppHeader>

    <main class="notification-content">
      <div class="summary-row">
        <p>
          全部未读
          <strong v-if="unreadStatus === 'success'">{{ unreadCount }}</strong>
          <strong v-else>未知</strong>
        </p>
        <span v-if="unreadStatus === 'error'">未读数获取失败，保留上次可信值</span>
      </div>

      <nav
        class="filters"
        aria-label="通知筛选"
      >
        <button
          v-for="filterName in NOTIFICATION_FILTERS"
          :key="filterName"
          :data-test="`filter-${filterName}`"
          type="button"
          :class="{ active: filter === filterName }"
          @click="notificationStore.setFilter(filterName)"
        >
          {{ FILTER_LABELS[filterName] }}
        </button>
      </nav>

      <section
        v-if="isFilterUnavailable"
        class="state-panel"
        data-test="ai-unavailable"
        role="status"
      >
        <van-icon name="warning-o" />
        <h2>暂不支持 AI 通知筛选</h2>
        <p>服务端没有 AI 通知类型能力，因此未发送列表请求。</p>
      </section>
      <AsyncState
        v-else-if="status === 'loading'"
        status="loading"
        message="正在加载通知"
      />
      <section
        v-else-if="status === 'unauthorized'"
        class="state-panel"
        data-test="notification-unauthorized"
        role="alert"
      >
        <van-icon name="contact" />
        <h2>需要重新登录</h2>
        <p>当前会话无法读取通知，请重新登录。</p>
      </section>
      <AsyncState
        v-else-if="status === 'error'"
        status="error"
        message="通知加载失败，已有可信数据不会被清空"
        @retry="notificationStore.retry"
      />
      <AsyncState
        v-else-if="status === 'empty'"
        status="empty"
        message="当前筛选下没有通知"
      />

      <template v-else>
        <p
          v-if="errorCode"
          class="inline-error"
          role="alert"
        >
          新一页加载失败，已有通知已保留。
          <button
            type="button"
            @click="notificationStore.retry"
          >
            重试
          </button>
        </p>
        <ol class="notification-list">
          <li
            v-for="entry in items"
            :key="entry.id"
          >
            <button
              type="button"
              class="notification-card"
              :class="{ unread: !entry.isRead }"
              :disabled="Boolean(pendingReadIds[entry.id])"
              @click="notificationStore.markAsRead(entry.id)"
            >
              <span
                class="type-icon"
                aria-hidden="true"
              >
                <van-icon :name="entry.type === 2 ? 'like-o' : entry.type === 3 ? 'clock-o' : 'info-o'" />
              </span>
              <span class="notification-copy">
                <span class="notification-meta">
                  <span>{{ TYPE_LABELS[entry.type] || '通知' }}</span>
                  <time>{{ formatTime(entry.createTime) }}</time>
                </span>
                <strong>{{ entry.title }}</strong>
                <span>{{ entry.content }}</span>
              </span>
              <span
                v-if="!entry.isRead"
                class="unread-dot"
                aria-label="未读"
              />
            </button>
          </li>
        </ol>
        <button
          v-if="hasMore"
          class="load-more"
          type="button"
          :disabled="status === 'loading'"
          @click="notificationStore.loadMore"
        >
          加载更多
        </button>
        <p
          v-else
          class="list-end"
        >
          已加载当前筛选的全部通知
        </p>
      </template>
    </main>
  </div>
</template>

<style lang="scss" scoped>
.notification-page { min-height: 100vh; color: $cosmos-text; background: $cosmos-bg; }
.read-all { display: inline-flex; min-height: 40px; padding: 0 $space-3; align-items: center; gap: $space-1; border: 1px solid $cosmos-border; border-radius: 6px; background: $cosmos-surface-raised; color: $cosmos-secondary; }
.read-all:disabled { opacity: .5; }
.notification-content { max-width: 720px; margin: 0 auto; padding: $space-5 $page-padding 96px; }
.summary-row { display: flex; min-height: 36px; align-items: center; justify-content: space-between; gap: $space-3; color: $cosmos-text-muted; font-size: $fs-caption; }
.summary-row strong { margin-left: $space-1; color: $cosmos-gold; font-size: $fs-label; }
.summary-row > span { text-align: right; }
.filters { display: flex; gap: $space-2; margin: $space-3 0 $space-5; overflow-x: auto; }
.filters button { min-width: 72px; min-height: 40px; padding: 0 $space-4; border: 1px solid $cosmos-border; border-radius: 999px; background: transparent; color: $cosmos-text-muted; }
.filters button.active { border-color: $cosmos-primary; background: $cosmos-primary; color: #fff; }
.state-panel { display: grid; min-height: 320px; place-items: center; align-content: center; gap: $space-3; text-align: center; }
.state-panel > i { color: $cosmos-gold; font-size: 42px; }
.state-panel h2 { font-size: $fs-title; }
.state-panel p { max-width: 320px; color: $cosmos-text-muted; }
.notification-list { display: grid; gap: $space-3; list-style: none; }
.notification-card { display: grid; width: 100%; min-height: 112px; padding: $space-4; grid-template-columns: 44px minmax(0,1fr) 8px; gap: $space-3; align-items: start; border: 1px solid $cosmos-border; border-radius: 8px; background: $cosmos-surface; color: $cosmos-text; text-align: left; }
.notification-card.unread { border-left: 3px solid $cosmos-primary; background: $cosmos-surface-raised; }
.type-icon { display: grid; width: 44px; height: 44px; place-items: center; border-radius: 6px; background: rgba(84,232,211,.1); color: $cosmos-secondary; font-size: 22px; }
.notification-copy { display: grid; min-width: 0; gap: $space-1; }
.notification-copy > strong { overflow-wrap: anywhere; }
.notification-copy > span:last-child { display: -webkit-box; overflow: hidden; color: $cosmos-text-muted; font-size: $fs-label; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }
.notification-meta { display: flex; justify-content: space-between; gap: $space-2; color: $cosmos-gold; font-size: $fs-caption; }
.notification-meta time { color: $cosmos-text-muted; white-space: nowrap; }
.unread-dot { width: 8px; height: 8px; margin-top: $space-2; border-radius: 50%; background: $cosmos-primary; }
.load-more { width: 100%; min-height: 44px; margin-top: $space-4; border: 1px solid $cosmos-border; border-radius: 6px; background: $cosmos-surface-raised; color: $cosmos-text; }
.list-end { padding: $space-5; color: $cosmos-text-muted; text-align: center; font-size: $fs-caption; }
.inline-error { display: flex; margin-bottom: $space-3; padding: $space-3; align-items: center; justify-content: space-between; gap: $space-3; border-left: 3px solid $color-error; background: rgba(255,130,145,.08); color: $color-error; font-size: $fs-caption; }
.inline-error button { min-height: 36px; padding: 0 $space-3; border: 1px solid $color-error; border-radius: 6px; background: transparent; color: $color-error; }
@media (max-width: 360px) { .read-all span { display: none; } .summary-row { align-items: flex-start; flex-direction: column; } }
</style>
