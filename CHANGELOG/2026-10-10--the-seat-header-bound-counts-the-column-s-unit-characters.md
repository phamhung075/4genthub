## The seat header bound counts characters, because that is what the column counts

### Changed

- `agenthub_go/fastmcp/seat_management/domain/mcpblock/mcpblock.go` — `ValidateSeatValue` measures the header with `utf8.RuneCountInString` instead of `len`, and the refusal says "characters" rather than "bytes". `SeatValueMaxLen`'s doc comment now states why: `task_events.actor_id` is `VARCHAR(255)`, and PostgreSQL's `VARCHAR(n)` counts **characters**, so a byte bound is not the column's rule.
- `agenthub_go/fastmcp/seat_management/domain/mcpblock/mcpblock_test.go` — the width section gains a pair in the column's own unit: 255 characters carried in 505 bytes is **ACCEPTED**, and 256 characters is refused with the length named in characters. The fixture asserts its own shape first — that it is 255 characters *and* wider than 255 bytes — so the case cannot pass by accident against a byte bound.

### Why the safe direction was still wrong

The reviewer raised this as a nit: a bound in bytes can only refuse more, never less, so nothing illegal reaches the database. That reasoning is sound about the failure it was guarding and silent about the failure it creates: a seat key carrying an accented letter at the column's own width is a **legal identity**, and the boundary would have refused it — the caller loses a write the database would have accepted, which is the exact harm the check exists to prevent, just decided by the wrong rule. Refusing more is only safe while everything refused is junk.

### Testing

From `agenthub_go` (`GOCACHE`/`TMPDIR` in-tree, throwaway PostgreSQL on 55432):

- `gofmt -l fastmcp/seat_management/domain/mcpblock/` printed nothing; `go vet` on the package clean; `go test -count=1 ./fastmcp/seat_management/domain/mcpblock/` **ok**, the multi-byte pair included.
- The boundary case re-run end-to-end with the database: `TestMCPStatusCallWithAnUnusableSeatHeaderIsRefusedBeforeTheWrite` **PASSES**, observing `POST /mcp` with a 256-byte seat header -> `200` carrying `INVALID_SEAT_HEADER`, and the message now reads `seat header is 256 characters, past the 255 an actor id is recorded in`. `TestMCPStatusCallIsAttributedToTheSeatThatMadeIt` **PASSES** unchanged.
- Nothing pinned the old wording: a search for `bytes, past` / `past the 255` across the test files finds no assertion, so this commit changes behaviour and message together without rewriting a test to match.
- ASCII behaviour is unchanged — 255 accepted, 256 refused — because for ASCII one character is one byte.
