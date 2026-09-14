<script setup>
import { computed, onMounted, ref } from 'vue'
import { showToast } from 'vant'
import { adminApi } from '@/api'
import { logUiEvent } from '@/composables/useStructuredLog'

const date = new Date().toISOString().slice(0, 10)
const loading = ref(true)
const error = ref('')
const report = ref({ views: 0, cartAdds: 0, orders: 0, completed: 0, cancelled: 0, conversionRate: 0, singleModeRatio: 0 })
const hourly = ref([])
const audits = ref([])
const orders = ref([])
const imports = ref([])

const pendingReviews = computed(() => audits.value.filter(item => item.operation === 'catalog.review'))
const statusLabel = status => ({ pending: '待处理', confirmed: '已确认', cancelled: '已取消', completed: '已完成' }[status] || status || '未知')
const unwrap = (response, fallback) => response?.data ?? fallback

const load = async () => {
  loading.value = true
  error.value = ''
  const startedAt = Date.now()
  try {
    const result = await Promise.allSettled([
      adminApi.getDailyReport(date), adminApi.getHourlyReport(date), adminApi.getAudit(),
      adminApi.getOrders(), adminApi.getCatalogImports()
    ])
    const [daily, hourlyResult, auditResult, orderResult, importResult] = result
    if (daily.status === 'fulfilled') report.value = unwrap(daily.value, report.value)
    if (hourlyResult.status === 'fulfilled') hourly.value = unwrap(hourlyResult.value, { items: [] }).items || []
    if (auditResult.status === 'fulfilled') audits.value = unwrap(auditResult.value, { items: [] }).items || []
    if (orderResult.status === 'fulfilled') orders.value = unwrap(orderResult.value, { items: [] }).items || []
    if (importResult.status === 'fulfilled') imports.value = unwrap(importResult.value, { items: [] }).items || []
    if (result.every(item => item.status === 'rejected')) throw result[0].reason
    logUiEvent('admin.dashboard.load', { module: 'admin', operation: 'load_dashboard', result: 'success', durationMs: Date.now() - startedAt })
  } catch (cause) {
    error.value = cause?.message || '后台数据暂时不可用'
    logUiEvent('admin.dashboard.load', { module: 'admin', operation: 'load_dashboard', result: 'error', durationMs: Date.now() - startedAt, errorCode: cause?.code || 'ADMIN_DASHBOARD_LOAD_FAILED' })
  } finally { loading.value = false }
}

const approve = async (item, approved) => {
  try {
    await adminApi.reviewCatalog({ slug: item.target || item.slug, approved, reason: approved ? '后台审核通过' : '后台审核驳回' })
    showToast(approved ? '已通过审核' : '已驳回来源')
    await load()
  } catch (cause) { showToast(cause?.message || '审核失败') }
}

const flag = async order => {
  try { await adminApi.flagOrder(order.orderId || order.id, { flagged: !order.flagged, reason: '后台人工标记' }); await load() } catch (cause) { showToast(cause?.message || '标记失败') }
}

onMounted(load)
</script>

<template>
  <main class="admin-dashboard">
    <header class="dashboard-header"><div><p class="eyebrow">COUPLE COSMOS / CONTROL ROOM</p><h1>运营指挥台</h1><p class="muted">{{ date }} · 菜品、订单与体验数据</p></div><button class="refresh" type="button" @click="load">刷新数据</button></header>
    <p v-if="loading" class="state" role="status">正在同步运营数据…</p>
    <p v-else-if="error" class="state error" role="alert">{{ error }} <button type="button" @click="load">重试</button></p>
    <template v-else>
      <section class="metrics" aria-label="今日核心指标">
        <article><span>菜品浏览</span><strong>{{ report.views }}</strong><small>转化 {{ report.conversionRate }}%</small></article>
        <article><span>加入购物车</span><strong>{{ report.cartAdds }}</strong><small>单人模式 {{ report.singleModeRatio }}%</small></article>
        <article><span>订单创建</span><strong>{{ report.orders }}</strong><small>完成 {{ report.completed }}</small></article>
        <article><span>取消订单</span><strong>{{ report.cancelled }}</strong><small>需关注异常</small></article>
      </section>
      <section class="dashboard-grid">
        <article class="panel panel--wide"><div class="panel-heading"><h2>菜品来源审核</h2><span>{{ pendingReviews.length }} 条记录</span></div><div v-if="pendingReviews.length" class="review-list"><div v-for="item in pendingReviews" :key="item.id || item.target" class="review-row"><div><strong>{{ item.target }}</strong><small>{{ item.reviewStatus || item.result }} · {{ item.createdAt }}</small></div><div class="actions"><button data-test="catalog-approve" type="button" @click="approve(item, true)">通过</button><button type="button" class="quiet" @click="approve(item, false)">驳回</button></div></div></div><p v-else class="empty">暂无待处理审核</p></article>
        <article class="panel"><div class="panel-heading"><h2>订单监控</h2><span>{{ orders.length }} 笔</span></div><div v-if="orders.length" class="order-list"><div v-for="order in orders" :key="order.orderId || order.id" class="order-row"><div><strong>{{ order.orderId || order.id }}</strong><small>{{ statusLabel(order.status) }} · ¥{{ order.totalAmount || order.total || '0.00' }}</small></div><button type="button" :class="{ flagged: order.flagged }" @click="flag(order)">{{ order.flagged ? '取消标记' : '标记' }}</button></div></div><p v-else class="empty">暂无订单</p></article>
        <article class="panel"><div class="panel-heading"><h2>审计轨迹</h2><span>{{ audits.length }} 条</span></div><div class="audit-list"><div v-for="item in audits.slice(0, 8)" :key="item.id" class="audit-row"><strong>{{ item.operation }}</strong><span>{{ item.target || '系统' }}</span><small>{{ item.createdAt }}</small></div><p v-if="!audits.length" class="empty">暂无操作记录</p></div></article>
        <article class="panel"><div class="panel-heading"><h2>导入批次</h2><span>{{ imports.length }} 批</span></div><div class="audit-list"><div v-for="item in imports.slice(0, 8)" :key="item.id || item.target" class="audit-row"><strong>{{ item.target || item.source || 'catalog' }}</strong><span>成功 {{ item.imported || 0 }} / 失败 {{ item.failed || 0 }}</span><small>{{ item.createdAt }}</small></div><p v-if="!imports.length" class="empty">暂无导入批次</p></div></article>
        <article class="panel panel--wide"><div class="panel-heading"><h2>每小时订单趋势</h2><span>{{ hourly.length }} 个时间段</span></div><div v-if="hourly.length" class="hourly-bars"><div v-for="item in hourly" :key="item.period"><i :style="{ height: `${Math.max(8, Math.min(100, (item.orders || 0) * 20))}%` }" /><small>{{ item.period.slice(11, 16) }}</small></div></div><p v-else class="empty">今日暂无小时级数据</p></article>
      </section>
    </template>
  </main>
