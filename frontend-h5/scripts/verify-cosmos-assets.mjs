import { createHash } from 'node:crypto'
import { lstat, readFile, readdir, realpath } from 'node:fs/promises'
import { dirname, extname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const moduleName = 'cosmos-assets'
const scriptDirectory = dirname(fileURLToPath(import.meta.url))
const frontendDirectory = resolve(scriptDirectory, '..')
const projectDirectory = resolve(frontendDirectory, '..')
const manifestPath = resolve(frontendDirectory, 'src/assets/cosmos-manifest.json')
const assetsDirectory = resolve(frontendDirectory, 'src/assets/cosmos')
const licensePath = resolve(projectDirectory, 'docs/legal/assets/cosmos-runtime-assets.md')
const sourceEntries = [
  resolve(frontendDirectory, 'index.html'),
  resolve(frontendDirectory, 'public'),
  resolve(frontendDirectory, 'src')
]
const blockedHosts = [
  'lh3.googleusercontent.com',
  'cdn.tailwindcss.com',
  'transparenttextures.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com'
]
const errorCodes = Object.freeze({
  manifest: 'COSMOS_MANIFEST_INVALID',
  assetPath: 'COSMOS_ASSET_PATH_INVALID',
  assetInventory: 'COSMOS_ASSET_INVENTORY_INVALID',
  authorization: 'COSMOS_AUTHORIZATION_INVALID',
  sourceHost: 'COSMOS_SOURCE_HOST_INVALID',
  sourcePath: 'COSMOS_SOURCE_PATH_INVALID',
  unexpected: 'COSMOS_VERIFICATION_FAILED'
})

class VerificationError extends Error {
  constructor(errorCode, stage) {
    super(errorCode)
    this.errorCode = errorCode
    this.stage = stage
  }
}

const fail = (errorCode, stage) => {
  throw new VerificationError(errorCode, stage)
}

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
const isWithin = (candidate, directory) => candidate.startsWith(`${directory}${sep}`)
const isIgnoredSourcePath = (candidate) => candidate.split(sep).some((part) => (
  part === 'node_modules' || part === 'dist' || part === 'tests'
))

const verifiedTextFile = async (filePath, directory, errorCode, stage) => {
  let metadata
  try {
    metadata = await lstat(filePath)
  } catch {
    fail(errorCode, stage)
  }

  if (!metadata.isFile() || metadata.isSymbolicLink()) {
    fail(errorCode, stage)
  }

  let resolvedFile
  let resolvedDirectory
  try {
    [resolvedFile, resolvedDirectory] = await Promise.all([
      realpath(filePath),
      realpath(directory)
    ])
  } catch {
    fail(errorCode, stage)
  }

  if (!isWithin(resolvedFile, resolvedDirectory)) {
    fail(errorCode, stage)
  }

  try {
    return await readFile(resolvedFile, 'utf8')
  } catch {
    fail(errorCode, stage)
  }
}

const isAssetPath = async (assetPath) => {
  if (typeof assetPath !== 'string' || extname(assetPath) !== '.webp') {
    return null
  }

  const candidate = resolve(frontendDirectory, assetPath)
  const lexicalAssetsPrefix = `${assetsDirectory}${sep}`
  if (!candidate.startsWith(lexicalAssetsPrefix)) {
    return null
  }

  try {
    const [metadata, resolvedAsset, resolvedAssetsDirectory] = await Promise.all([
      lstat(candidate),
      realpath(candidate),
      realpath(assetsDirectory)
    ])

    if (!metadata.isFile() || metadata.isSymbolicLink() || !isWithin(resolvedAsset, resolvedAssetsDirectory)) {
      return null
    }

    return resolvedAsset
  } catch {
    return null
  }
}

const evidenceAnchor = (evidence) => {
  const prefix = 'docs/legal/assets/cosmos-runtime-assets.md#'
  if (typeof evidence !== 'string' || !evidence.startsWith(prefix)) {
    fail(errorCodes.authorization, 'authorization')
  }

  const anchor = evidence.slice(prefix.length)
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(anchor)) {
    fail(errorCodes.authorization, 'authorization')
  }

  return anchor
}

const sourceFiles = async (candidate, rootDirectory) => {
  if (isIgnoredSourcePath(candidate)) {
    return []
  }

  let metadata
  try {
    metadata = await lstat(candidate)
  } catch {
    fail(errorCodes.sourcePath, 'source_scan')
  }

  if (metadata.isSymbolicLink()) {
    fail(errorCodes.sourcePath, 'source_scan')
  }

  let resolvedCandidate
  let resolvedRoot
  try {
    [resolvedCandidate, resolvedRoot] = await Promise.all([
      realpath(candidate),
      realpath(rootDirectory)
    ])
  } catch {
    fail(errorCodes.sourcePath, 'source_scan')
  }

  if (resolvedCandidate !== resolvedRoot && !isWithin(resolvedCandidate, resolvedRoot)) {
    fail(errorCodes.sourcePath, 'source_scan')
  }

  if (metadata.isDirectory()) {
    const entries = await readdir(resolvedCandidate)
    const files = await Promise.all(entries.map((entry) => sourceFiles(resolve(resolvedCandidate, entry), resolvedRoot)))
    return files.flat()
  }

  return metadata.isFile() ? [resolvedCandidate] : []
}

