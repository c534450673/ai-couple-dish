<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { diningApi } from '@/api'
import { useUserStore } from '@/stores/user'
import { logUiEvent, normalizeUiErrorCode } from '@/composables/useStructuredLog'
import placeRestaurant from '@/assets/cosmos/place-restaurant.webp'

const router = useRouter()
const userStore = useUserStore()
const cuisines = ref([])
const dishes = ref([])
const cart = ref({ items: [], count: 0, totalAmount: '0.00' })
const orders = ref([])
const selectedCuisine = ref('')
const keyword = ref('')
const submittedKeyword = ref('')
const loadState = ref('loading')
const cartState = ref('loading')
const ordersState = ref('loading')
const cartOpen = ref(false)
const remark = ref('')
const submittingOrder = ref(false)
const changingItem = ref(null)
const changingOrder = ref(null)
const lastError = ref(null)
const orderNotice = ref('')

const hasCouple = computed(() => Boolean(userStore.coupleInfo))
const cartItems = computed(() => Array.isArray(cart.value?.items) ? cart.value.items : [])
const cartCount = computed(() => Number(cart.value?.count || cartItems.value.reduce((sum, item) => sum + Number(item.quantity || 0), 0)))
const cartTotal = computed(() => Number(cart.value?.totalAmount || 0).toFixed(2))
const isEmpty = computed(() => loadState.value === 'success' && dishes.value.length === 0)
const displayCuisine = cuisine => typeof cuisine === 'string'
  ? { slug: cuisine, name: cuisine }
  : { slug: cuisine?.slug || cuisine?.name || '', name: cuisine?.name || cuisine?.slug || '' }
const unwrap = response => response?.data ?? response
const errorCode = error => normalizeUiErrorCode(error, 'DINE_NETWORK_ERROR')

const log = (event, startedAt, result, fields = {}) => logUiEvent(event, {
  module: 'dining_h5',
  operation: fields.operation || event.replace('dining.', ''),
  result,
  durationMs: Date.now() - startedAt,
  errorCode: fields.errorCode || 'NONE',
  ...fields
})

const normalizeCuisines = payload => {
  const list = Array.isArray(payload) ? payload : (payload?.items || payload?.records || [])
  return list.map(displayCuisine).filter(item => item.slug && item.name)
}

const loadCuisines = async () => {
  const startedAt = Date.now()
  try {
    cuisines.value = normalizeCuisines(unwrap(await diningApi.getCuisines()))
    log('dining.cuisines', startedAt, 'success', { count: cuisines.value.length })
  } catch (error) {
    log('dining.cuisines', startedAt, 'error', { errorCode: errorCode(error) })
    // 菜系筛选不是点菜主流程，失败时保留“全部”并允许继续浏览。
    cuisines.value = []
  }
}

const loadDishes = async ({ retry = false } = {}) => {
  const startedAt = Date.now()
  loadState.value = 'loading'
  lastError.value = null
  try {
    const payload = unwrap(await diningApi.getDishes({
      ...(selectedCuisine.value ? { cuisine: selectedCuisine.value } : {}),
      ...(submittedKeyword.value ? { keyword: submittedKeyword.value } : {})
    }))
    dishes.value = Array.isArray(payload) ? payload : (payload?.items || payload?.records || [])
    loadState.value = 'success'
    log('dining.load', startedAt, 'success', { count: dishes.value.length, retry })
  } catch (error) {
    loadState.value = 'error'
    lastError.value = error
    log('dining.load', startedAt, 'error', { errorCode: errorCode(error), retry })
  }
}

const loadCart = async () => {
  const startedAt = Date.now()
  cartState.value = 'loading'
  try {
    cart.value = unwrap(await diningApi.getCart()) || { items: [], count: 0, totalAmount: '0.00' }
    cartState.value = 'success'
    log('dining.cart', startedAt, 'success', { count: cartCount.value })
  } catch (error) {
    cartState.value = 'error'
    log('dining.cart', startedAt, 'error', { errorCode: errorCode(error) })
  }
}

