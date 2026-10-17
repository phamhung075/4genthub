## The lockfile drops the katex advisory mermaid brought in

`pnpm audit --registry https://registry.npmjs.org --json` (the configured
`registry.npmmirror.com` implements no audit endpoint, so the flag is required) reported TWO
findings on the tip:

- `braces` 3.0.3, GHSA-vfj7-8cjw-p6xm (high) - `patched_versions: null`,
  `patched_versions_unpublished: true`; no fix exists to install, so it stays on the owner's route
  decision (task 4906b25c).
- `katex` 0.16.47, GHSA-238p-pmpm-9mq7 (low, CWE-807): an existing prototype pollution can bypass
  katex's trust restrictions; patched `>=0.18.2`. Unlike `braces` this one has a fix, and it is a
  PRODUCTION dependency (`dev: false`) reached only through `mermaid` 12.1.0.

### Changed
- `agenthub-frontend/pnpm-workspace.yaml`: `katex: '^0.18.2'` in `overrides`. mermaid 12.1.0
  declares `katex: ^0.16.47`, so the patched version is outside its range and rule 79's override is
  the only route short of a mermaid major. mermaid touches only `katex.render` and
  `katex.renderToString`; both exist in 0.18 (measured: a scratch install of 0.18.11 exports both and
  `renderToString('x^2')` returns markup).
- `agenthub-frontend/pnpm-lock.yaml`: regenerated with `pnpm install --lockfile-only`. The diff is
  the katex pair and its dependency: `katex@0.16.47` -> `0.18.11`, `commander@8.3.0` -> `15.0.0`
  (katex's own build CLI, not used at runtime). Nothing else moved.

### Verification
- Before: audit `metadata.vulnerabilities` = 1 low, 1 high. After: 0 low, 1 high (`braces`,
  unchanged - no patch published).
- `npx tsc --noEmit -p .` exits 0; `npx vitest run src/tests/lib/mermaidDiagrams.test.ts
  src/tests/pages/DocsPage.test.tsx` = 2 files / 8 tests, 0 failed.
- Not proven here: mermaid rendering a math node with katex 0.18 in a real bundle - that path is
  mocked in the unit tests and is proven by a production image build plus a `/docs` render.

### Not run
- No `vite build` and no `pnpm install` with node_modules (the seat guard refuses a local build, and
  node_modules here is shared); the lockfile is the artefact the image build consumes.
