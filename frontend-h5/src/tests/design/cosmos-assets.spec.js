import { execFile as execFileCallback } from 'node:child_process'
import { createHash } from 'node:crypto'
import { readFile, symlink, unlink, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { promisify } from 'node:util'
import { describe, expect, it } from 'vitest'

const execFile = promisify(execFileCallback)
const manifestPath = resolve(process.cwd(), 'src/assets/cosmos-manifest.json')
const indexPath = resolve(process.cwd(), 'index.html')
const cosmosDirectory = resolve(process.cwd(), 'src/assets/cosmos')
const sourceProbePath = resolve(process.cwd(), 'src/.cosmos-host-probe.js')
const host = ['fonts', 'googleapis', 'com'].join('.')

const runVerifier = async () => {
  try {
    return (await execFile('node', ['scripts/verify-cosmos-assets.mjs'], {
      cwd: process.cwd()
    })).stdout
  } catch (error) {
    return error.stdout
  }
}

const sha256 = (content) => createHash('sha256').update(content).digest('hex')

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
    const stdout = await runVerifier()

    expect(stdout).toContain('"event":"cosmos_assets_verification"')
    expect(stdout).toContain('"result":"passed"')
  })

  it('扫描入口 HTML 中的受禁运行时主机', async () => {
    const original = await readFile(indexPath, 'utf8')
    await writeFile(indexPath, `${original}\n<link href="https://${host}/css2" rel="stylesheet">\n`)

    try {
      const stdout = await runVerifier()
      expect(stdout).toContain('"result":"failed"')
    } finally {
      await writeFile(indexPath, original)
    }
  })

  it('扫描 src 中的受禁运行时主机', async () => {
    await writeFile(sourceProbePath, `export default 'https://${host}/css2'\n`)

    try {
      const stdout = await runVerifier()
      expect(stdout).toContain('"result":"failed"')
    } finally {
      await unlink(sourceProbePath)
    }
  })

  it('拒绝通过符号链接逃出 Cosmos 目录的清单路径', async () => {
    const original = await readFile(manifestPath, 'utf8')
    const manifest = JSON.parse(original)
    const linkedPath = resolve(cosmosDirectory, 'escape.webp')
    const outsideBytes = await readFile(resolve(process.cwd(), 'src/assets/images/logo.png'))

    manifest[0].path = 'src/assets/cosmos/escape.webp'
    manifest[0].sha256 = sha256(outsideBytes)
    await symlink('../images/logo.png', linkedPath)
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)

    try {
      const stdout = await runVerifier()
      expect(stdout).toContain('"result":"failed"')
    } finally {
      await unlink(linkedPath)
      await writeFile(manifestPath, original)
    }
  })

  it('拒绝 Cosmos 目录中未登记的第四张 WebP', async () => {
    const extraPath = resolve(cosmosDirectory, 'unexpected.webp')
    await writeFile(extraPath, 'unexpected asset')

    try {
      const stdout = await runVerifier()
      expect(stdout).toContain('"result":"failed"')
    } finally {
      await unlink(extraPath)
    }
  })

  it('要求授权锚点精确匹配 Markdown 二级标题', async () => {
    const original = await readFile(manifestPath, 'utf8')
    const manifest = JSON.parse(original)
    manifest[0].licenseEvidence = 'docs/legal/assets/cosmos-runtime-assets.md#food'
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)

    try {
      const stdout = await runVerifier()
      expect(stdout).toContain('"result":"failed"')
    } finally {
      await writeFile(manifestPath, original)
    }
  })

  it('失败日志只输出固定错误码和阶段', async () => {
    const original = await readFile(manifestPath, 'utf8')
    const manifest = JSON.parse(original)
    const invalidPath = 'src/assets/not-cosmos.webp'
    manifest[0].path = invalidPath
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)

    try {
      const stdout = await runVerifier()
      expect(stdout).toContain('"result":"failed"')
      expect(stdout).toContain('"errorCode":')
      expect(stdout).toContain('"stage":')
      expect(stdout).not.toContain('"error":')
      expect(stdout).not.toContain(invalidPath)
      expect(stdout).not.toContain(process.cwd())
    } finally {
      await writeFile(manifestPath, original)
    }
  })

  it('通过可复用 CSS 资源类将三张 WebP 纳入生产依赖图', async () => {
    const main = await readFile('src/assets/styles/main.scss', 'utf8')

    expect(main).toContain('.cosmos-media')
    expect(main).toContain("url('../cosmos/food-hero.webp')")
    expect(main).toContain("url('../cosmos/partner-avatar.webp')")
    expect(main).toContain("url('../cosmos/place-restaurant.webp')")
  })
})
