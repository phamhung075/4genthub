## The seat guide carries the owner's docs rule, and the lock records the new text

### Changed
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: a new section, **Writing documentation**, carries the owner's rule — a doc names no commit hash, no count, no line number and no measured-on-date note; it points to the code or to the command that gives the answer; one page per topic, updated in place, with no per-change entries; `CHANGELOG.md` only for what a user or operator would notice; a claim that needs a number states the command that prints it; and a commit whose only purpose is to re-measure a number in a doc is stopped, because the number is deleted instead. The added text carries no digits at all, which is what the reviewer's regex over a commit's added lines comes back empty on.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/guides.lock.json`: guide-common's `sha256` and `source_sha256` re-recorded to the edited block's digest. **The two move TOGETHER, and the lock's own test is what says so:** `TestBlockDriftNamesEveryWayAFileCanMove` materialises a faithful copy of the tree, writes each interim source from its block, and fails with `guide-common … source-differs` when only `sha256` moves. The record's invariant is that a source which exists is byte-identical to its block, so freezing `source_sha256` is not the conservative choice — it is a red suite.

### Verified
- `cd agenthub_go && go test -count=1 ./fastmcp/seat_management/domain/seedlibrary/...` -> ok, exit 0.
- `cd agenthub_go && go run ./cmd/blockdrift -root ..` -> exit 0: `17 block(s) in step`, `11 source file(s) already gone (expected after the migration)`, and no divergence line.

### Not in force in any seat yet, stated rather than implied
- This commit is the REPO half. A seat reads this text through its seat type's render, and a resolved seat moves only when a new module version is published AND the refs name it: a module version is immutable and the resolver refuses a floating ref. Until that publish lands with the principal's token, every seat keeps reading the previous text, and the change will look exactly like a rule nobody obeyed.
