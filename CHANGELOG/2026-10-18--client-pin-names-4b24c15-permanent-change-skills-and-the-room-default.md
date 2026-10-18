# The client pin names `4b24c15`: team-benchmark, permanent-change, the ROOM default and the lean workflow

`agenthub_client` moves `d0ffef4` -> `4b24c15` (14 commits, all pushed before this pin):

### Added
- `9c2296b` - skill `team-benchmark`: each seat's chat, board, git, writing and test share of tool calls over 24h, the commits by kind, and the change against the previous run.
- `5c05cea`, `122805b` - skill `permanent-change`: a team change is done only when committed in the versioned seat source and shown in the seat's installed copy.
- `c459221` - the `install` skill links the client and share skills into Claude Code.
- `807ae85` - the queue verbs default ROOM to `$AGENTHUB_ROOM` (go-dev ran `queue show` without it 147 times in 24h).
- `038f468` - a seat's lane is named by its key, and a room refuses a prefix pair.

### Changed
- `030c847`, `76470b0`, `de2600c`, `3d71ea9` - `seat-crew` and `queue-row-schema`: the chore claim rule, one row in / one verdict out, done = committed, one changelog file per merged task.

Testing: client `go test ./...` and `cargo test --offline` run before the client push; hub CI is the repoguards check at `fetch-depth: 0`.