</template>

<style lang="scss" scoped>
.admin-dashboard { min-height: 100vh; padding: clamp(20px, 4vw, 48px) clamp(16px, 5vw, 64px) 48px; color: $cosmos-text; background: radial-gradient(circle at 80% 0, rgba(92,66,145,.28), transparent 34%), $cosmos-bg; }
.dashboard-header { display: flex; align-items: flex-start; justify-content: space-between; gap: $space-4; max-width: 1440px; margin: 0 auto $space-6; } .eyebrow { color: $cosmos-secondary; font-size: $fs-caption; letter-spacing: .1em; } h1 { margin: $space-2 0; font-size: clamp(28px, 5vw, 48px); } h2 { font-size: $fs-title; } .muted, small, .panel-heading span { color: $cosmos-text-muted; font-size: $fs-caption; } button { min-height: 40px; padding: 0 $space-3; border: 0; border-radius: $radius-pill; background: $cosmos-primary; color: #fff; font: inherit; font-weight: $fw-semibold; cursor: pointer; } .refresh { border: 1px solid $cosmos-border; background: transparent; }
.metrics, .dashboard-grid { display: grid; gap: $space-4; max-width: 1440px; margin: 0 auto; } .metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: $space-4; } .metrics article, .panel { border: 1px solid $cosmos-border; border-radius: $radius-lg; background: rgba(20,27,51,.78); box-shadow: $shadow-sm; backdrop-filter: blur(12px); } .metrics article { display: grid; gap: $space-2; padding: $space-5; } .metrics span { color: $cosmos-text-muted; font-size: $fs-label; } .metrics strong { font-size: clamp(28px, 4vw, 40px); } .metrics small { color: $cosmos-secondary; }
.dashboard-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .panel { min-width: 0; padding: $space-5; } .panel--wide { grid-column: span 2; } .panel-heading { display: flex; align-items: center; justify-content: space-between; gap: $space-3; margin-bottom: $space-4; } .review-list, .order-list, .audit-list { display: grid; gap: 1px; overflow: hidden; border: 1px solid $cosmos-border; border-radius: $radius-md; background: $cosmos-border; } .review-row, .order-row, .audit-row { display: flex; align-items: center; justify-content: space-between; gap: $space-3; padding: $space-3; background: $cosmos-surface; } .review-row div:first-child, .order-row div:first-child { display: grid; gap: 2px; min-width: 0; } .review-row strong, .order-row strong, .audit-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .actions { display: flex; gap: $space-2; flex: 0 0 auto; } .quiet, .order-row button { min-height: 34px; padding: 0 $space-2; background: transparent; border: 1px solid $cosmos-border; } .order-row button.flagged { border-color: $cosmos-gold; color: $cosmos-gold; } .audit-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto; gap: $space-2; } .audit-row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: $cosmos-secondary; font-size: $fs-caption; } .empty, .state { padding: $space-6; color: $cosmos-text-muted; text-align: center; } .state { max-width: 1440px; margin: 0 auto; } .state.error { color: $color-error; } .state.error button { margin-left: $space-2; } .hourly-bars { display: flex; align-items: end; gap: 6px; min-height: 150px; padding: $space-4; overflow-x: auto; border: 1px solid $cosmos-border; border-radius: $radius-md; background: rgba(6,11,28,.34); } .hourly-bars div { display: grid; flex: 1 0 28px; align-items: end; gap: 4px; height: 120px; text-align: center; } .hourly-bars i { display: block; min-height: 8px; border-radius: 6px 6px 2px 2px; background: linear-gradient($cosmos-secondary, $cosmos-primary); } .hourly-bars small { font-size: 10px; }
@media (max-width: 760px) { .dashboard-header { align-items: stretch; flex-direction: column; } .refresh { width: 100%; } .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } .dashboard-grid { grid-template-columns: 1fr; } .panel--wide { grid-column: span 1; } .panel { padding: $space-4; } .audit-row { grid-template-columns: 1fr; gap: 2px; } .review-row, .order-row { align-items: flex-start; flex-direction: column; } .actions { width: 100%; } .actions button { flex: 1; } }
</style>
