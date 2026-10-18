## The comm guard denies `4genteam send --via-owner`, and the seed version names why

### Changed

- `fastmcp/seat_management/domain/seedlibrary/shared-modules/comm-guard.json`: the deny list gains
  `Bash(4genteam send --via-owner:*)`. The flag types one command into the room's owner node, so the
  signature a seat sees is that node's terminal - a seat must not reach the route, while plain
  `4genteam send` stays allowed as the audited path. Deny wins over the `Bash(4genteam send:*)` allow.
- `fastmcp/seat_management/domain/seedmap/seedmap.go`: `seedVersion` 1.4.17 -> 1.4.18 with its Why line,
  because a stored seat type version is immutable and the module content moved.
- `fastmcp/seat_management/domain/seedlibrary/seedcontent.lock.json`: re-stamped with
  `-update-seedcontent-lock` for 1.4.18.

### Tests

- `seedlibrary_test.go`: `wantDeny` carries the fourth row, so every embedded seat type is pinned to it.
- `seatrenderer/renderer_test.go`: the merge test's exact deny join, the claude fragment join, and the
  real-seed parity test (4 denies, 2 allows; 4 codex `forbidden` rules) follow. The codex test asserts the
  three-token rule renders as `pattern = ["4genteam", "send", "--via-owner"]` while the bare two-token
  `["4genteam", "send"]` rule stays absent - an exact join, because a substring match would have read the
  longer row as the verb's own deny.

### Why this is the mirror and not the guarantee

The hub render binds claude-code and codex seats only: an omp seat carries no claude fragment
(`renderer.go:58`), and the claude deny was measured not to bind this room's omp seats. The refusal that
binds every runtime is in the client verb (`agenthub_client`), which this change mirrors where a
permission list does bind.

At this change: `go test ./fastmcp/seat_management/...` passes.
