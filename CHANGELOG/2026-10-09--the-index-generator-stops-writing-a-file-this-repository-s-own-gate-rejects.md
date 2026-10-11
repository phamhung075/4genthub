## The index generator stops writing a file this repository's own gate rejects

### Fixed
- `.claude/hooks/utils/docs_indexer.py` (`4genthub-hooks`, commit `4d3247e`): `update_index()` now writes the final newline that `pre-commit-hooks` v5.0.0 `end-of-file-fixer` requires of `ai_docs/index.json`. `json.dump` writes none, so every regeneration produced a file this repository's own gate refused on the next commit and then rewrote.
- **REPRODUCED FIRST, BOTH SIDES IN ONE HARNESS, ON THE ARTIFACT THAT LANDED.** In a sandbox holding a copy of this tree's `ai_docs/` (66 markdown files) and the two hook entries extracted verbatim from `agenthub_main/.pre-commit-config.yaml`, the revision before the fix (`git show d27ea24:hooks/utils/docs_indexer.py`) leaves last byte `0x7d`, `pre-commit` exits 1 with "files were modified by this hook" and MODIFIES the file; the fixed revision leaves `0x0a` and both hooks pass with the file UNMODIFIED.

### Not in this commit
- The gitlink. `4d3247e` is local in the submodule, which is now three commits ahead of `origin/main` (two pre-existing unpushed ones plus this), and this repository excludes `.claude` from every commit, so a bump would carry all three. It is left to whoever next intends to bump.
- `ai_docs/index.json` in the worktree still ends `0x7d`; `HEAD`'s copy is the hook-repaired one. Nothing here regenerates it, so the next regeneration is the first that writes its own newline.
