# S4 Review Fix: Encode fallback screenshot URL path segment

## Goal

Fix the open Important finding from the independent S4 review: a fallback HTML image URL must not interpret `#` or `?` in `localId` as a fragment or query string.

## Files

- Modify `tools/stitch/src/exporter.mjs`
- Modify `tools/stitch/test/exporter.test.mjs`
- Append implementation evidence to `.superpowers/sdd/stitch-html-fallback-url-encoding-fix-report.md`

## Required behavior

- Continue using the original `localId` escaped for visible text and HTML attributes.
- For the fallback `<img src>`, encode `localId` as one URL path segment with `encodeURIComponent(localId)`, then HTML-escape the encoded value before interpolation.
- A fallback export for `localId = "login#detail?mode=dark"` must reference `../screenshots/login%23detail%3Fmode%3Ddark.png`.
- Preserve the current `screenshot-fallback` provenance marker, manifest hashes, structured logs, staging/promotion behavior, and normal Stitch HTML path.
- Do not modify the verifier, generation state, real design assets, or any unrelated code.
- Do not access the network or any API key.

## TDD and verification

1. Change the existing fallback exporter test input to include both `#` and `?`, and update its expected image URL.
2. Run `node --test test/exporter.test.mjs` before production code changes and capture the expected RED mismatch proving the URL is unencoded.
3. Apply the minimal production fix.
4. Run `node --test test/exporter.test.mjs`, then `npm test`.
5. Run `node --check src/exporter.mjs`, `node --check test/exporter.test.mjs`, and `git diff --check`.
6. Run GitNexus change detection or the available CLI equivalent before committing.
7. Commit only the two source/test files and this brief/report evidence with message `fix: 编码Stitch降级截图路径`.

## Impact evidence

GitNexus upstream impact at base `19b3812`:

- `screenshotFallbackHtml`: LOW, one direct caller (`exportDesignProject`), zero processes.
- `exportArtifact`: LOW, one direct caller (`exportDesignProject`), zero processes.
- `exportDesignProject`: LOW, directly covered only by `exporter.test.mjs`, zero processes.