const loadOrders = async () => {
  const startedAt = Date.now()
  ordersState.value = 'loading'
  try {
    const payload = unwrap(await diningApi.getOrders())
    orders.value = Array.isArray(payload) ? payload : (payload?.records || payload?.items || [])
    ordersState.value = 'success'
    log('dining.orders', startedAt, 'success', { count: orders.value.length })
  } catch (error) {
    ordersState.value = 'error'
    log('dining.orders', startedAt, 'error', { errorCode: errorCode(error) })
  }
}

const selectCuisine = async cuisine => {
  selectedCuisine.value = cuisine?.slug || cuisine || ''
  logUiEvent('dining.filter', {
    module: 'dining_h5', operation: 'select_cuisine', result: 'selected', durationMs: 0,
    errorCode: 'NONE', cuisine: selectedCuisine.value || 'all'
  })
  await loadDishes()
}

const submitSearch = async () => {
  submittedKeyword.value = keyword.value.trim()
  logUiEvent('dining.search', {
    module: 'dining_h5', operation: 'submit_search', result: 'submitted', durationMs: 0,
    errorCode: 'NONE', hasKeyword: Boolean(submittedKeyword.value)
  })
  await loadDishes()
}

const addDish = async dish => {
  const startedAt = Date.now()
  try {
    await diningApi.addItem({ dishId: Number(dish.id), quantity: 1 })
    await loadCart()
    log('dining.add_item', startedAt, 'success', { dishId: Number(dish.id) })
  } catch (error) {
    log('dining.add_item', startedAt, 'error', { dishId: Number(dish.id), errorCode: errorCode(error) })
  }
}

const toggleCart = () => {
  cartOpen.value = !cartOpen.value
  logUiEvent('dining.cart_toggle', {
    module: 'dining_h5', operation: 'toggle_cart', result: cartOpen.value ? 'opened' : 'closed',
    durationMs: 0, errorCode: 'NONE', count: cartCount.value
  })
}

const updateQuantity = async (item, nextQuantity) => {
  if (changingItem.value === item.id || nextQuantity < 1) return
  const startedAt = Date.now()
  changingItem.value = item.id
  try {
    await diningApi.updateItem(item.id, nextQuantity)
    await loadCart()
    log('dining.cart_quantity', startedAt, 'success', { itemId: item.id, quantity: nextQuantity })
  } catch (error) {
    log('dining.cart_quantity', startedAt, 'error', { itemId: item.id, errorCode: errorCode(error) })
  } finally {
    changingItem.value = null
  }
}

const removeItem = async item => {
  if (changingItem.value === item.id) return
  const startedAt = Date.now()
  changingItem.value = item.id
  try {
    await diningApi.removeItem(item.id)
    await loadCart()
    log('dining.remove_item', startedAt, 'success', { itemId: item.id })
  } catch (error) {
    log('dining.remove_item', startedAt, 'error', { itemId: item.id, errorCode: errorCode(error) })
  } finally {
    changingItem.value = null
  }
}

const clearCart = async () => {
  if (!cartItems.value.length) return
  const startedAt = Date.now()
  try {
    await diningApi.clearCart()
    await loadCart()
    log('dining.clear_cart', startedAt, 'success')
  } catch (error) {
    log('dining.clear_cart', startedAt, 'error', { errorCode: errorCode(error) })
  }
}

