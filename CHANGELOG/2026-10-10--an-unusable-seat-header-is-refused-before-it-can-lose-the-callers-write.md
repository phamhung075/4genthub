## An unusable seat header is refused before it can lose the caller's write

### Changed

- `agenthub_go/fastmcp/seat_management/domain/mcpblock/mcpblock.go` — `SeatValueMaxLen` (255, the width of `task_events.actor_id`) and `ValidateSeatValue`, which refuses a value past that width or one that has no `<room>/<seat>` shape. The rule lives with the header's own shape so the renderer and the route cannot disagree about how long an identity may be. It splits only at the FIRST separator, so a seat key that itself contains one is still accepted, and it quotes at most 60 bytes when it prints — a hostile header must not be able to inflate the message.
- `agenthub_go/fastmcp/server/httpapp/mcp_routes.go` — the MCP boundary validates the header and returns `INVALID_SEAT_HEADER` as the tool's own error result BEFORE anything is attempted, instead of letting the value reach the INSERT.

### Why this is a fix and not a nicety

The header is recorded in `task_events.actor_id VARCHAR(255)`, and that INSERT shares the caller's transaction with the status write it describes. An over-long header therefore did not merely record a strange actor id: it ROLLED BACK THE CALLER'S OWN STATUS WRITE — a header losing a legitimate write. The reviewer measured it in the O2 gate, and the lead dispositioned it as a real fix rather than a recorded note. No access consequence is claimed or implied: the header is attribution only, and this is about a write being lost, not about one being allowed.

### Testing

From `agenthub_go` (`GOCACHE`/`TMPDIR` in-tree, throwaway PostgreSQL on 55432):

- `gofmt -l` on both packages printed nothing; `go build ./...` ok; `go vet` on both clean.
- `TestSeatValueRoundTripsThroughItsOwnValidator` and `TestValidateSeatValueRefusesWhatCannotBeAnActorID` (`mcpblock`, no database): every value `SeatValue` produces is accepted, including a key that contains a separator; the boundary widths are the fixtures — 255 accepted, 256 refused; `""`, `alpha`, `/beta` and `alpha/` are refused; the refusal names the length and stays under 200 bytes.
- `TestMCPStatusCallWithAnUnusableSeatHeaderIsRefusedBeforeTheWrite` (`httpapp`, real database): observed `POST /mcp` with a 256-byte seat header → `200` carrying `INVALID_SEAT_HEADER`, with the task still `todo` and **0** entries recorded for it.
- **RED FIRST, MEASURED**: with the boundary check disabled the same case failed `the refusal does not name itself`, observing the reported defect end to end — `{"success": false, "error": {"message": "Unexpected error: ERROR: value too long for type character varying(255) (SQLSTATE 22001)", "code": "OPERATION_FAILED", "operation": "update"}}` — the caller's own write attempted, refused by the database, and rolled back.
- `TestMCPStatusCallIsAttributedToTheSeatThatMadeIt` re-run with the landed vocabulary: `entry actor = seat/"alpha/beta"` with the header, `human/"<the scoped id>"` without it.

### One of my own steps was wrong, and the record says so

The validator's cases were first written with `write`, which REPLACED this package's existing `mcpblock_test.go` — six tests (`Parse` http/stdio/errors/env references, `CheckURL`, the fragment's JSON shape) and its `platformBlock` fixture — instead of extending it. `git show --stat` on the commit caught it (163 changed lines where 58 were expected), the file was restored from the commit before it with the two cases appended, and the commit was amended: the package now runs EIGHT cases, all passing. The rule this team already has — a tool's success report is an indicator, so read the artefact back — is what found it, and the count of test functions in the file is the evidence.

### Not covered, named rather than implied

The validator checks width and shape, NOT existence: a well-formed header naming a seat that was never resolved is still recorded as an actor id, because resolving a seat is the resolver's business and attribution is not authorization. Nothing is pushed and `/health` was not touched.
