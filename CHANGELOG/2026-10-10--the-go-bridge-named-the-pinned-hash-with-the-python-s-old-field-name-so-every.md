## The Go bridge named the pinned hash with the Python's old field name, so every report was a 400 that reads as OFFLINE

### Changed
- `agenthub_go/internal/clientbridge/payload.go`: `SeatStatus` now sends `json:"pinned_hash"`. It carried `json:"hash"`, the name from before the rename that DEPLOYED in `f878ab4d`, while the server has required `pinned_hash` under `DisallowUnknownFields` since then (`fastmcp/server/httpapp/seat_status_mount.go:101` and `:137`). The Go port's report was therefore rejected **400**, and the bridge reads a rejected report as the machine going OFFLINE - on the day the Go port ships. **One name: no dual field, no fallback.**
- `agenthub_go/internal/clientbridge/testdata/python_dump.json`: its **36** `"hash"` keys become `"pinned_hash"`. That fixture is the capture of the Python `once --print` dump, and the Python report already sends `pinned_hash` (`agenthub_client/.../bridge.py:269`), so the fixture was stale in exactly the way that kept the parity case green. `PinnedHash`'s read of the client's own `pinned.json` keeps `json:"hash"` deliberately: that file is the local lock, and Python reads `"hash"` from it too (`bridge.py:211`).

### Verified
- **Fail-first, in the direction that was hidden.** With the fixture re-keyed and `payload.go` untouched, `TestPayloadParityWithThePythonBridge` **FAILS** on the one pinned seat - `go {… Hash:a1a1a1…}` against `python {… Hash:}` - because the fixture no longer decodes into the stale tag. With the tag renamed it is **ok** (`go test ./internal/clientbridge/... -count=1`). That pair is the point of the change: the parity fixture was pinning the wrong name and therefore could not fail.
- **Both directions against the real mount**, driven through `seat_status_mount_test.go`'s own mux and body with a throwaway case that is no longer in the tree: a report carrying `pinned_hash` -> **200**; the same report with the old name -> **400 `{"detail":"json: unknown field \"hash\""}`**, the production rejection verbatim.
- In this tree: `gofmt` nothing, `go vet ./...` rc 0, `go test ./...` **141 packages ok / 0 FAIL**.
- **Not run, deliberately:** the production POST. A bridge report changes production seat state, so the live 200 is proposed to the owner rather than executed by a seat.

### Found by
- Row `de2753c8`, from the read-only measurement in `BRIDGE-STATUS-PINNED-HASH-SCOPING-2026-10-10.md` (row `2230faf5`).
