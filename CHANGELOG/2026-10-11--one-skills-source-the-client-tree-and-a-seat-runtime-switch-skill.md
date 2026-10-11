## Project skills have one source: `agenthub_client/skills`, and a seat-runtime-switch skill

### Added
- `agenthub_client/skills/client/seat-runtime-switch/SKILL.md` (client commit `7d11a7c`): switch one seat to another runtime or model when a provider is capped. Variant spec, owner-approved rig rebuild, DeepSeek key check in the launch directory, verify, kickoff, grid reopen.
- `AGENTS.md` section 2: a "Project skills" line pointing to `agenthub_client/skills/` and the ruling `ai_docs/core-architecture/seat-skills.md`.
- Client `README.md`: the five `skills/client/` skills, and how another project uses the tree.

### Changed
- The 13 skill folders in the git-ignored `.agents/skills` were renamed to `*.obsolete` (reversible, one at a time). Each has a client-tree counterpart. `~/.agents/skills` and `~/.claude/skills` now carry symlinks to the `share/` and `client/` skills, with no copies.

### Verified
- Counterpart mapping of all 13 folders printed before the rename; the rename check printed `retired` for each. No code changed, so no tests apply.
