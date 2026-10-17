## 2026-10-17 - the docs-only guard judges the staged commit, not a pre-commit batch

### Fixed
- `scripts/git-hooks/docs-only-guard` read its file list from the arguments, which pre-commit passes in batches. A commit mixing docs with code could reach the guard as a docs-only batch and be refused. It now reads `git diff --cached --name-only --diff-filter=ACMR` and judges the whole commit; with nothing staged it exits 0.

### Testing
- Proven by the lead seat in a scratch repo: mixed docs+code staged exits 0, docs-only staged exits 1, nothing staged exits 0.
