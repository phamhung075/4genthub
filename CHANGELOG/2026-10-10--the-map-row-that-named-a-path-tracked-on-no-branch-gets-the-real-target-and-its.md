## The map row that named a path tracked on no branch gets the real target and its deletion witness

### Changed
- `agenthub_go/MIGRATION.md`, the row for `agent_management/infrastructure/database/models.py`: its Go target was `fastmcp/agent_management/infrastructure/database/models.go`, **a path tracked on NO branch**, while the row's own note said "see models_agent_management.go". The real port is `fastmcp/agent_management/infrastructure/database/models_agent_management.go` — **`6b0bdd5f` added it and `e0338f54` deleted it with the old agent system (T7 Go half)**. The row now reads `removed (the PORT was models_agent_management.go — added by 6b0bdd5f, deleted by e0338f54; the path this row names was tracked on NO branch)`.

### Verified
- **Which of the three it is, with the command for each read — the TARGET is the defect AND the deletion witness exists for the real file.** (i) *ported under another name:* YES, and that file is deleted — `git log --all --diff-filter=A -1 -- '*models_agent_management.go'` returns `6b0bdd5f`, and `--diff-filter=D` returns `e0338f54`. (ii) *never ported:* FALSE — the file existed from `6b0bdd5f` to `e0338f54`. (iii) *the row's path is the typo:* TRUE of the path COLUMN — `git log --all --oneline -- agenthub_go/fastmcp/agent_management/infrastructure/database/models.go` returns **0 commits**, and the sibling rows in the same section use the suffixed-name convention for exactly this case (`auth/infrastructure/database/models.py` → `done (tested; see models_auth.go)`, where `models_auth.go` EXISTS).
- **Nothing implements those models today:** `git grep -l "AgentTemplateORM\|UserAgentInstanceORM" -- 'agenthub_go/**/*.go'` returns nothing, and the only hits for `agent_templates` under `agenthub_go` are in documents.
- **Scope:** `git diff --numstat -- agenthub_go/MIGRATION.md` reads **1/1** — one row — plus this entry.

### Found by
- The residual of row `7117bab2`, ruled by the lead: measure which of the three it is and say which, with the command; **do not mark `removed` without a deletion commit.**
