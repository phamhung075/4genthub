## The docs index is the tree

### Removed

- `ai_docs/index.json`: the catalogue was generated on 2026-10-10 by
  `.claude/hooks/utils/docs_indexer.py`, a path this repository does not check out, and no hook in
  `scripts/git-hooks/pre-commit-config.yaml` regenerates it. It named 20 files, omitted 25 of the 45
  tracked `ai_docs/*.md` (nine added after that date and all 17 under `public-docs/`), and carried a
  filesystem `modified` field that rewrites on every fresh clone. Nothing in `agenthub_go` or
  `agenthub-frontend` reads it; `/docs` builds its catalogue from the tree (`docsSite.ts`).

### Added

- `/ai_docs/index.json` in `.gitignore`, under the comment naming why: the external hook client
  (4genthub-hooks) still writes that name, so a checkout carrying `.claude` would recreate the file as
  an untracked change. `git check-ignore` exited 1 before this line and exits 0 after it, so a
  resurrection cannot enter a commit.

### Changed

- The command that answers "does this doc already exist" replaces the file in every instruction site:
  `git ls-files 'ai_docs/**/*.md'`. Repointed: `.gemini/gemini.md` (the AI Documentation System block),
  `.gemini/gemini.local.md` and `CLAUDE.local.md` (the MANDATORY check), `CLAUDE.local.md` (knowledge
  management), `agenthub_go/fastmcp/seat_management/domain/seedlibrary/blocks/guide-writer.md`,
  `ai_docs/agent-system/repo-agent-rules.md`, `ai_docs/agent-system/seat-model-and-mcp-surface.md` and
  `scripts/team/4genthub/area-docs.txt`. Each line keeps its sentence and swaps only the pointer; the
  `area-docs.txt` claim that hooks regenerate the index is corrected with it.
- Repointed in the rider commit: `agenthub_go/NEXT_GEN.md` (the standing docs duty),
  `ai_docs/core-architecture/agenthub-system-architecture.md` §3.9, `README.md` (the architecture
  diagram's documentation node) and the `# Update documentation index manually` command in both
  Quick Reference blocks, which now runs the `git ls-files` command.
- Stay, by the ruling's classification, because they describe the external hook client's own files or
  record history: the `.claude/hooks` listings in `CLAUDE.local.md` and `.gemini/gemini.local.md`
  (including the `4d3247e` note), `README.md`'s "post-tool documentation indexing", `NEXT_GEN.md` rule
  27, the two `ai_docs/operations/` narratives and the changelog history.

### Testing

- `git grep -n "index\\.json"` over the tracked tree leaves no instruction: the remaining hits are the
  stay set above and `performance_cache_manager.go`'s unrelated cache filename.
- `git check-ignore -v ai_docs/index.json` prints the ignore rule and exits 0 (it exited 1 before the
  guard was added).
- Both commits carry a non-doc path, so the docs-only guard accepts each mixed set:
  `scripts/team/4genthub/area-docs.txt` in the first, `.gitignore` in the rider.
  `PRE_COMMIT_NO_CONCURRENCY=1` was used as the ruling measured.
- No runtime boundary changed, so no build or test suite is affected; `/docs` still reads the tree.
