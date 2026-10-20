# The frontend line returns to main

`main` merges `fe-parity` (`f1a08bb7`). Both lines now carry the same shipped tree, and
`origin/frontend` was pushed to that sha first — a shipped branch is merged back, never re-ported.

## What the merge carries

- `ModuleContentView` sections with the raw toggle, and the seat History tab that reads the occupant
  trail off `GET /api/v2/rooms/{room}/seats/{seat}/occupant-history`.
- `taskTimeline`'s `contextChangeDetails`, so a context entry renders what changed.
- The login 403 reaches the user as the hub worded it (`AuthContext` pass-through).
- HUB1: `ai_docs/agent-system/repo-agent-rules.md:169` now says a push to `main` deploys nothing and
  the app ships from the `frontend` branch.
- The stale `agenthub-frontend/captain-definition` goes: it named `./Dockerfile.production`, which does
  not exist at HEAD — the second definition the operations guide says is dead.

## Proof

- Merge onto current `main` (`fc473f71`, two commits past the branch point) is clean: no conflict,
  18 files, +567/−76. It is a real merge, not the fast-forward the branch point would have allowed.
- `git diff f1a08bb7 -- agenthub-frontend` is empty: the merged frontend tree is the pushed sha's tree.
- `npx tsc --noEmit -p .` exit 0 and `npx vitest run` 131 files / 1933 tests passed, run independently
  of the reviewer's identical numbers.
- Deploy is proven by served content, not by a hash: the live bundle serves `Bypass cache and force
  fresh` and `inheritance | caching` before this push; after it the bundle must serve
  `inheritance | delegation | insights` and not the removed line.

Task: 50f64aba-5f94-424b-b31c-080564828f37
