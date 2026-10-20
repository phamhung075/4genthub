## The two frontend test headers cite files that exist

Two citation defects found while sweeping `agenthub-frontend/src` for repository paths that do not
resolve, on branch `4genthub-min/fe-rig-gone`. Both are comments, both predate this branch, and
neither is part of the `rig` slice: a comment is a claim, and a claim about a path is checkable.

### Changed

- `agenthub-frontend/src/tests/components/SeatComposerPurposes.test.tsx:8`: the header elided the
  path as `agenthub_go/.../resolver/resolver.go`, which no `git cat-file` can resolve. It now spells
  the path the case itself reads (`:60`, `agenthub_go/fastmcp/seat_management/domain/resolver/resolver.go`).
- `agenthub-frontend/src/tests/hooks/test_useRealtimeSync_branch_delete.test.tsx:4`: the header named
  `ai_docs/core-architecture/websocket-protocol-migration-guide.md` as the source of truth. That file
  exists in no commit of the hub tree (`git cat-file -e`, and `git log --diff-filter=D` finds no
  removal), so the citation was never true. It now names `src/types/websocket-protocol.ts` -
  `BranchDeletePayload` and `isBranchDeletePayload`, both of which the file imports and exercises -
  and records the stale citation so the next reader does not restore it.

### Checks

`npx tsc --noEmit -p .` exit 0. `npx vitest run` on the two files: 2 files, 10 tests passed.

The sweep that found them (`ai_docs/`, `CHANGELOG/`, `agenthub_go/`, `agenthub_client/` paths cited
from `agenthub-frontend/src` and `e2e`) left one deliberate miss: `ai_docs/core-architecture/agent-boundaries.md`,
which slice D-frontend cites and slice B renames. Verified present at B's tip `ad08932a` and absent
on `origin/main` at `606a770f`, which is exactly the hold.
