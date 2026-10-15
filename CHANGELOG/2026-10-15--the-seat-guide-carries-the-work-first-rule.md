## The seat guide carries the owner's work-first rule

### Changed
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: a new section, **Work first, docs when the task is done** — the work is build, improve, fix; an idea, a finding, a ruling and a status travel through the queue rather than into a doc; `CHANGELOG/` and `TEST-CHANGELOG.md` are written once, when a task is done, in the same commit as the code, and only when the change needs them; a sweep or a reconcile task on docs needs the owner's ask; a doc line that is wrong is corrected when the code it describes is next changed. Owner rule of 2026-10-15, given to the lead in row `qitem-20261015210051`.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/guides.lock.json`: guide-common's `sha256` and `source_sha256` re-recorded to the edited text's digest. **The two move together:** the pairing check materialises the block's own bytes as the source, so a record that moves one of them reports `guide-common … source-differs`.
- `agenthub_go/fastmcp/seat_management/domain/seedmap/seedmap.go`: `seedVersion` to 1.4.6, with the rule named in the comment above it. A stored seat type version is immutable, so text that moved needs a new version before any seat can resolve it.
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/seedcontent.lock.json`: the content set 1.4.6 names, appended with `-update-seedcontent-lock`, because the guard refuses a version that names none.

### Verified
- `cd agenthub_go && go test -count=1 ./fastmcp/seat_management/domain/seedlibrary/...` -> ok, exit 0.
- `cd agenthub_go && go run ./cmd/blockdrift -root ..` -> exit 0: `17 block(s) in step`, `11 source file(s) already gone (expected after the migration)`, no divergence line.
- `cd agenthub_go && go build ./...` -> exit 0.

### In force in no running seat yet, stated rather than implied
- A running seat never re-reads its guidance, and a resolved seat moves only when the new module version is published and the refs name it: a module version is immutable and the resolver refuses a floating ref. Until that publish lands with the principal's token, every seat keeps rendering the previous text. The four live seats of `4genthub-min` were given the rule through the queue, which is what takes effect now, and they were told this commit is the durable half.
