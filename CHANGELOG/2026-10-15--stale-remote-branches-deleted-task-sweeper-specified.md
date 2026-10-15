## 2026-10-15

### Changed
- Remote branches: deleted every branch contained in `main` or `frontend` (47 in the main repo; `4genthub-min/u2-native-runner`, `feat/support-agy-watch`, `fix/compact-reply-not-a-turn` in the client). Used `git push --no-verify --delete` on the owner's instruction, because `pre-push-branches` refuses deletions.
- Kept, not contained in `main`: client `feat/room-requires-links` (`f5514c1`, one commit) and three 2025 Python-era branches `claude/fix-datetime-utc-attribute-*`, `claude/fix-env-loading-tests-*`, `claude/mock-database-tests-*`. The team merges the client one into `main`; the three Python-era ones target code that no longer exists and are listed for the owner.

### Added
- `ai_docs/development-guides/task-lifecycle-sweeper.md`: the specification for a server sweep that prunes completed tasks after a week, escalates unfinished ones, and blocks the ones that stay idle at critical priority. Specification only; no code yet.