const createOrder = async () => {
  if (!cartItems.value.length || submittingOrder.value) return
  const startedAt = Date.now()
  submittingOrder.value = true
  orderNotice.value = ''
  const idempotencyKey = globalThis.crypto?.randomUUID?.() || `h5-${Date.now()}-${Math.random().toString(16).slice(2)}`
  try {
    await diningApi.createOrder({ remark: remark.value.trim() || undefined }, idempotencyKey)
    orderNotice.value = '订单已创建，等待确认'
    remark.value = ''
    const refreshStartedAt = Date.now()
    const refreshResults = await Promise.allSettled([loadCart(), loadOrders()])
    const refreshFailed = refreshResults.some(result => result.status === 'rejected') ||
      cartState.value === 'error' || ordersState.value === 'error'
    if (refreshFailed) {
      logUiEvent('dining.refresh', {
        module: 'dining_h5', operation: 'refresh_after_order', result: 'error',
        durationMs: Date.now() - refreshStartedAt, errorCode: 'DINE_REFRESH_ERROR'
      })
      orderNotice.value = '订单已创建，列表刷新失败，请稍后刷新查看'
    } else {
      logUiEvent('dining.refresh', {
        module: 'dining_h5', operation: 'refresh_after_order', result: 'success',
        durationMs: Date.now() - refreshStartedAt, errorCode: 'NONE'
      })
    }
    log('dining.create_order', startedAt, 'success', { idempotencyKeyGenerated: true })
  } catch (error) {
    orderNotice.value = '订单创建失败，请稍后重试'
    log('dining.create_order', startedAt, 'error', { errorCode: errorCode(error), idempotencyKeyGenerated: true })
  } finally {
    submittingOrder.value = false
  }
}

const transitionOrder = async (item, target) => {
  if (changingOrder.value === item.id || !['pending_confirmation'].includes(item.status)) return
  const startedAt = Date.now()
  changingOrder.value = item.id
  try {
    if (target === 'confirmed') await diningApi.confirmOrder(item.id)
    else await diningApi.cancelOrder(item.id)
    await loadOrders()
    log(`dining.${target === 'confirmed' ? 'confirm_order' : 'cancel_order'}`, startedAt, 'success', { orderId: item.id })
  } catch (error) {
    log(`dining.${target === 'confirmed' ? 'confirm_order' : 'cancel_order'}`, startedAt, 'error', { orderId: item.id, errorCode: errorCode(error) })
  } finally {
    changingOrder.value = null
  }
}

const imageFor = dish => dish?.imageUrl || dish?.coverUrl || placeRestaurant
const displayPrice = dish => Number(dish?.unitPrice ?? dish?.price ?? 0).toFixed(2)
const statusText = order => order.statusDesc || ({ pending_confirmation: '待确认', confirmed: '已确认', cancelled: '已取消' }[order.status] || order.status)

onMounted(async () => {
  const startedAt = Date.now()
  logUiEvent('dining.page_load', { module: 'dining_h5', operation: 'load_page', result: 'started', durationMs: 0, errorCode: 'NONE' })
  await Promise.all([loadCuisines(), loadDishes(), loadCart(), loadOrders()])
  log('dining.page_load', startedAt, 'success', { mode: hasCouple.value ? 'couple' : 'single' })
})
</script>

