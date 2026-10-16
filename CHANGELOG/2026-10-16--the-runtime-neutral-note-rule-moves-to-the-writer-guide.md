# The runtime-neutral note rule moves from the architect guide to the writer guide

### Fixed

- The rule "write notes that read the same to either runtime" was the second sentence of a bullet inside
  `guide-architect.md`'s `### Tools you use, and for what` list, where every other bullet names a tool it is
  used for. It is a writing rule, not a tool, so it moves to `guide-writer.md` as its own workflow line,
  generalized: "Write each note so it reads the same to a seat on any runtime: the runtime-neutral wording by
  default, and a runtime-specific command or path named only when the fact itself is about that runtime."
- This is reason (3) of the lead's decision on the seed-drift report (row `qitem-20261016041920-c619061eb03c`),
  the half that outlived the deletion of line 11 at `c3f8aedf`. It was rehomed rather than dropped because the
  shelf had no other home for it: `grep -rn 'either runtime|any runtime|runtime-neutral|read the same'` over
  `blocks/`, `shared-modules/` and `seat-types/` was 0 hits before this change.

### Changed

- `seedVersion` moves `1.4.9` -> `1.4.10` (`domain/seedmap/seedmap.go`). The two edits were one decision but two
  content sets, and `seedcontent.lock.json` is append-only: it refuses to re-stamp a version with different
  content (`REFUSING to re-record seedVersion 1.4.9 ... Re-stamping is the drift, not the repair`), so the
  rehoming needs its own version rather than a second edit under the deletion's. The lock appends the 1.4.10 set
  (`blocks/guide-writer.md` at `b443f9fd8935ef97…`) and `guides.lock.json` re-records the `guide-writer` pairing
  (`591698b1d8d6d891…` -> `b443f9fd8935ef97…`); `verifyGuideLocks` refuses the shelf at load otherwise.
- Reach is the same boundary the deletion carries: a seat type built at 1.4.10 or later renders the rehomed rule,
  anything stored under an earlier version keeps the text it was built with, and nothing is deployed until the
  owner's push.

### Testing

- The repair was taken through the guard's own path: `go test ./fastmcp/seat_management/domain/seedlibrary/`
  fails first (`seedVersion 1.4.10 names no content set`), `-args -update-seedcontent-lock` appends the record,
  and the package is green. `go test ./fastmcp/... ./cmd/...` is green and `go run ./cmd/blockdrift -root ..`
  exits 0 (17 blocks, 11 sources gone, no divergence). No test file changed, so `TEST-CHANGELOG.md` is untouched.
