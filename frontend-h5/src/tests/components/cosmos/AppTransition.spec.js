/* eslint-disable vue/one-component-per-file */
import { createPinia } from 'pinia'
import { defineComponent, h, nextTick, onMounted, reactive } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const checkLoginStatus = vi.hoisted(() => vi.fn())

vi.mock('@/stores/user', () => ({
  useUserStore: () => ({ checkLoginStatus })
}))

import App from '@/App.vue'

describe('App 页面过渡', () => {
  it('路由 fullPath 改变时重建 Transition 的直接子节点', async () => {
    let boundaryMounts = 0
    const route = reactive({ fullPath: '/home', meta: { shell: true } })
    const Page = defineComponent({ render: () => h('div', '页面') })
    const RouterView = defineComponent({
      setup(_, { slots }) {
        return () => slots.default({ Component: Page, route })
      }
    })
    const ErrorBoundary = defineComponent({
      setup(_, { slots }) {
        onMounted(() => { boundaryMounts += 1 })
        return () => h('div', slots.default?.())
      }
    })

    mount(App, {
      global: {
        plugins: [createPinia()],
        mocks: { $route: route },
        stubs: {
          RouterView,
          ErrorBoundary,
          MainLayout: { template: '<main><slot /></main>' },
          AiAssistantFab: true
        }
      }
    })

    expect(boundaryMounts).toBe(1)
    route.fullPath = '/menu?filter=nearby'
    await nextTick()
    await nextTick()

    expect(boundaryMounts).toBe(2)
  })
})
