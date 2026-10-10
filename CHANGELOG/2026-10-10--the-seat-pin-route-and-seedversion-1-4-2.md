## The seat pin route: an existing seat's seat-type version can be changed, and seedVersion is 1.4.2

R1 of the rollout ruling (`DELEGATED-rollout-decision-2026-10-10.md`, item 1), assigned by the lead at 20:14Z and 20:16Z (queue row `qitem-20261010201603-e37ed8e0bb54f5b2`). Acceptance is recorded on board row `308c3ae3` progress 2.

### Added
- **`PUT /api/v2/openrig/rooms/{room}/seats/{seat}/pin`**, mounted in `fastmcp/server/httpapp/seat_admin_mount.go` beside the other seat mutations and wrapped in `seatMutation("seat", "updated", …)` so it emits exactly one seat-domain frame like its neighbours. Body: `{"pinned_version":"<version>"}`.
- **`SeatAdminService.SetPinnedVersion`** (`fastmcp/seat_management/application/services/seat_admin_service.go`), which resolves the seat, resolves its seat type's slug, and refuses a version that type does not have with `ErrInvalidSeatTypeVersion` *before* the store is touched. That error is already mapped to `http.StatusBadRequest` by `writeSeatAdminServiceError`, so the route reuses the refusal shape `handleCreateSeat` produces when a create pins a version that does not exist.
- **`SeatRepository.UpdatePinnedVersion`** (`infrastructure/repositories/orm/seat_repository.go`), an `UPDATE "seats" SET "pinned_version" = $1, "updated_at" = $2 WHERE "user_id" = $3 AND "id" = $4` mirroring `UpdatePermissionPolicy`; declared on the domain interface, the service's `SeatAdminStore` and the httpapp `seatAdminSource` so every implementation migrated with it.

### Changed
- **`const seedVersion` is `"1.4.2"`** (`fastmcp/seat_management/domain/seedmap/seedmap.go:14`). `origin/main` at `a3eb0762` already shipped the changed `guide-common` under **1.4.1**, so 1.4.1 names two different texts depending on when a database seeded; 1.4.2 has one text everywhere. No Go test pinned the old value (grep over the tree: only `.gomodcache` noise).

### Verified
- `go test ./fastmcp/server/httpapp/ -run TestSeatAdminPinSeatVersion -count=1 -v` -> `--- PASS: TestSeatAdminPinSeatVersion (0.00s)`, from the new `seat_admin_pin_test.go`. It drives the real route over `mountSeatAdminRoutes` (handler, service and its version check, not around them): pin to `9.9.9` on a type that has `1.0.0`/`0.9.0`/`1.4.2` -> **400**; pin to `1.4.2` -> 200 carrying `"pinned_version":"1.4.2"`; a following `GET /api/v2/openrig/rooms/dev/seats` reads back `"pinned_version":"1.4.2"` from the store rather than echoing the request; an omitted version -> 400, not a silent unpin; an absent seat -> 404.
- `go test ./fastmcp/seat_management/... -count=1` -> every package `ok`.
- `go vet ./fastmcp/seat_management/... ./fastmcp/server/httpapp/...` -> rc 0, which is also what forced the three test fakes (`fakeSeatAdminStore`, `controller fakeStore`, httpapp `fakeSeatAdmin`) to gain the two new methods in the same change.

### Regenerated
- `agenthub-frontend/src/docs/apiReference.ts`, by `cd agenthub_go && go run ./cmd/apirefgen` -> `wrote ../agenthub-frontend/src/docs/apiReference.ts: 145 routes, 10 tools`. The diff is +10 lines and is exactly the new route entry, checked against a fresh `-out /tmp/apiref-r1.ts` generation before writing in place. Every entry in that artefact carries an empty `handler`/`description`, so the new entry matches the file rather than leaving a gap in it.

### Not run
- No clean-export `go test ./... -count=1`: that is the architect's gate on this commit, and this worktree carries another seat's in-flight edits, so it cannot be run from here honestly. What was run for this change: `go test ./fastmcp/server/httpapp/ ./fastmcp/seat_management/interface/mcp_controllers/ -count=1` with `AGENTHUB_TEST_PG_URL` set -> both `ok` (230.673s / 0.004s); `go test ./fastmcp/seat_management/... -count=1` -> every package `ok`; `go build ./...` rc 0; `gofmt -l` on the nine files -> empty.
- No production write, no push, no deploy. The seat pins the ruling schedules (step 8) are the operator's, after the owner's approval.
- The resolver leg the gate also names ("to 1.4.2 -> the resolve returns 1.4.2") is not covered by a test here: this package's resolve cases run over a faked seat source returning a canned snapshot with no version, so that leg has to be measured where a real resolver and a database are wired.

### Left red on purpose, with the measurements
- `python3 scripts/COUNTS-AUDIT.py` exits **1**, on one row: `httpapp route registrations` - document and EXPECTED **124**, **tree 125**, which is this route. The route total moves **144 -> 145**. Both belong to a docs-duty pass, together with `ai_docs/api-integration/surface-inventory.md`, whose counts, route table and `file:line` citations this change dates.
- `python3 scripts/CITATION-AUDIT.py` exits **1** on 26 rows, all in `seat_admin_mount.go`, all from the same +5-line shift this change makes (`:330 -> :335`, `:333 -> :338`, … `:387 -> :395`). Its `--write` mode is refused while a gate marker is set, so it was not run.
