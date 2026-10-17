## The agent guides name the layout commands, not a copied tree

### Changed

- `CLAUDE.local.md` and `.gemini/gemini.local.md`, the `ai_docs/` Structure block (one text, carried
  byte-identical in both files): the 17-entry tree is replaced by two commands - `git ls-tree --name-only
  HEAD:ai_docs` prints the folders and `git ls-files 'ai_docs/**/*.md'` the documents - and the
  kebab-case rule stays as prose. The heading drops the "17 Standard Folders" count, which was wrong:
  `git ls-tree --name-only HEAD:ai_docs` printed 11 directories at `e18c560d`, so eight listed folders
  were absent (`_obsolete_docs`, `claude-code`, `context-system`, `issues`, `keycloak`,
  `migration-guides`, `reports-status`, `testing-qa`) and three present ones were unlisted
  (`agent-system`, `public-docs`, `verification`). Nothing to regenerate, nothing to copy.
- The three index lines in "Fast Context Access" and "Automatic Management", and the "Index files" rules
  row, now state the retirement instead of the live file: the tracked tree is the index, and
  `ai_docs/index.json` is retired (2026-10-17). The hook-client lines that describe the external
  4genthub-hooks files (`post_tool_use.py`, `utils/docs_indexer.py`, including the `4d3247e` note) stay
  as written, by the ruling's classification - they are not claims about this tree.

### Added

- `agenthub_go/internal/repoguards/agent_docs_block_test.go`: three assertions, each the ruling's table
  rather than a new opinion - (a) the two guides' documentation blocks are byte-identical, (b) neither
  guide carries any of the five deleted index claims and both carry the retirement note, (c) each docs
  chapter names the two layout commands and draws no folder tree. It reuses `repoRoot(t)` from
  `task_trailer_guard_test.go`; no new harness.

### Testing

- Red before the rewrite, green after: `go test ./internal/repoguards/ -run
  'AgentGuide|DocsChapter|RetiredIndex' -count=1` reported all five forbidden claims in both guides
  against the pre-rewrite files, and passes on this commit.
- The two blocks were compared with `cmp` before and after the edit: byte-identical today, and the test
  now refuses the next divergence.
- This commit carries a non-doc path (`*_test.go`), so the docs-only guard accepts the mixed set.
