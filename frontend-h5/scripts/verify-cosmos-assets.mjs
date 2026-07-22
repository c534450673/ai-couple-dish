import { createHash } from 'node:crypto'
import { readFile, readdir } from 'node:fs/promises'
import { dirname, extname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const moduleName = 'cosmos-assets'
const scriptDirectory = dirname(fileURLToPath(import.meta.url))
const frontendDirectory = resolve(scriptDirectory, '..')
const projectDirectory = resolve(frontendDirectory, '..')
const manifestPath = resolve(frontendDirectory, 'src/assets/cosmos-manifest.json')
const assetsDirectory = resolve(frontendDirectory, 'src/assets/cosmos')
const licensePath = resolve(projectDirectory, 'docs/legal/assets/cosmos-runtime-assets.md')
const blockedHosts = [
  'lh3.googleusercontent.com',
  'cdn.tailwindcss.com',
  'transparenttextures.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com'
]

const log = (event, result, operation, startedAt, details = {}) => {
  console.info(JSON.stringify({
    event,
    result,
    durationMs: Date.now() - startedAt,
    module: moduleName,
    operation,
    ...details
  }))
}

const sha256 = (content) => createHash('sha256').update(content).digest('hex')

const isAssetPath = (assetPath) => {
  const resolvedPath = resolve(frontendDirectory, assetPath)
  const assetPrefix = `${assetsDirectory}${sep}`

  return resolvedPath.startsWith(assetPrefix) && extname(resolvedPath) === '.webp'
}

const evidenceAnchor = (evidence) => {
  const prefix = 'docs/legal/assets/cosmos-runtime-assets.md#'
  if (!evidence.startsWith(prefix)) {
    throw new Error(`非法授权证据引用: ${evidence}`)
  }

  return evidence.slice(prefix.length)
}

const sourceFiles = async (directory) => {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = await Promise.all(entries.map(async (entry) => {
    const entryPath = resolve(directory, entry.name)
    return entry.isDirectory() ? sourceFiles(entryPath) : [entryPath]
  }))

  return files.flat()
}

const verifyManifest = async () => {
  const startedAt = Date.now()
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'))
  const license = await readFile(licensePath, 'utf8')

  if (!Array.isArray(manifest) || manifest.length !== 3) {
    throw new Error('资源清单必须且只能声明三项运行时位图')
  }

  await Promise.all(manifest.map(async (asset) => {
    if (!isAssetPath(asset.path)) {
      throw new Error(`资源路径不在 Cosmos 目录内: ${asset.path}`)
    }
    if (!/^[a-f0-9]{64}$/.test(asset.sha256)) {
      throw new Error(`资源摘要格式无效: ${asset.path}`)
    }
    if (!Array.isArray(asset.usage) || asset.usage.length === 0) {
      throw new Error(`资源用途不能为空: ${asset.path}`)
    }

    const anchor = evidenceAnchor(asset.licenseEvidence)
    if (!license.includes(`## ${anchor}`)) {
      throw new Error(`授权证据锚点不存在: ${anchor}`)
    }

    const bytes = await readFile(resolve(frontendDirectory, asset.path))
    if (sha256(bytes) !== asset.sha256) {
      throw new Error(`资源摘要不匹配: ${asset.path}`)
    }
  }))

  log('cosmos_assets_manifest', 'passed', 'verify_manifest', startedAt, {
    assetCount: manifest.length
  })
}

const verifyBlockedHosts = async () => {
  const startedAt = Date.now()
  const files = await sourceFiles(resolve(frontendDirectory, 'src'))
  const sourceContents = await Promise.all(files.map((file) => readFile(file, 'utf8')))
  const source = sourceContents.join('\n')
  const blockedHost = blockedHosts.find((host) => source.includes(host))

  if (blockedHost) {
    throw new Error('源码包含受禁远程资源主机')
  }

  log('cosmos_assets_source_scan', 'passed', 'scan_source_hosts', startedAt, {
    scannedFileCount: files.length,
    blockedHostCount: blockedHosts.length
  })
}

const startedAt = Date.now()

try {
  await verifyManifest()
  await verifyBlockedHosts()
  log('cosmos_assets_verification', 'passed', 'verify_assets', startedAt)
} catch (error) {
  log('cosmos_assets_verification', 'failed', 'verify_assets', startedAt, {
    error: error instanceof Error ? error.message : '未知校验错误'
  })
  process.exitCode = 1
}
