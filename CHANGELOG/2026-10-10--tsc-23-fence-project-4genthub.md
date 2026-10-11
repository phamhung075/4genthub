## TSC-23 fence (3/5): `project-4genthub.txt` names the command instead of a count

Fence holder: writer. Spec: §3 site 3 of `DISPOSITION-tsc-23-count-cluster-2026-10-10.md`.

### Changed
- `scripts/team/4genthub/project-4genthub.txt:14` — `- Frontend: npx vitest run, npx tsc --noEmit -p . (0 errors — the 23-error baseline was removed 2026-10-03), npx vite build.` becomes `- Frontend: npx vitest run, npx tsc --noEmit -p . (prints no \`error TS\` line), npx vite build.`

### Verified
- §4's per-file loop: `stale=0 command=1` (before: `stale=1 command=1`).
- Word band preserved: **364** words against `project-4genthub` 350-500 — the tightest of the four, 14 words above its floor (before 368).
