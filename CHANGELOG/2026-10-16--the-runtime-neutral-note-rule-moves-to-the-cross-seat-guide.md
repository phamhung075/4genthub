# The runtime-neutral note rule moves to the cross-seat guide

### Fixed

- The rule added at `751a1482` is at `shared-modules/guide-common.md`, under `### Writing style`, as its own
  paragraph - "Write each note so it reads the same to a seat on any runtime: the runtime-neutral wording by
  default, and a runtime-specific command or path named only when the fact itself is about that runtime." - and
  `blocks/guide-writer.md` returns to its pre-1.4.10 content. `751a1482` had put the rule in a ROLE block, and
  its own words ("a seat on any runtime") cover every seat that writes a note.
- The home is read off the shelf's own record rather than chosen: in `seedcontent.lock.json`, 1.4.5 -> 1.4.6,
  1.4.6 -> 1.4.7 and 1.4.7 -> 1.4.8 each changed exactly `shared-modules/guide-common.md`, which is
  "## Working procedure (every seat)" and already carries the writing sections; 1.4.8 -> 1.4.9 changed exactly
  `blocks/guide-architect.md` (role-scoped, correct); 1.4.9 -> 1.4.10 changed exactly `blocks/guide-writer.md`,
  a seat-scoped container for an all-seats rule. The revert is exact, not approximated: `guide-writer.md` hashes
  `591698b1d8d6d891…`, the value the 1.4.9 set records for it, so the rule exists in exactly one place.
- Decided by the lead on rows `qitem-20261016042636-b4d44bd1c8cf` (the decision) and
  `qitem-20261016042636-6c1d40379376` (the placement report it answers), and landed before the deploy so the
  misplaced version never ships and no later correction is owed.

### Changed

- `seedVersion` moves `1.4.10` -> `1.4.11`; the set differs from 1.4.10 in exactly
  `blocks/guide-writer.md` and `shared-modules/guide-common.md` (26 files either side). `guides.lock.json`
  re-records both pairings - `guide-common` `9bf5345698121596…` -> `30d0af1f7d81a8a6…`, `guide-writer`
  `b443f9fd8935ef97…` -> `591698b1d8d6d891…` - which `verifyGuideLocks` requires at load.
- Reach is the chain the review of `751a1482` settled: the hub push, the server rebuilt and restarted (the shelf
  is embedded; the seed library has no home in the client tree), and the seat type version a seat resolves being
  1.4.11 before a reseat renders it. This room pins `pinned_version: 1.4.3` on all five seats, so its own guide
  text does not move until that pin does.

### Testing

- Through the guard's own path, as before: `go test ./fastmcp/seat_management/domain/seedlibrary/ -count=1` fails
  first (`seedVersion 1.4.11 names no content set`), `-args -update-seedcontent-lock` appends the record, then
  the package is green. `go test ./fastmcp/... ./cmd/...` is green and `go run ./cmd/blockdrift -root ..` exits 0
  (17 blocks in step, 11 sources gone, no divergence). No test file changed, so `TEST-CHANGELOG.md` is untouched.
