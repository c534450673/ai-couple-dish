import { expect, test as contractTest } from './contract'

const mockUser = { id: 1, nickName: '测试用户', nickname: '测试用户', avatarUrl: '' }
const mockCouple = { id: 2, partner: { nickName: '测试伴侣', nickname: '测试伴侣', avatarUrl: '' } }

const applySession = async (page, { authenticated = true, coupled = true } = {}) => {
  await page.addInitScript(({ authenticated: hasSession, coupled: hasCouple, user, couple }) => {
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    localStorage.removeItem('coupleInfo')
    if (!hasSession) return
    localStorage.setItem('token', 'mock-session-token')
    localStorage.setItem('userInfo', JSON.stringify(user))
    if (hasCouple) localStorage.setItem('coupleInfo', JSON.stringify(couple))
  }, { authenticated, coupled, user: mockUser, couple: mockCouple })
}

export const test = contractTest.extend({
  auth: async ({ page }, use) => {
    await applySession(page)
    await use({
      authenticated: () => applySession(page),
      unauthenticated: () => applySession(page, { authenticated: false }),
      unbound: () => applySession(page, { coupled: false }),
      denyGeolocation: () => page.addInitScript(() => {
        Object.defineProperty(navigator, 'geolocation', {
          configurable: true,
          value: { getCurrentPosition: (_success, error) => error({ code: 1, message: 'permission denied' }) }
        })
      })
    })
  }
})

export { expect }
