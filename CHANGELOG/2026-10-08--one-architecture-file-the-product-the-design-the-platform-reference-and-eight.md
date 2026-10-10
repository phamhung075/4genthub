## One architecture file: the product, the design, the platform reference and eight decision notes are rewritten into `agenthub-system-architecture.md`

### Changed
- `ai_docs/core-architecture/agenthub-system-architecture.md` is rewritten as the single source of truth: product (section 1), architecture and component state (2), platform reference (3), the eight decisions as dated sections D1 to D8 with status (4), the unbuilt knowledge/skill proposal (5), open owner decisions (6), where things live (7). It was de-duplicated, not pasted: counts are owned by `surface-inventory.md` and dated, the tool list is ten (the old technical reference said nine), the table count is 39, and the schema hierarchy is the post-D2 one (migrations before Go entities).
- Links to the absorbed files are repointed to the matching section in `agenthub_go/NEXT_GEN.md`, `ai_docs/api-integration/surface-inventory.md`, `ai_docs/operations/syncing-seats-with-the-cloud.md`, `README.md`, `.gemini/commands/*.toml` and a comment in `routes_mount_test.go` (no behaviour change).
- `ai_docs/agent-system/repo-agent-rules.md` still names `decision-commit-form-in-seat-instructions.md` inside another seat's uncommitted edit; it is left for that edit's owner to repoint to section D8.

### Tested
- `git ls-files | grep` for the absorbed file names outside `agenthub_main/`, the changelogs and the SSOT itself: only the uncommitted `repo-agent-rules.md` hunk and the files deleted next remain.
