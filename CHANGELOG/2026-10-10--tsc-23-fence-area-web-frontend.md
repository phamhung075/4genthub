## TSC-23 fence (2/5): `area-web-frontend.txt` names the command instead of a count

Fence holder: writer. Spec: §3 site 2 of `DISPOSITION-tsc-23-count-cluster-2026-10-10.md`.

### Changed
- `scripts/team/4genthub/area-web-frontend.txt:11` — `- npx tsc --noEmit -p . (0 errors since 2026-10-03, when the 23-error baseline was removed; your change must not add any)` becomes `- npx tsc --noEmit -p . (prints no \`error TS\` line; your change must not add any)`.

The command was already here, so this is a deletion: the parenthetical's count and its date go, the condition it was groping at stays.

### Verified
- §4's per-file loop: `stale=0 command=1` (before: `stale=1 command=1`).
- Word band preserved: **141** words against `area-web-frontend` 100-200 (before 146).
