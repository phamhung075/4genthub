## The dev-toolchain's own HIGH/CRITICAL alerts are cleared too, and pnpm's settings moved house

- **Owner ruling 2026-10-07.** Cleared **eleven** of the twelve modules `pnpm audit` reports at HIGH/CRITICAL for the
  frontend lock. Every patched version was a **patch or minor** of what was installed (`vitest` 3.2.4->3.2.7,
  `vite` 7.1.7->>=7.3.5, `postcss` 8.5.6->>=8.5.18, `rollup` >=4.59.0, `ws` >=8.21.0, `browserslist` >=4.28.7,
  `flatted` >=3.4.0, `nanoid` >=3.3.18, `minimatch` >=9.0.7, `tinypool` >=2.1.2) except **`glob` >=12**, which is a
  **major** - the one real risk, settled by data rather than judgement: the `vite build` runs tailwind's chain through
  `sucrase`->`glob` and **built green in 22.15s**, so the major stands rather than being reverted.
- **THE ONE REMAINING HIGH IS `braces`**, through `tailwindcss@3.4.17 -> micromatch@4.0.8` (already latest), which needs
  a **tailwind MAJOR** - the open owner decision, unchanged and deliberately not taken. The root lock audits clean at
  HIGH and CRITICAL both before and after this change.
- **MEASURED, BECAUSE IT INVALIDATES AN EARLIER LINE OF MY OWN REPORT:** pnpm **12.10.1** now warns *"The 'pnpm' field in
  package.json is no longer read by pnpm... 'pnpm.onlyBuiltDependencies', 'pnpm.overrides'"* and **ignores** it - so the
  overrides that `90a739f8` wrote into `package.json` became inert the moment the toolchain moved, which a static read
  of the diff could not have shown. Both settings now live in `agenthub-frontend/pnpm-workspace.yaml` (the documented new
  home), the `package.json` block is **removed rather than left as a second voice**, and `onlyBuiltDependencies` is also
  passed per-install because the yaml key alone did not satisfy pnpm 12's build-script check.
- **The lockfile is the artefact, not the manifest:** the Trivy step is `scan-type: fs` and no workflow runs pnpm, so
  every fix here is verified in `pnpm-lock.yaml`.
- Gates: `npx tsc --noEmit -p .` 0 errors; `npx vite build` green in 22.15s; the suite in the commit notes.
