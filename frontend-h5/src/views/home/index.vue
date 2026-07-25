<script setup>
import { computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import CoupleOrbit from '@/components/home/CoupleOrbit.vue'
import HomeBento from '@/components/home/HomeBento.vue'
import { useReducedMotion } from '@/composables/useReducedMotion'
import { logUiEvent } from '@/composables/useStructuredLog'
import foodHero from '@/assets/cosmos/food-hero.webp'
import { useHomeStore } from '@/stores/home'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const homeStore = useHomeStore()
const userStore = useUserStore()
const prefersReducedMotion = useReducedMotion()
let mounted = false
let activeContextId = 0

const resources = computed(() => homeStore.resources)
const currentAvatar = computed(() => userStore.userInfo?.avatarUrl || '')
const feedText = computed(() => {
  const candidates = [
    resources.value.feed.data?.content,
    resources.value.feed.data?.message
  ]
  const value = candidates.find(candidate => typeof candidate === 'string' && candidate.trim())
  return value ? value.trim() : ''
})
const feedImage = computed(() => {
  const images = resources.value.feed.data?.imageUrls
  return Array.isArray(images) ? images[0] || '' : ''
})

const routeLabel = target => typeof target === 'string'
  ? target
  : `${target.path}${target.query ? `?${new URLSearchParams(target.query)}` : ''}`

const logNavigation = (target) => {
  logUiEvent('home.navigation', {
    targetRoute: routeLabel(target),
    reducedMotion: prefersReducedMotion.value
  })
}

const redirectForAccessFlow = (contextId = activeContextId) => {
  if (!mounted || contextId !== activeContextId) return false
  const states = Object.values(resources.value)
  const targetRoute = states.some(resource => resource.flow === 'login')
    ? '/login'
    : (states.some(resource => resource.flow === 'bind') ? '/bind' : null)
  if (!targetRoute) return false
  logUiEvent('home.access_redirect', {
    state: 'redirect',
    targetRoute,
    reducedMotion: prefersReducedMotion.value
  })
  router.replace(targetRoute)
  return true
}

const retryResource = async (resource) => {
  const contextId = activeContextId
  await homeStore.retryResource(resource)
  redirectForAccessFlow(contextId)
}

onMounted(async () => {
  mounted = true
  const contextId = ++activeContextId
  // 等待应用层用户快照请求先完成，避免 request 去重器取消首页关系摘要。
  await nextTick()
  if (!mounted || contextId !== activeContextId) return
  await homeStore.loadAll()
  redirectForAccessFlow(contextId)
})

onUnmounted(() => {
  homeStore.invalidatePending()
  mounted = false
  activeContextId += 1
})
</script>

<template>
  <div
    class="home-emotion"
    :data-motion="prefersReducedMotion ? 'static' : 'animated'"
  >
    <header class="home-emotion__relationship">
      <CoupleOrbit
        :current-avatar="currentAvatar"
        :couple="resources.couple"
        :timer="resources.timer"
        :reduced-motion="prefersReducedMotion"
        @retry="retryResource"
      />
    </header>

    <main class="home-emotion__content">
      <router-link
        class="home-hero"
        to="/ai"
        data-test="home-hero"
        aria-label="打开 AI 决定今晚吃什么"
        @click="logNavigation('/ai')"
      >
        <img
          data-test="hero-image"
          class="home-hero__image"
          :src="foodHero"
          alt="一桌适合两人分享的料理"
          width="1280"
          height="871"
          fetchpriority="high"
        >
        <span
          class="home-hero__shade"
          aria-hidden="true"
        />
        <span class="home-hero__content">
          <span class="home-hero__eyebrow">TONIGHT WE EAT</span>
          <strong class="home-hero__title">今晚吃什么？</strong>
          <span class="home-hero__cta">
            <van-icon
              name="shop-o"
              aria-hidden="true"
            />
            <span>问 AI</span>
          </span>
        </span>
      </router-link>

      <section
        class="home-bento-grid"
        aria-label="我们的共同空间"
      >
        <HomeBento
          resource-key="recipe"
          title="双方已发布菜谱"
          to="/recipes"
          icon="orders-o"
          accent="gold"
          link-test="recipe-link"
          :resource="resources.recipe"
          @retry="retryResource"
          @navigate="logNavigation"
        >
          <span class="bento-value">{{ resources.recipe.data.total }} 道</span>
          <small
            v-if="resources.recipe.data.item?.title"
            class="bento-detail"
          >
            {{ resources.recipe.data.item.title }}
          </small>
        </HomeBento>

        <HomeBento
          resource-key="footprint"
          title="餐厅地图"
          to="/map"
          icon="location-o"
          accent="violet"
          link-test="footprint-link"
          unavailable-text="不提供到访记录，可打开地图"
          :resource="resources.footprint"
          @navigate="logNavigation"
        />

        <HomeBento
          resource-key="anniversary"
          title="下一个纪念日"
          :to="{ path: '/memories', query: { type: 'anniversary' } }"
          icon="calendar-o"
          accent="coral"
          link-test="anniversary-link"
          :resource="resources.anniversary"
          @retry="retryResource"
          @navigate="logNavigation"
        >
          <span class="bento-value">{{ resources.anniversary.data.name }}</span>
          <small class="bento-detail">
            {{ resources.anniversary.data.daysUntil === 0 ? '就是今天' : `还有 ${resources.anniversary.data.daysUntil} 天` }}
          </small>
        </HomeBento>

        <HomeBento
          resource-key="wish"
          title="最新心愿"
          :to="{ path: '/memories', query: { type: 'wish' } }"
          icon="like-o"
          accent="mint"
          link-test="wish-link"
          :resource="resources.wish"
          @retry="retryResource"
          @navigate="logNavigation"
        >
          <span class="bento-value">{{ resources.wish.data.title }}</span>
          <small
            v-if="resources.wish.data.statusName"
            class="bento-detail"
          >
            {{ resources.wish.data.statusName }}
          </small>
        </HomeBento>
      </section>

      <section
        class="recent-feed"
        aria-labelledby="recent-feed-title"
      >
        <div class="recent-feed__heading">
          <div>
            <p class="recent-feed__eyebrow">
              SHARED MOMENT
            </p>
            <h2 id="recent-feed-title">
              最近动态
            </h2>
          </div>
          <router-link
            class="recent-feed__all"
            to="/feed"
            data-test="feed-link"
            aria-label="查看全部动态"
            @click="logNavigation('/feed')"
          >
            <van-icon
              name="arrow"
              aria-hidden="true"
            />
          </router-link>
        </div>

        <router-link
          v-if="resources.feed.status === 'success' && feedText"
          class="recent-feed__entry"
          to="/feed"
          @click="logNavigation('/feed')"
        >
          <img
            v-if="feedImage"
            class="recent-feed__image"
            data-test="feed-image"
            :src="feedImage"
            alt="最近动态配图"
            width="112"
            height="88"
            loading="lazy"
          >
          <span class="recent-feed__body">
            <span class="recent-feed__text">{{ feedText || '动态内容未填写' }}</span>
            <small
              v-if="resources.feed.degradedSides.length"
              data-test="feed-degraded"
            >
              部分动态暂未加载
            </small>
          </span>
          <van-icon
            name="arrow"
            aria-hidden="true"
          />
        </router-link>

        <div
          v-else
          class="recent-feed__state"
          data-test="feed-state"
          aria-live="polite"
        >
          <span v-if="resources.feed.status === 'loading'">动态加载中</span>
          <span v-else-if="resources.feed.status === 'empty'">暂无动态</span>
          <span v-else-if="resources.feed.status === 'success'">暂无可显示的动态</span>
          <span v-else>动态暂时无法加载</span>
          <button
            v-if="resources.feed.status === 'error'"
            type="button"
            data-test="retry-feed"
            @click="retryResource('feed')"
          >
            重试
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<style lang="scss" scoped>
.home-emotion {
  width: 100%;
  min-height: 100vh;
  min-height: 100dvh;
  overflow-x: clip;
  background:
    radial-gradient(circle at 50% 0%, rgba(42, 42, 74, 0.88) 0, rgba(19, 19, 27, 0.96) 34%, #09090d 72%),
    #09090d;
  color: #e5e1e4;
}

.home-emotion__relationship,
.home-emotion__content {
  width: min(100%, 540px);
  margin: 0 auto;
  padding-right: 20px;
  padding-left: 20px;
}

.home-emotion__relationship {
  padding-top: max(12px, env(safe-area-inset-top));
  padding-bottom: 12px;
}

.home-emotion__content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: calc(94px + env(safe-area-inset-bottom));
}

.home-hero {
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: 1.42;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  background: #201f21;
  color: #fff;
  box-shadow: 0 22px 45px rgba(0, 0, 0, 0.28);
  text-decoration: none;
  transform: translateZ(0);
}

.home-hero:focus-visible,
.recent-feed a:focus-visible,
.recent-feed button:focus-visible {
  outline: 3px solid #54e8d3;
  outline-offset: 3px;
}

.home-hero__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 50% 56%;
  transition: transform 500ms ease;
}

