## The seat status is decided by identity, never by the text

### Changed
- **`fastmcp/seat_management/application/services/seat_resolution_service.go` — the resolver's three misses now wrap the sentinels the seat-admin switch already reads:** `ErrRoomNotFound` (:46), `ErrSeatNotFound` (:53, previously `seat %q not found in room %q`), `ErrSeatTypeNotFound` (:60). The bodies become `room not found: room "x"` / `seat not found: seat "x"` / `seat type not found: seat "x"`.
- **`fastmcp/server/httpapp/seat_mount.go` — `writeSeatResolutionError` no longer asks the MESSAGE what the status is.** `strings.Contains(err.Error(), "not found")` is deleted, replaced by `errors.Is` over those three sentinels — the same switch `seat_admin_mount.go:1188` runs. An unrelated error that happens to SAY "not found" is now this server's own failure (500) rather than a 404 it never earned, which is the defect class this change closes.
- **THE FOURTH PRODUCER WAS CHECKED AND DOES NOT RIDE.** `seat_resolution_service.go:179` (the overlay branch) was proposed for the same wrap and the measurement says no: `ValidateOverlayResolution` is called ONLY from the admin mount (`seat_admin_mount.go:1223`, `:1256`, `:1293`), each of which answers 400 unconditionally, and the only callers of `writeSeatResolutionError` are the two `ResolveSeat` sites (`seat_mount.go:254`, `:356`). No input changes status either way, so wrapping it would be scope this row does not need. The two repository texts under `seat_management` (`seat_type_repository.go:98`, `module_repository.go:68`) sit on AddVersion write paths, not on `ResolveSeat`'s.
- Unchanged and named so no successor has to re-derive it: `seat_resolution_service.go`'s `seat type %q has no usable version` carries no "not found", so it answered 500 before and answers 500 now.

### Testing
- BEFORE, read from the commit: `seat_resolution_service.go:46/:53/:60` printed the three old texts, and `seat_mount.go:285` was `if strings.Contains(err.Error(), "not found")`.
- AFTER, as the tests print it: `TestResolveSeatStatusMapping` (httpapp) now carries four cases — the sentinels answer **404 with the surviving bodies** (`{"detail":"seat not found: seat \"x\""}` and `{"detail":"room not found: room \"dev\""}`), an anonymous error that merely says "not found" answers **500**, and `database down` is unchanged. `TestSeatMessageUnreachableSeatAnswersTheSame404` uses the sentinel and still asserts the write and pull bodies are byte-identical.
- NEW, closing the other end of the chain: `TestResolveSeatMissesCarryTheirSentinel` (services) proves the resolver itself wraps the three sentinels, so the routes' 404 is not resting on an untested link.
- `gofmt -l` on the four files printed nothing; `go vet ./fastmcp/seat_management/... ./fastmcp/server/httpapp/...` clean; `go test -count=1 ./fastmcp/...` green.
- Not run, stated rather than implied: no DB-backed path (this change touches none) and nothing was pushed.

Part of the identifier row `655227df` (commit 1 of the ruled order: error identity, then the session's own seat key).