<template>
  <main class="dining-page">
    <header class="dining-hero">
      <div>
        <p class="dining-eyebrow">COUPLE COSMOS · DINING ORBIT</p>
        <h1>今晚吃什么</h1>
        <p class="dining-subtitle">把想吃的料理放进同一颗星球，随时开始一顿饭。</p>
      </div>
      <button class="dining-back" type="button" aria-label="返回菜单记录" @click="router.push('/menu')">
        <van-icon name="arrow-left" />
        <span>记录</span>
      </button>
    </header>

    <section class="mode-note" :class="{ 'mode-note--couple': hasCouple }" role="status">
      <van-icon :name="hasCouple ? 'friends-o' : 'user-o'" aria-hidden="true" />
      <span>{{ hasCouple ? '情侣共享模式：你们的购物车会保持同步。' : '单人模式可用：先为自己选一顿喜欢的，绑定后可继续共享。' }}</span>
    </section>

    <form class="dining-search" role="search" @submit.prevent="submitSearch">
      <van-icon name="search" aria-hidden="true" />
      <input v-model="keyword" type="search" placeholder="搜索菜名或口味" aria-label="搜索菜名或口味">
      <button type="submit">搜索</button>
    </form>

    <nav class="cuisine-strip" aria-label="菜系筛选">
      <button type="button" :class="{ active: !selectedCuisine }" @click="selectCuisine('')">全部</button>
      <button
        v-for="cuisine in cuisines"
        :key="cuisine.slug"
        :data-test="`cuisine-${cuisine.name}`"
        type="button"
        :class="{ active: selectedCuisine === cuisine.slug }"
        @click="selectCuisine(cuisine)"
      >{{ cuisine.name }}</button>
    </nav>

    <section v-if="loadState === 'loading'" class="dining-state" role="status">
      <span class="dining-spinner" aria-hidden="true" />
      <p>正在扫描可用菜品…</p>
    </section>
    <section v-else-if="loadState === 'error'" class="dining-state" role="alert">
      <van-icon name="warning-o" size="32" />
      <h2>菜品暂时迷路了</h2>
      <p>网络恢复后再试一次，购物车不会被重复提交。</p>
      <button data-test="dining-retry" type="button" @click="logUiEvent('dining.retry', { module: 'dining_h5', operation: 'retry_load', result: 'requested', durationMs: 0, errorCode: 'NONE' }); loadDishes({ retry: true })">重新加载</button>
    </section>
    <section v-else-if="isEmpty" class="dining-state">
      <van-icon name="shop-o" size="32" />
      <h2>这片星区还没有菜品</h2>
      <p>换个菜系或关键词试试。</p>
    </section>
    <section v-else class="dish-grid" aria-live="polite">
      <article v-for="dish in dishes" :key="dish.id" :data-test="`dish-card-${dish.id}`" class="dish-card">
        <div class="dish-card__media">
          <img :src="imageFor(dish)" :alt="dish.name" loading="lazy" width="640" height="420">
          <span v-if="dish.cuisine" class="dish-card__cuisine">{{ dish.cuisine }}</span>
        </div>
        <div class="dish-card__body">
          <div class="dish-card__heading"><h2>{{ dish.name }}</h2><strong>¥{{ displayPrice(dish) }}</strong></div>
          <p v-if="dish.tags?.length" class="dish-card__tags">{{ dish.tags.join(' · ') }}</p>
          <button :data-test="`add-dish-${dish.id}`" class="add-dish" type="button" @click="addDish(dish)">
            <van-icon name="plus" /> 加入购物车
          </button>
        </div>
      </article>
    </section>

    <section class="orders-section" aria-labelledby="orders-title">
      <div class="section-heading"><div><p class="section-kicker">YOUR TABLE</p><h2 id="orders-title">最近订单</h2></div><span>{{ orders.length }} 笔</span></div>
      <div v-if="ordersState === 'loading'" class="orders-muted">同步订单中…</div>
      <div v-else-if="ordersState === 'error'" class="orders-muted">订单暂不可用，稍后刷新页面重试。</div>
      <div v-else-if="!orders.length" class="orders-muted">还没有订单，从一份喜欢的菜开始。</div>
      <article v-for="item in orders" v-else :key="item.id" class="order-card">
        <div><strong>{{ item.orderNo || `订单 #${item.id}` }}</strong><span>{{ statusText(item) }}</span></div>
        <b>¥{{ Number(item.totalAmount || 0).toFixed(2) }}</b>
        <div v-if="item.status === 'pending_confirmation'" class="order-card__actions">
          <button :data-test="`order-confirm-${item.id}`" type="button" :disabled="changingOrder === item.id" @click="transitionOrder(item, 'confirmed')">{{ changingOrder === item.id ? '处理中…' : '确认' }}</button>
          <button :data-test="`order-cancel-${item.id}`" type="button" :disabled="changingOrder === item.id" @click="transitionOrder(item, 'cancelled')">取消</button>
        </div>
      </article>
    </section>

    <button class="cart-fab" type="button" data-test="cart-toggle" @click="toggleCart">
      <van-icon name="shopping-cart-o" /><span>购物车</span><b>{{ cartCount }}</b><strong>¥{{ cartTotal }}</strong>
    </button>

    <div v-if="cartOpen" class="cart-overlay" @click.self="toggleCart">
      <aside class="cart-drawer" data-test="cart-drawer" aria-label="购物车">
        <div class="drawer-heading"><div><p class="section-kicker">YOUR ORBIT</p><h2>购物车</h2></div><button type="button" aria-label="关闭购物车" @click="toggleCart">×</button></div>
        <div v-if="!cartItems.length" class="cart-empty">还没有选中的料理。</div>
        <div v-else class="cart-list">
          <article v-for="item in cartItems" :key="item.id" class="cart-item">
            <div><strong>{{ item.dishName }}</strong><small>¥{{ Number(item.unitPrice || 0).toFixed(2) }} / 份</small></div>
            <div class="quantity-control"><button :disabled="changingItem === item.id" type="button" @click="item.quantity > 1 ? updateQuantity(item, item.quantity - 1) : removeItem(item)">−</button><span>{{ item.quantity }}</span><button :data-test="`cart-increase-${item.id}`" :disabled="changingItem === item.id" type="button" @click="updateQuantity(item, item.quantity + 1)">+</button></div>
          </article>
          <button class="clear-cart" type="button" @click="clearCart">清空购物车</button>
          <label class="remark-field">给这顿饭留句话<textarea v-model="remark" data-test="order-remark" rows="2" maxlength="512" placeholder="例如：少辣、分开装" /></label>
          <div class="checkout-row"><strong>合计 ¥{{ cartTotal }}</strong><button data-test="checkout-submit" type="button" :disabled="submittingOrder" @click="createOrder">{{ submittingOrder ? '提交中…' : '去结算' }}</button></div>
          <p v-if="orderNotice" class="order-notice" role="status">{{ orderNotice }}</p>
        </div>
      </aside>
    </div>
  </main>
