## TSC-23 fence (4/5): `area-quality.txt` names the command instead of a count

Fence holder: writer. Spec: §3 site 4 of `DISPOSITION-tsc-23-count-cluster-2026-10-10.md`.

### Changed
- `scripts/team/4genthub/area-quality.txt:9` — `- npx tsc --noEmit reports **0** errors on the untouched tree (**23-error baseline removed 2026-10-03**), so **ANY \`error TS\` line is a regression, not a pre-existing failure.**` becomes `- npx tsc --noEmit prints no \`error TS\` line on the untouched tree, so **ANY \`error TS\` line is a regression, not a pre-existing failure.**`

The conclusion the line was written to reach is unchanged and is now reached by a condition rather than by a number. Its file's full command lives in the suite list at line 6, so the positive control counts there, not in this line — per §4's ruling, the back-reference is not expanded.

### Verified
- §4's per-file loop: `stale=0 command=1` (before: `stale=1 command=1`).
- Word band preserved: **193** words against `area-quality` 100-240 (before 195).
