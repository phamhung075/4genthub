### Added

**Project skills are now generic — `.agents/skills` is the single source** (2026-10-04)

- All 12 project skills moved from `.claude/skills/` to `.agents/skills/` (the house convention: `deepseek-offload/.agents/skills/<name>/SKILL.md`, optional `scripts/`/`references/`), so every agent — Claude Code, the omp/DeepSeek seats, codex, agy — reads the same files. `.claude/skills` is now a symlink to `../.agents/skills`: Claude Code keeps loading all skills unchanged (verified end-to-end: `rig-runtime-switch` loads through the symlink, and both paths resolve to the same file). A skill added under either path lands in the same store; no duplicate copies. Note: `.agents/` is gitignored (local store); the symlink lives in the `.claude` submodule.

**Rig runtime-switch playbook as a reusable skill** (2026-10-04)

- `.agents/skills/rig-runtime-switch/SKILL.md`: the verified playbook for keeping an OpenRig team working through a usage cap by swapping its runtime variant — authoring `rig-omp.yaml` (`runtime: omp`, `model: deepseek/deepseek-flash`, `builtin:yolo`), `.env` placement for the omp launch dir, `rig up --plan` dry-run, the owner-named teardown, down/up + verification, the kickoff requirements (state-at-cutoff, rules, the omp runtime note), companion-rig revival (`rig up 4genthub-deepseek --existing --yes`), the herdr watch wall (`rig terminal open <rig>`), and the switch-back path. Derived from the 2026-10-04 `4genthub-min` claude-code → omp/DeepSeek switch executed while the Claude weekly cap was active.
