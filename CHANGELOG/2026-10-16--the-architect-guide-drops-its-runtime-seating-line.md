# The architect guide drops its runtime seating line

### Fixed

- `blocks/guide-architect.md` no longer carries "You are the only seat here on claude-code; the rest run omp.
  Write notes that read the same to either runtime." Both halves were false - `scripts/team/4genthub-min/team.json`
  runs all five seats as `runtime: omp`, `model: deepseek/deepseek-flash`, and `4genteam whoami --json` for this
  seat answers `architect omp deepseek/deepseek-flash` - and the seed library is ROLE-scoped, not room-scoped, so
  a seating fact about one room does not belong in a block every room's architect renders. The line went whole:
  its second sentence was the other half of the same claim. It was the only `claude-code` claim in the shelf's
  blocks (`grep -rn 'claude-code' .../seedlibrary/blocks/*.md` = 1, at `:11`).
- Found by the architect while re-reading its own guide on 2026-10-16 (row `qitem-20261016041654`), decided by
  the lead (row `qitem-20261016041920-c619061eb03c`, option 1 - delete the line rather than make it rig-specific),
  implemented by go-dev.

### Changed

- `seedVersion` moves `1.4.8` -> `1.4.9` (`domain/seedmap/seedmap.go`), because the library is content-locked and
  a stored seat type version is immutable: the content and the version move together, or a load is refused.
  `seedcontent.lock.json` appends the 1.4.9 content set (`content_sha256 2d2b2feee5ec9ab7…`,
  `blocks/guide-architect.md` at `e52f9b4571d18ce4…`), and `guides.lock.json` re-records the `guide-architect`
  pairing (`2a9b494078b35361…` -> `e52f9b4571d18ce4…`). The lock is append-only, so 1.4.3-1.4.8 keep the sets they
  named.
- Reach, stated because it is not automatic: a seat type built at 1.4.9 or later renders the guide without the
  line. Content already stored under an earlier version keeps the text it was built with - this room's spec pins
  `pinned_version: 1.4.3` - so bringing the fix to an existing room means moving that pin (or reseating the seat).
  Nothing is deployed by this change; the library reaches a room through the server and the owner's push.

### Testing

- `go test ./fastmcp/seat_management/...` and `go test ./fastmcp/... ./cmd/...` are green, and the repair was
  taken through the guard's own path rather than by hand: `go test ./fastmcp/seat_management/domain/seedlibrary/
  -run TestSeedVersionNamesOneContentSet` fails first (`seedVersion 1.4.9 names no content set`), then
  `-args -update-seedcontent-lock` appends the record, then the package is green.
- `go run ./cmd/blockdrift -root ..` exits 0: 17 blocks in step, 11 sources already gone (the post-migration
  steady state the tool counts rather than fails), no divergence between the shelf, the lock and the tree.
  No test file changed, so this repo's `TEST-CHANGELOG.md` is untouched.
