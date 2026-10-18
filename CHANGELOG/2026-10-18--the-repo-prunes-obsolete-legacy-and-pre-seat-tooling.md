# The repository prunes obsolete markers, legacy Python helpers and pre-seat-model tooling

### Changed
- Removed the tracked `*.obsolete` markers: `NEXT-GEN2.md.obsolete`,
  `agenthub_go/internal/repoguards/docs_only_guard_test.go.obsolete`, `scripts/git-hooks/docs-only-guard.obsolete`.
- Removed the Python-backend helpers `scripts/add_future_annotations.py`, `fix_code_quality.py`,
  `modernize_type_hints.py`, `test-keycloak-auth.py`, `test_mcp_crud_suite.py` and `docker-system/docker-menu.py`.
- Removed `.gemini/` (27 command files and two notes), `.automation/` and `docker-system/.claude/`
  (stored sessions and a dead hooks link); `docker-system/Makefile` no longer chmods `docker-menu.py`.
- Deleted five untracked `CHANGELOG/*.obsolete` files, `scripts/mem-sampler.sh` and the stray nested clone
  `agenthub-frontend/agenthub_client/`.

### Kept
- `scripts/check_served_frontend.py` (the frontend deploy), the census audits `CITATION-AUDIT`, `COUNTS-AUDIT`,
  `S3-REDERIVE`, `G3-DROP-CLASSIFY`, `agenthub_go/TEAM_SPLIT.md` and `PROD_READINESS_REPORT.md` (live documents
  cite them) and the untracked `ai_docs/reports-status/` (64 seat reports, still written today).

### Tested
- `git grep` finds no live reference to a removed file outside `CHANGELOG/` and one historical doc line.
