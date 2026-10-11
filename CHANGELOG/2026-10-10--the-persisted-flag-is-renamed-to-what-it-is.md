## The `persisted` flag is renamed to what it is — a shape fact, not a write confirmation

`{'success': true, 'meta': {'persisted': true}}` sat over writes that never happened, on a healthy database as
much as a broken one, because the flag means *"the response was well formed"* and everyone read it as *"your
write landed"*. That is the whole cost of the `user_seq` night, and this removes the name that promised what it
could not know. Decided by the lead's ruling (remove the lie; rename to what it is), on a reader census taken
first.

### Changed
- `fastmcp/task_management/interface/utils/response_formatter.go` — the writer at `:104` and the gate that reads
  it in `VerifyResponseSuccess` at `:244` now use **`data_present`**, which is exactly `data != nil`.
- `fastmcp/task_management/application/services/response_optimizer.go` — the flatten paths at `:190`/`:196` and
  at `:373`/`:374` publish **`meta.data_present`** instead of `meta.persisted`. The collapse itself is unchanged:
  a small confirmation with no partial failures is still moved into `meta`, so no consumer loses a field it had.
- `response_formatter_test.go` and `response_optimizer_test.go` updated with it, not preserved around it.

### The reader census that decided it
- **Nothing outside Go reads the flag**: `agenthub-frontend/src` zero hits (one unrelated comment about deletion),
  `agenthub_client` zero, `scripts/` zero. So no consumer can break on the rename, and the census is the reason
  this is a rename rather than a compatibility shim.
- **Inside Go it is shape throughout**: `response_formatter.go:104` writes it from
  `status != ResponseStatusFailure && data != nil`; `:244` gates on it; and `response_optimizer.go:190/196`
  **publishes** it under the name `persisted` — the delivery mechanism of the lie — with a second publication
  at `:374`.

### Verified
- **Acceptance, read rather than asserted**: `grep -rn '"persisted"' --include=*.go` returns **nothing**, and
  `grep -rn "data_persisted" --include=*.go` returns nothing, so a write that did not happen cannot produce
  `persisted: true` — nothing can produce `persisted` at all.
- `gofmt` clean on all four files; `go vet` clean on both packages;
  `go test ./fastmcp/task_management/interface/utils/ ./fastmcp/task_management/application/services/ -count=1`
  → both ok; module-wide `go test ./... -count=1` → exit 0, 0 FAIL.
- **Gated, not self-certified**: handed to `context-dev` with the instruction to try to **falsify** the
  zero-outside-Go claim rather than repeat it — a renamed published field is a behaviour change even when the
  census says nothing reads it.

### Ordering
- It lands **above** the 0.0.34 marker, and that is safe because the push ask is a **hash**
  (`git push origin 301ae824:main`): a commit above the marker never enters the pushed set. The next set's
  marker sits above this rename.
