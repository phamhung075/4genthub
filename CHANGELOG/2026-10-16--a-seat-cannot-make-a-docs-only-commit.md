# A seat cannot make a docs-only commit

### Added
- `scripts/git-hooks/docs-only-guard` and its `docs-only-guard` entry in `scripts/git-hooks/pre-commit-config.yaml` (stage `pre-commit`): a commit whose staged files are ALL documentation (`*.md`, `ai_docs/`, `CHANGELOG/`, `TEST-CHANGELOG.md`, `NEXT-GEN*`) is refused when `AGENTHUB_SESSION_NAME` is set, i.e. when a seat runs it. The owner's host does not set it, and `OWNER_DOCS_COMMIT=1` allows one commit the owner asked for.
- Why: 15 of 23 hub commits in one night were docs (plan status, sha corrections) after repeated GUIDE rows. Docs now change once, in the code commit of a finished task.

### Testing
- Script run directly: docs-only seat rc=1; docs plus a `.go` file rc=0; no seat env rc=0; `OWNER_DOCS_COMMIT=1` rc=0.
- `pre-commit run docs-only-guard --files README.md`: refused with the seat env, Passed without. No test file changed.
