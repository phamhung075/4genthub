## The TypeSafe skill joins the shared seat skills

### Added

- `agenthub_client/skills/share/typesafe-ai/` (`SKILL.md`, `LICENSE`), copied unchanged from
  `git@github.com:typesafe-ai/skills.git` at `65a39f3` (v0.5.7), so every seat gets it through the share tier
  regardless of its LLM. Client commit `2dd3350` on `feat/support-agy-watch`.

### Changed

- `agenthub_client` pin bumped `f193f34` → `2dd3350`.

### Notes

- Tested: `go test ./internal/clientskills/...` passes (the link test walks the whole skill tree).
- Not delivered to running seats yet: `sync rig` builds the store, then `seat reseat` copies skills into a live
  agent directory. Reseating the five live seats waits for a quiet moment in the OpenRig-free cutover work.