.home-hero:active .home-hero__image {
  transform: scale(1.02);
}

.home-hero__shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(5, 5, 9, 0.08) 25%, rgba(5, 5, 9, 0.9) 100%);
}

.home-hero__content {
  position: absolute;
  right: 18px;
  bottom: 18px;
  left: 18px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 6px 12px;
}

.home-hero__eyebrow {
  grid-column: 1 / -1;
  color: #ffc857;
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0;
}

.home-hero__title {
  min-width: 0;
  font-size: 30px;
  line-height: 1.12;
}

.home-hero__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 76px;
  min-height: 48px;
  padding: 0 12px;
  border-radius: 14px;
  background: #ff5d73;
  box-shadow: 0 0 24px rgba(255, 93, 115, 0.36);
  font-size: 13px;
  font-weight: 800;
}

.home-bento-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.bento-value,
.bento-detail {
  display: block;
}

.bento-detail {
  overflow: hidden;
  margin-top: 4px;
  color: #aaa8b1;
  font-size: 10px;
  font-weight: 500;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-feed {
  padding-top: 8px;
}

.recent-feed__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.recent-feed__eyebrow {
  margin: 0 0 4px;
  color: #54e8d3;
  font-size: 9px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0;
}

.recent-feed h2 {
  margin: 0;
  color: #f8f5f7;
  font-size: 20px;
  line-height: 1.3;
}

.recent-feed__all {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  color: #c7c5ce;
  text-decoration: none;
}

.recent-feed__entry,
.recent-feed__state {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 112px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.06);
  color: #f8f5f7;
  text-decoration: none;
}

