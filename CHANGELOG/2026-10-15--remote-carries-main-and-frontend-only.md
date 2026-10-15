# The remote carries `main` and `frontend` only

### Added
- `scripts/git-hooks/pre-push-branches` and a `pre-push` entry in `scripts/git-hooks/pre-commit-config.yaml`: a push to any remote ref other than `refs/heads/main` and `refs/heads/frontend` (a feature branch, a tag, a deletion) is refused with the reason. Seats keep branches and worktrees local and merge into `main`. The same script is installed as the client repo's `pre-push`. `git push --no-verify` is the owner's bypass.
- `AGENTS.md` states the rule beside the push-approval rule.

### Testing
- The script given a `feat/x` ref exits 1 and names it; `main` and `frontend` exit 0. Not exercised through a real `git push`.
- Existing stale remote branches (`claude/*`, `feat/support-agy-watch`, `4genthub-min/*` and others) are untouched: deleting them needs the owner's go-ahead.
