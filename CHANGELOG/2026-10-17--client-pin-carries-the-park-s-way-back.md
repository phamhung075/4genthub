## Changed

- `agenthub_client` pin moves `c3f5a7e` -> `ca8f5f5`, a merge of `4genthub-min/park-way-back` (2 commits, 5
  files).

### Added

- The park names its way back. `roombudget.Parked` carries the concrete exit - the removal command and the
  reseat that must follow it, in that order - so a reader holding only the record file learns it, and the park
  row itself asks the reader to close the row with why the seat came back
  (`internal/roombudget/roombudget.go`). `clientlifecycle`'s park path writes that record and the row: the
  record must be REMOVED FIRST, because a reseat before the removal leaves the seat stopped
  (`internal/clientlifecycle/budgetguard.go`).

### Measured, so the way back is checkable

- The record is written through `WriteParked`, read back off disk and asserted to carry the exit command and the
  ORDER (`remove this file FIRST`; `a reseat before the removal leaves the seat stopped`), not merely the field.
- Red first by `go test -overlay` over the pre-change `budgetguard.go`: the new assertions fail on the row's old
  sentence and on the exit value; restored, the package is green. The rail's own cap is pinned at this room's
  names and root: 91/120 summary, 561/600 body.
- Both commits carry `Task: 1a560121-b11d-43c3-bc20-e369b463d091`, and the reviewer measured the park half
  byte-identical to the HOLDed range (`d5c9b5d` -> `54a56e4`), so nothing needed re-measuring.

Validated: gated by the reviewer at `e9fdada` (32 packages ok / 0 FAIL), and measured again here on the MERGED
tip `ca8f5f5` because the two gated lanes are combined: `go test -count=1 ./...` = 32 packages ok / 0 FAIL,
`go vet ./...` rc 0, `gofmt -l` silent over tracked files. This pin's hub entry and the parked `TEST-CHANGELOG.md`
section stay in the working tree, owed to the next non-doc carrier commit - `docs-only-guard` cannot see a
gitlink (`qitem-20261017002819`).
