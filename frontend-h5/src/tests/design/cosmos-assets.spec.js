import { execFile as execFileCallback } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import { promisify } from 'node:util'
import { describe, expect, it } from 'vitest'

const execFile = promisify(execFileCallback)

describe('Couple Cosmos 运行时资源', () => {
  it('资源清单仅声明三张本地 WebP 位图', async () => {
    const manifest = JSON.parse(await readFile('src/assets/cosmos-manifest.json', 'utf8'))

    expect(manifest).toHaveLength(3)
    expect(manifest.map(({ path }) => path).sort()).toEqual([
      'src/assets/cosmos/food-hero.webp',
      'src/assets/cosmos/partner-avatar.webp',
      'src/assets/cosmos/place-restaurant.webp'
    ])
    for (const item of manifest) {
      expect(item.sha256).toMatch(/^[a-f0-9]{64}$/)
      expect(item.licenseEvidence).toContain('docs/legal/assets/cosmos-runtime-assets.md#')
      expect(item.usage.length).toBeGreaterThan(0)
    }
  })

  it('资源门禁接受受跟踪的本地资源', async () => {
    const { stdout } = await execFile('node', ['scripts/verify-cosmos-assets.mjs'], {
      cwd: process.cwd()
    })

    expect(stdout).toContain('"event":"cosmos_assets_verification"')
    expect(stdout).toContain('"result":"passed"')
  })
})
