## The seat guide carries the owner's short-pointers rule

### Changed
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: a new section, **Think and reply in short pointers**, placed beside the work-first section — think in short pointers naming the next step, the fact relied on and the risk, not full reasoning or alternatives that will not be taken; a reply and a queue row give the result first, then at most five short lines of paths and ids; no large tool output or whole file pasted into a thought or a row. Owner rule of 2026-10-15, given to the lead in row `qitem-20261015214302-4404c2f5eca5`.
- `agenthub_go/fastmcp/seat_management/domain/seedmap/seedmap.go`: `seedVersion` to 1.4.7, with the rule named in the comment above it. A stored seat type version is immutable, so text that moved needs a new version before any seat can resolve it.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/guides.lock.json`: guide-common's `sha256` and `source_sha256` re-recorded to the edited text's digest; **the two move together**, because the pairing check materialises the block's own bytes as the source and a record that moves one reports `guide-common … source-differs`.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/seedcontent.lock.json`: the content set 1.4.7 names, appended with `-update-seedcontent-lock`, because the guard refuses a version that names none.

### Verified
- `cd agenthub_go && go test -count=1 ./fastmcp/seat_management/...` -> ok, exit 0.
- `cd agenthub_go && go run ./cmd/blockdrift -root ..` -> exit 0: `17 block(s) in step`, `11 source file(s) already gone (expected after the migration)`, no divergence line.
- `cd agenthub_go && go build ./...` -> exit 0.

### In force in no running seat yet, stated rather than implied
- A running seat never re-reads its guidance, and a resolved seat moves only when the new module version is published and the refs name it: a module version is immutable and the resolver refuses a floating ref. Until that publish lands, every seat keeps rendering the previous text. The live seats of `4genthub-min` already carry this rule through the queue, which is what takes effect now; this commit is the durable half.
