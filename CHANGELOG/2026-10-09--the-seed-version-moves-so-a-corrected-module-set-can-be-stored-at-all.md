## The seed version moves, so a corrected module set can be stored at all

### Changed
- `agenthub_go/fastmcp/seat_management/domain/seedmap/seedmap.go:14`: `seedVersion` **`1.3.0` -> `1.4.0`**. The const carries its own rule — a stored seat type version is immutable, so a changed module set needs a new version — and the module set changed in `8cebb0f7` (`blocks/guide-architect.md`, nine files, +288/-22).
- **Why this one line gates everything downstream, measured rather than argued:** until the version moves, no corrected module text can be stored in the cloud at all. `call_seat(room=4genthub-min, seat=lead)` still returned the SAME seat hash and the SAME snapshot as 21:26Z the previous day, with a `role.md` still carrying the pre-move script-test path and the retired "23 pre-existing errors" baseline. The repository half was correct; the stored version made the corrected text unstorable.

### Tested
- `go test ./fastmcp/seat_management/...` -> **ok** for all twelve packages; `gofmt -l` over the package prints nothing; `go build ./...` and `go vet` exit 0.
- **`seedmap_test.go` needs no edit, confirmed rather than assumed:** it compares against the CONST and never the literal — `seed.Version != seedVersion` (`:20`) and `role.Version != seedVersion` (`:25`) — so the expectation moves with the const by construction.

### Not in this commit
- The order after the bump, which is not the seat's to run: the principal builds, deploys, re-seeds and recreates the seats, then the seats re-resolve and install verbatim. Rows `3185add6` and `4e2459bd` carry that chain.
