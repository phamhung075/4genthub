## The seat message route carries the room, so a seat that is not there answers 404

### Changed

- `agenthub_go/fastmcp/server/httpapp/seat_mount.go` — the seat chat window's route moves from
  `POST /api/v2/openrig/seats/{seat}/messages` to
  `POST /api/v2/openrig/rooms/{room}/seats/{seat}/messages`, the shape every other seat
  sub-resource already uses (`/overlay`, `/links`, `/occupant`). A bare seat key cannot name a
  seat: the schema's `uq_seats_room_seat_key` makes a seat unique per `(room_id, seat_key)`, so a
  key-only path could name one only by guessing its room, and the guess is silently wrong for every
  user with two rooms carrying the same seat key. The route therefore no longer shares a path with
  the resolution `GET /api/v2/openrig/seats/{room}/{seat}`, which keeps both its path and its verb.

### Added

- `agenthub_go/fastmcp/server/httpapp/seat_mount.go` — the 404 branch the key-only shape could not
  have. The handler resolves the seat **in the room named in the URL**, so a seat that is not in
  that room is answered **404**, and the resolver is asked for the pair the URL carries rather than
  a guessed one.
- `agenthub_go/fastmcp/server/httpapp/seat_mount.go` — `writeSeatResolutionError`, now shared with
  the resolution handler, so both seat routes that resolve a seat map "not found" to **404** and
  anything else to **500** in one place instead of twice.

### Not changed, and why

- The refusal is still a refusal. The auth gate, the `{text}` body with `DisallowUnknownFields`,
  and the **501** whose detail ends "Nothing was sent" are untouched, because delivery stays
  client-side until the delivery store exists (row (c)); this route is that row's prerequisite.
- The body is still decoded BEFORE the seat is resolved, so a malformed request is refused for
  being malformed rather than for the seat's absence.
- The resolution `GET /api/v2/openrig/seats/{room}/{seat}` does not move: its path is a live client
  contract and nothing here needs it changed.

### Testing

- `gofmt -l` on both files → nothing. `go vet ./fastmcp/server/httpapp/...` → rc 0. `go test
  -count=1 ./fastmcp/server/httpapp/...` → **ok**.
- **SEEN RED FIRST, ON THE REAL CAUSE:** with the resolve-and-404 branch replaced by a discarded
  call, `TestSeatMessageRouteResolvesTheSeatInTheRoomTheURLNames` fails on the
  seat-not-in-the-room subtest with `status = 501, want 404` — the defect this row reports — and
  passes restored. `md5sum -c` confirms both files were restored byte-identical.
- **AND ONE RED I CAUSED MYSELF, RECORDED RATHER THAN QUIETLY CORRECTED:** the first run of the new
  cases wrote the path without its `/seats/` literal, and every one of them answered `404 page not
  found`. That is what proves these cases observe the mounted pattern rather than their own
  fixture, and it is why the fix went into the test's path and not into the pattern.

### Known, and NOT fixed here

- `agenthub-frontend/src/docs/apiReference.ts` is generated from this route table and is now one
  entry behind: `go run ./cmd/apirefgen -out /tmp/apiReference.ts` adds exactly one route
  (`POST /api/v2/openrig/rooms/{room}/seats/{seat}/messages`, 10 lines, 144 routes total), and
  `agenthub_go/internal/apiref TestTheCommittedArtefactMatchesTheProducer` stays red until that
  file is regenerated. **That gate was already red at HEAD**, for the key-only route it never
  listed, and it is red for the moved route here. The artefact is a frontend file, so it is left to
  the frontend half of this batch rather than regenerated in a Go commit that the freeze covers.
