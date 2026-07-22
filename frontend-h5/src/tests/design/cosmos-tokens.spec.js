import { readFile } from 'node:fs/promises'
import { execFile as execFileCallback } from 'node:child_process'
import { resolve } from 'node:path'
import { promisify } from 'node:util'
import { describe, expect, it } from 'vitest'

const stylesDirectory = resolve(process.cwd(), 'src/assets/styles')
const execFile = promisify(execFileCallback)

const negativeLetterSpacing = async () => {
  try {
    return (await execFile('rg', ['-n', 'letter-spacing\\s*:\\s*-', 'src'], {
      cwd: process.cwd()
    })).stdout
  } catch (error) {
    if (error.code === 1) {
      return ''
    }
    throw error
  }
}

describe('Couple Cosmos 设计令牌', () => {
  it('提供深色 Cosmos 色彩和圆角令牌', async () => {
    const css = await readFile(resolve(stylesDirectory, 'tokens.scss'), 'utf8')

    expect(css).toContain('$cosmos-primary: #ff5d73')
    expect(css).toContain('$cosmos-secondary: #54e8d3')
    expect(css).toContain('$cosmos-gold: #ffc857')
    expect(css).toContain('$cosmos-card-radius: 24px')
    expect(css).toContain('$cosmos-sheet-radius: 28px')
    expect(css).toContain("$font-family-base: 'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif")
    expect(css).not.toContain('#fff8f5')
  })

  it('公开匹配的 CSS 变量与可访问动效降级', async () => {
    const [tokens, main, motion] = await Promise.all([
      readFile(resolve(stylesDirectory, 'tokens.scss'), 'utf8'),
      readFile(resolve(stylesDirectory, 'main.scss'), 'utf8'),
      readFile(resolve(stylesDirectory, 'motion.scss'), 'utf8')
    ])

    expect(tokens).toContain('$cosmos-bg')
    expect(main).toContain('--cosmos-primary')
    expect(main).toContain('--cosmos-secondary')
    expect(main).toContain('--cosmos-gold')
    expect(motion).toContain('@keyframes cosmos-fade')
    expect(motion).toContain('@keyframes cosmos-rise')
    expect(motion).toContain('@keyframes cosmos-breathe')
    expect(motion).toContain('@keyframes cosmos-orbit')
    expect(motion).toContain('@media (prefers-reduced-motion: reduce)')
    expect(motion).toMatch(/animation-duration:\s*0\.01ms\s*!important/)
  })

  it('为中文全局字距归零且 src 中不存在负字距', async () => {
    const main = await readFile(resolve(stylesDirectory, 'main.scss'), 'utf8')

    expect(main).toMatch(/body\s*\{[\s\S]*letter-spacing:\s*0;/)
    expect(await negativeLetterSpacing()).toBe('')
  })
})