.recent-feed__image {
  flex: 0 0 auto;
  width: 112px;
  height: 88px;
  border-radius: 12px;
  object-fit: cover;
}

.recent-feed__body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.recent-feed__text {
  display: -webkit-box;
  overflow: hidden;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.45;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.recent-feed__body small {
  color: #ffc857;
  font-size: 10px;
}

.recent-feed__state {
  justify-content: space-between;
  color: #aaa8b1;
  font-size: 13px;
}

.recent-feed__state button {
  min-width: 56px;
  min-height: 44px;
  border: 0;
  border-radius: 12px;
  background: rgba(255, 93, 115, 0.15);
  color: #ff9da4;
  font-weight: 700;
}

[data-motion='animated'] .home-hero,
[data-motion='animated'] .home-bento-grid,
[data-motion='animated'] .recent-feed {
  animation: home-enter 420ms ease both;
}

[data-motion='animated'] .home-bento-grid { animation-delay: 70ms; }
[data-motion='animated'] .recent-feed { animation-delay: 120ms; }

@keyframes home-enter {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .home-emotion *,
  .home-emotion *::before,
  .home-emotion *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

@media (max-width: 380px) {
  .home-emotion__relationship,
  .home-emotion__content {
    padding-right: 16px;
    padding-left: 16px;
  }

  .home-hero__title { font-size: 27px; }
  .home-hero__cta { min-width: 70px; }
}
</style>
