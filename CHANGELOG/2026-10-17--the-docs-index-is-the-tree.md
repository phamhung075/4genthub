## The docs index is the tree

### Removed

- `ai_docs/index.json`: the catalogue was generated on 2026-10-10 by
  `.claude/hooks/utils/docs_indexer.py`, a path this repository does not check out, and no hook in
  `scripts/git-hooks/pre-commit-config.yaml` regenerates it. It named 20 files, omitted 25 of the 45
  tracked `ai_docs/*.md` (nine added after that date and all 17 under `public-docs/`), and carried a
  filesystem `modified` field that rewrites on every fresh clone. Nothing in `agenthub_go` or
  `agenthub-frontend` reads it; `/docs` builds its catalogue from the tree (`docsSite.ts`).

### Changed

- The command that answers "does this doc already exist" replaces the file in every instruction site:
  `git ls-files 'ai_docs/**/*.md'`. Repointed: `.gemini/gemini.md` (the AI Documentation System block),
  `.gemini/gemini.local.md` and `CLAUDE.local.md` (the MANDATORY check), `CLAUDE.local.md` (knowledge
  management), `agenthub_go/fastmcp/seat_management/domain/seedlibrary/blocks/guide-writer.md`,
  `ai_docs/agent-system/repo-agent-rules.md`, `ai_docs/agent-system/seat-model-and-mcp-surface.md` and
  `scripts/team/4genthub/area-docs.txt`. Each line keeps its sentence and swaps only the pointer; the
  `area-docs.txt` claim that hooks regenerate the index is corrected with it.
- Descriptive passages that narrate the retired generator (`ai_docs/operations/`, historical
  changelogs, `agenthub_go/NEXT_GEN.md`) are history and are left as written.

### Testing

- `git grep -n "ai_docs/index\\.json"` over the tracked tree leaves no instruction site: the only hits
  are the historical ones named above.
- The commit carries `scripts/team/4genthub/area-docs.txt`, a non-doc path, so the docs-only guard
  accepts the mixed set; `PRE_COMMIT_NO_CONCURRENCY=1` was used as the ruling measured.
- No runtime boundary changed, so no build or test suite is affected; `/docs` still reads the tree.
