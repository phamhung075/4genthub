## TSC-23 fence (1/5): `mission.md` names the command instead of a count

Fence holder: writer (lead's routing, `DISPOSITION-tsc-23-count-cluster-2026-10-10.md` §7).
Spec: §3 site 1 of the same document.

### Changed
- `scripts/team/4genthub/mission.md:7` — `- Frontend: no new TypeScript errors (23 old ones removed 2026-10-03; count now zero), vitest passes, vite build passes.` becomes `- Frontend: \`npx tsc --noEmit -p .\` prints no \`error TS\` line, vitest passes, vite build passes.`

**This is the one site whose replacement ADDS a command rather than only deleting a count**: measured before the edit it was the only one of the four with `command=0`, and now it carries the command. The count and its funeral notice both go: what a seat needs is the command and the absence of the string, not the history of a number it was once punished by. The 2026-10-03 removal stays where it is history — `agenthub-frontend/CHANGELOG.md`, which guides do not edit.

### Verified
- §4's per-file loop: `stale=0 command=1` (before: `stale=1 command=0`).
- Word band preserved: **514** words against `mission-4genthub` 350-560 in `scripts/tests/test_team_definition.py`'s `ROOM_WORD_LIMITS` (before 516).