</template>

<style lang="scss" scoped>
.dining-page { min-height: 100vh; padding: calc($space-6 + env(safe-area-inset-top)) max($page-padding, 4vw) 128px; color: $cosmos-text; background: radial-gradient(circle at 90% 0%, rgba(84, 232, 211, .12), transparent 34%), $cosmos-bg; }
.dining-hero, .section-heading, .dish-card__heading, .drawer-heading, .checkout-row, .order-card > div:first-child { display: flex; align-items: center; justify-content: space-between; gap: $space-3; }
.dining-hero { max-width: 1180px; margin: 0 auto $space-5; align-items: flex-start; }
.dining-eyebrow, .section-kicker { color: $cosmos-secondary; font-size: $fs-caption; font-weight: $fw-semibold; letter-spacing: .14em; }
.dining-hero h1 { margin-top: $space-2; font-size: clamp(28px, 5vw, 46px); line-height: 1.15; }
.dining-subtitle { max-width: 500px; margin-top: $space-2; color: $cosmos-text-muted; }
.dining-back { display: inline-flex; align-items: center; gap: $space-1; min-height: $cosmos-min-touch-target; padding: 0 $space-3; border: 1px solid $cosmos-border; border-radius: $radius-pill; color: $cosmos-text-muted; background: rgba(20, 27, 51, .64); }
.mode-note, .dining-search, .dish-card, .orders-section { max-width: 1180px; margin-right: auto; margin-left: auto; }
.mode-note { display: flex; gap: $space-2; align-items: center; margin-bottom: $space-4; padding: $space-3 $space-4; border: 1px solid rgba(255, 200, 87, .28); border-radius: $radius-md; color: $cosmos-gold; background: rgba(255, 200, 87, .08); font-size: $fs-caption; }
.mode-note--couple { border-color: rgba(84, 232, 211, .28); color: $cosmos-secondary; background: rgba(84, 232, 211, .08); }
.dining-search { display: grid; grid-template-columns: auto 1fr auto; gap: $space-2; align-items: center; padding: $space-2 $space-3; border: 1px solid $cosmos-border; border-radius: $radius-lg; background: rgba(20, 27, 51, .82); }
.dining-search input { min-width: 0; min-height: 40px; border: 0; outline: 0; color: $cosmos-text; background: transparent; font: inherit; }
.dining-search button, .dining-state button, .checkout-row button { min-height: 40px; padding: 0 $space-4; border: 0; border-radius: $radius-pill; color: #fff; background: $cosmos-primary; font-weight: $fw-semibold; }
.cuisine-strip { display: flex; max-width: 1180px; gap: $space-2; margin: $space-4 auto; overflow-x: auto; padding-bottom: 2px; scrollbar-width: none; }
.cuisine-strip button { flex: 0 0 auto; min-height: 40px; padding: 0 $space-4; border: 1px solid $cosmos-border; border-radius: $radius-pill; color: $cosmos-text-muted; background: rgba(20, 27, 51, .64); }
.cuisine-strip button.active { border-color: $cosmos-secondary; color: $cosmos-bg; background: $cosmos-secondary; }
.dining-state { display: grid; min-height: 300px; place-content: center; justify-items: center; gap: $space-3; color: $cosmos-text-muted; text-align: center; }
.dining-state h2 { color: $cosmos-text; font-size: $fs-title; }
.dining-state p { max-width: 300px; }
.dining-spinner { width: 32px; height: 32px; border: 3px solid $cosmos-border; border-top-color: $cosmos-secondary; border-radius: 50%; animation: cosmos-orbit $cosmos-duration-slow linear infinite; }
.dish-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: $space-4; max-width: 1180px; margin: 0 auto; }
.dish-card, .orders-section { border: 1px solid $cosmos-glass-border; border-radius: $cosmos-card-radius; background: rgba(20, 27, 51, .78); box-shadow: $shadow-card; overflow: hidden; }
.dish-card { max-width: none; margin: 0; }
.dish-card__media { position: relative; aspect-ratio: 16 / 9; overflow: hidden; background: $cosmos-surface-elevated; }
.dish-card__media img { width: 100%; height: 100%; object-fit: cover; }
.dish-card__cuisine { position: absolute; right: $space-3; bottom: $space-3; padding: 3px $space-2; border-radius: $radius-pill; color: $cosmos-text; background: rgba(8, 12, 37, .76); font-size: $fs-caption; }
.dish-card__body { padding: $space-4; }
.dish-card__heading { align-items: flex-start; }
.dish-card h2 { font-size: $fs-title; }
.dish-card strong { color: $cosmos-gold; font-size: $fs-title; white-space: nowrap; }
.dish-card__tags { margin: $space-2 0 $space-3; color: $cosmos-text-muted; font-size: $fs-caption; }
.add-dish { width: 100%; min-height: $cosmos-min-touch-target; border: 1px solid rgba(255, 93, 115, .46); border-radius: $radius-pill; color: $cosmos-primary; background: rgba(255, 93, 115, .08); font-weight: $fw-semibold; }
.orders-section { margin-top: $space-6; padding: $space-5; }
.section-heading { margin-bottom: $space-4; }
.section-heading h2 { margin-top: $space-1; font-size: $fs-title; }
.section-heading > span { color: $cosmos-text-muted; font-size: $fs-caption; }
.orders-muted, .cart-empty { padding: $space-5 0; color: $cosmos-text-muted; text-align: center; }
.order-card { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: $space-2; align-items: center; padding: $space-3 0; border-top: 1px solid $cosmos-border; }
.order-card > div:first-child { justify-content: flex-start; flex-wrap: wrap; }
.order-card > div:first-child span { padding: 2px $space-2; border-radius: $radius-pill; color: $cosmos-secondary; background: rgba(84, 232, 211, .1); font-size: $fs-caption; }
.order-card > b { color: $cosmos-gold; }
.order-card__actions { grid-column: 1 / -1; display: flex; gap: $space-2; }
.order-card__actions button { min-height: 36px; padding: 0 $space-3; border: 1px solid $cosmos-border; border-radius: $radius-pill; color: $cosmos-text-muted; background: transparent; }
.order-card__actions button:first-child { border-color: $cosmos-primary; color: $cosmos-primary; }
.order-card__actions button:disabled { opacity: .5; }
.cart-fab { position: fixed; right: max($page-padding, 4vw); bottom: calc(76px + env(safe-area-inset-bottom)); z-index: 40; display: inline-flex; align-items: center; gap: $space-2; min-height: 52px; padding: 0 $space-4; border: 1px solid rgba(255, 255, 255, .2); border-radius: $radius-pill; color: #fff; background: rgba(255, 93, 115, .92); box-shadow: $shadow-float; }
.cart-fab b { display: grid; width: 24px; height: 24px; place-items: center; border-radius: 50%; color: $cosmos-primary; background: #fff; font-size: $fs-caption; }
.cart-fab strong { color: #fff; }
.cart-overlay { position: fixed; inset: 0; z-index: 100; display: flex; align-items: flex-end; justify-content: flex-end; padding: $space-3; background: rgba(3, 7, 20, .68); }
.cart-drawer { width: min(460px, 100%); max-height: min(80vh, 760px); overflow: auto; padding: $space-5; border: 1px solid $cosmos-glass-border; border-radius: $cosmos-sheet-radius; color: $cosmos-text; background: rgba(20, 27, 51, .96); box-shadow: $shadow-float; }
.drawer-heading { margin-bottom: $space-4; }
.drawer-heading h2 { margin-top: $space-1; font-size: $fs-title; }
.drawer-heading > button { width: 40px; height: 40px; border: 0; border-radius: 50%; color: $cosmos-text; background: $cosmos-surface-elevated; font-size: 24px; }
.cart-item { display: flex; align-items: center; justify-content: space-between; gap: $space-3; padding: $space-3 0; border-top: 1px solid $cosmos-border; }
.cart-item > div:first-child { display: grid; gap: 2px; min-width: 0; }
.cart-item small { color: $cosmos-text-muted; font-size: $fs-caption; }
.quantity-control { display: flex; align-items: center; gap: $space-2; }
.quantity-control button { width: 34px; height: 34px; border: 1px solid $cosmos-border; border-radius: 50%; color: $cosmos-text; background: transparent; font-size: 18px; }
.quantity-control button:disabled { opacity: .45; }
.clear-cart { margin: $space-3 0; border: 0; color: $cosmos-text-muted; background: transparent; font-size: $fs-caption; text-decoration: underline; }
.remark-field { display: grid; gap: $space-2; color: $cosmos-text-muted; font-size: $fs-caption; }
.remark-field textarea { resize: vertical; min-height: 60px; padding: $space-2; border: 1px solid $cosmos-border; border-radius: $radius-md; outline: 0; color: $cosmos-text; background: $cosmos-surface; font: inherit; }
.checkout-row { margin-top: $space-4; }
.checkout-row strong { color: $cosmos-gold; font-size: $fs-title; }
.checkout-row button:disabled { opacity: .5; }
.order-notice { margin-top: $space-3; color: $cosmos-secondary; font-size: $fs-caption; }
@media (max-width: 640px) { .dining-page { padding-right: $space-4; padding-left: $space-4; } .dining-hero { gap: $space-2; } .dining-back span { display: none; } .dish-grid { grid-template-columns: 1fr; } .orders-section { padding: $space-4; border-radius: $radius-lg; } .cart-fab { right: $space-4; } }
@media (min-width: 1200px) { .dining-page { padding-right: 7vw; padding-left: 7vw; } .dish-card__media { aspect-ratio: 1.72; } }
</style>
