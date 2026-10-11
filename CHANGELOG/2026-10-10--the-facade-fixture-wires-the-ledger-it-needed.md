## The facade fixture wires the ledger it needed — the batch's red `go test ./...` is the fixture, not production

`go test ./...` went red at the batch tip (`81c6bd8f`) in `application/facades`. Both failures are the
refusal added by `f059e78c` doing its job on a fixture that had not been migrated, and the fix is one
construction in that fixture. The refusal is untouched: no weakening, no bypass, and no change to the
pass-through call sites.

### Fixed
- `agenthub_go/fastmcp/task_management/application/facades/task_update_broadcast_test.go`:
  `newUpdateFacadeUnderTest` built `use_cases.NewUpdateTaskUseCase(repo, nil)` — the same **unwired**
  construction `f059e78c` migrated in `update_task_test.go` and `complete_task_test.go`. It now builds
  `.WithLedger(noopStatusLedger())`, with the seam declared in this file because the use-case package's
  own `noopLedger()` is test-only and not importable across packages: `StatusOf` reports the same status
  before and after the save, `RecordStatusChange` records into nothing, and `Transaction` is a
  pass-through. `StatusLedger.Enabled()` requires both halves, so both are supplied.
- Failure before the fix, exactly, as `go test` printed it: *"UpdateTask failed: … error:Unexpected error:
  status ledger is not wired: a status write must record its entry, and saving the status alone would be a
  silent success over a missing event"* at `task_update_broadcast_test.go:111` and `:139`. The two tests
  are about the broadcast's acting-user stamp and its post-update payload; neither is about the ledger,
  which is why they are wired rather than rewritten.

### Verified
- `go vet ./fastmcp/task_management/application/facades/` → clean.
- `go test ./fastmcp/task_management/application/facades/ -count=1` → **ok, 0.043s** (both previously failing
  tests pass).
- Module-wide `go test ./... -count=1` result is recorded in the row `qitem-20261010184615-ec57412642f21722`
  and reported to the lead with its exact counts.
- Independent agreement on the diagnosis: `context-dev` bisected it (`./fastmcp/task_management/...` at
  `f059e78c` = 71 ok / 5 FAIL; the same package at the parent `dd7cd0c8` green in 0.006s), and the lead
  reproduced it at the tip. Production is unaffected — only the fixture was unwired.

### Note for whoever reads a formatter's output next
- `gofmt -l .` inside `agenthub_go` walks `.gomodcache` and `.gotmp`, which live in that directory, and
  prints the Go toolchain's own files. The honest command is
  `git ls-files '*.go' | xargs gofmt -l`, which reports only the two known non-Go decoys.