const existingSourceFiles = async () => {
  const files = await Promise.all(sourceEntries.map(async (entry) => {
    try {
      await lstat(entry)
    } catch (error) {
      if (error && error.code === 'ENOENT') {
        return []
      }
      fail(errorCodes.sourcePath, 'source_scan')
    }
    return sourceFiles(entry, entry)
  }))

  return files.flat()
}

const verifyManifest = async () => {
  const startedAt = Date.now()
  let manifest
  try {
    manifest = JSON.parse(await verifiedTextFile(manifestPath, frontendDirectory, errorCodes.manifest, 'manifest'))
  } catch (error) {
    if (error instanceof VerificationError) {
      throw error
    }
    fail(errorCodes.manifest, 'manifest')
  }
  const license = await verifiedTextFile(licensePath, projectDirectory, errorCodes.authorization, 'authorization')

  if (!Array.isArray(manifest) || manifest.length !== 3) {
    fail(errorCodes.manifest, 'manifest')
  }

  const assets = await Promise.all(manifest.map(async (asset) => {
    const resolvedAssetPath = await isAssetPath(asset.path)
    if (!resolvedAssetPath || !/^[a-f0-9]{64}$/.test(asset.sha256)) {
      fail(errorCodes.assetPath, 'manifest')
    }
    if (!Array.isArray(asset.usage) || asset.usage.length === 0) {
      fail(errorCodes.manifest, 'manifest')
    }

    const anchor = evidenceAnchor(asset.licenseEvidence)
    if (!license.split(/\r?\n/).includes(`## ${anchor}`)) {
      fail(errorCodes.authorization, 'authorization')
    }

    let bytes
    try {
      bytes = await readFile(resolvedAssetPath)
    } catch {
      fail(errorCodes.assetPath, 'manifest')
    }
    if (sha256(bytes) !== asset.sha256) {
      fail(errorCodes.assetPath, 'manifest')
    }

    return resolvedAssetPath
  }))

  if (new Set(assets).size !== manifest.length) {
    fail(errorCodes.manifest, 'manifest')
  }

  log('cosmos_assets_manifest', 'passed', 'verify_manifest', startedAt, {
    assetCount: manifest.length,
    stage: 'manifest'
  })
  return assets
}

const verifyAssetInventory = async (manifestAssets) => {
  const startedAt = Date.now()
  let metadata
  let resolvedAssetsDirectory
  try {
    [metadata, resolvedAssetsDirectory] = await Promise.all([
      lstat(assetsDirectory),
      realpath(assetsDirectory)
    ])
  } catch {
    fail(errorCodes.assetInventory, 'inventory')
  }

  if (!metadata.isDirectory() || metadata.isSymbolicLink()) {
    fail(errorCodes.assetInventory, 'inventory')
  }

  const entries = await readdir(resolvedAssetsDirectory)
  const actualAssets = await Promise.all(entries.map(async (entry) => {
    const entryPath = resolve(resolvedAssetsDirectory, entry)
    let entryMetadata
    try {
      entryMetadata = await lstat(entryPath)
    } catch {
      fail(errorCodes.assetInventory, 'inventory')
    }
    if (!entryMetadata.isFile() || entryMetadata.isSymbolicLink() || extname(entryPath) !== '.webp') {
      fail(errorCodes.assetInventory, 'inventory')
    }

    let resolvedEntry
    try {
      resolvedEntry = await realpath(entryPath)
    } catch {
      fail(errorCodes.assetInventory, 'inventory')
    }
    if (!isWithin(resolvedEntry, resolvedAssetsDirectory)) {
      fail(errorCodes.assetInventory, 'inventory')
    }
    return resolvedEntry
  }))

  const expectedAssets = new Set(manifestAssets)
  if (actualAssets.length !== expectedAssets.size || actualAssets.some((asset) => !expectedAssets.has(asset))) {
    fail(errorCodes.assetInventory, 'inventory')
  }

  log('cosmos_assets_inventory', 'passed', 'verify_inventory', startedAt, {
    assetCount: actualAssets.length,
    stage: 'inventory'
  })
}

const verifyBlockedHosts = async () => {
  const startedAt = Date.now()
  const files = await existingSourceFiles()
  const sourceContents = await Promise.all(files.map((file) => readFile(file, 'utf8')))
  const source = sourceContents.join('\n')

  if (blockedHosts.some((host) => source.includes(host))) {
    fail(errorCodes.sourceHost, 'source_scan')
  }

  log('cosmos_assets_source_scan', 'passed', 'scan_source_hosts', startedAt, {
    scannedFileCount: files.length,
    blockedHostCount: blockedHosts.length,
    stage: 'source_scan'
  })
}

const startedAt = Date.now()

try {
  const manifestAssets = await verifyManifest()
  await verifyAssetInventory(manifestAssets)
  await verifyBlockedHosts()
  log('cosmos_assets_verification', 'passed', 'verify_assets', startedAt, { stage: 'complete' })
} catch (error) {
  const verificationError = error instanceof VerificationError
    ? error
    : new VerificationError(errorCodes.unexpected, 'unexpected')
  log('cosmos_assets_verification', 'failed', 'verify_assets', startedAt, {
    errorCode: verificationError.errorCode,
    stage: verificationError.stage
  })
  process.exitCode = 1
}
