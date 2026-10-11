## The seat pin's ORM UPDATE is executed by a committed test at last

### Added
- `agenthub_go/fastmcp/server/httpapp/seat_admin_pin_pg_test.go`: `TestSeatAdminPinSeatVersionAgainstTheRealStore` - R1's acceptance driven through the real store, so the statement

  ```sql
  UPDATE "seats" SET "pinned_version" = $1, "updated_at" = $2 WHERE "user_id" = $3 AND "id" = $4
  ```

  (`fastmcp/seat_management/infrastructure/repositories/orm/seat_repository.go:109`-`:117`) is finally executed by a committed case. The committed case beside it (`seat_admin_pin_test.go`) drives the same route through `newFakeSeatAdmin()`, so the handler -> service -> version-check seam was covered while the statement that writes the row was not: the reviewer's post-hoc APPROVE on `42de79c2` and the architect's finding both said so, and the only proof was a scratch run against a real PostgreSQL that did not survive its session.
  - It seeds a room, a seat type with two version ROWS (`0.9.0`, `1.4.2`) and a seat pinned to the older one, then mounts `mountSeatRoutes` and `mountSeatAdminRoutes` over the real session manager in the order `app.go` mounts them - the second mount's argument is what resolves its source, so the package-level seams the fake case overrides stay default and the store IS the database.
  - Every assertion reads the COLUMN, not the response: a refused pin must leave the row at `0.9.0` (the version check has to run before the UPDATE), an accepted pin must leave it at `1.4.2` (the UPDATE has to reach it), the room's seats must read the row back, the resolved seat must render the pinned version, and an absent seat must be a 404 decided by the store.
  - The run prints the mount's own line, which is the statement doing its work rather than a double echoing a request: `[SEAT] user 11111111-1111-4111-8111-111111111111 pinned dev/alice to 1.4.2`.

### Verified
- `gofmt -l` empty on the new file; `go build ./...` rc 0; `go vet ./...` rc 0.
- `AGENTHUB_TEST_PG_URL=… go test -count=1 -run TestSeatAdminPinSeatVersionAgainstTheRealStore -v ./fastmcp/server/httpapp/` -> **PASS (1.40s)**, `ok agenthub/fastmcp/server/httpapp`.
- The first run of this case is what made the case honest: the resolved-seat route answered 404 because the admin mount does not carry it, so the case now mounts `seat_mount.go`'s route as well. Without the fix it fails; the failure is quoted in `TEST-CHANGELOG.md`.
