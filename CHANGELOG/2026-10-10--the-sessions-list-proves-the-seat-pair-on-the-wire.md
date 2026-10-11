## The sessions list proves the seat pair on the wire, and the API half was already there

### Added

- `agenthub_go/fastmcp/server/httpapp/ws_connector_test.go` — two cases over the DECODED body of `GET /api/v2/sessions` (row `54e5c4ce`). `TestSessionListCarriesTheSeatPairTheConnectorReported` drives a real connector socket whose session frame names a room and a seat, and asserts `room_slug` and `seat_key` arrive with the reported values; `TestSessionListCarriesAnUnreportedSeatPairAsNull` ingests a frame that names none and asserts both keys arrive as JSON `null` — present, and not `""`. Both are gated on `AGENTHUB_TEST_PG_URL` like the rest of the file, and both were run against a real Postgres.

### Corrected: the API half was not absent

The row read “the API half is absent: the DTO does not carry the fields”. Measured, it does carry them, and the missing half is the FRONTEND’s:

- `fastmcp/session_stream/repository.go` — `sessionRow` sets `room_slug` and `seat_key` (both keys, and `nil` when the connector named none); `sessionCols` selects the two columns and `scanAgentSession` scans them. Commit `14210172`’s own message says so: “The DTO gains room_slug and seat_key”.
- The list route serializes that map verbatim (`fastmcp/server/httpapp/session_stream_routes.go` → `session_stream.ListSessions`), so the fields were on the wire before this row.
- Why the row read otherwise: its search was `-S room_slug` over `agenthub_go/fastmcp/server`, and the DTO lives in the SIBLING package `agenthub_go/fastmcp/session_stream`. A search confined to one directory is not a measurement of the module.
- The rest of the chain is in the tree too, so nothing needed “adding”: the client’s connector reports the pair (`agenthub_client/internal/clientsync/connector.go`, `RegisterSession` → `sessionFrame`, whole-or-omitted, committed as `13c6e90`), the ingest reads `room`/`seat` from the frame (`fastmcp/server/httpapp/ws_mount.go:349`), and `UpsertSession` validates the pair (`seatIdentity`).
- The row’s third acceptance line — “resolve the room slug server-side in one place from the connector’s logicalId” — describes the opposite of the design `14210172` landed and `13c6e90` implements: the CONNECTOR resolves the pair from its own `rig ps --json` (`connectorverb.go:294-298,307-317`) and REPORTS it at ingest, and the SERVER validates rather than re-derives it. No code was changed here; the sentence needs the lead’s ruling, not an edit.

### Not changed

- `fastmcp/session_stream/repository.go` is byte-identical: its two DTO `m.Set` pairs were removed ONLY long enough to watch the new cases fail, then restored — `git diff` on that file is empty.
- No route, verb, endpoint or client edit. The frontend’s consumption of the fields stays row `64a95f59` (@web-dev); the fields it needs are now proven to arrive.

### Testing

From `agenthub_go` with `GOCACHE` and `TMPDIR` inside `.gocache`/`.gotmp`, against a real Postgres (`tools/testpg/start.sh`, port 55432):

- Red first, measured: with `sessionRow`’s two `m.Set` pairs removed, both cases failed naming the absent keys and printing the whole response map (`room_slug is absent from the response map[...]`). Restored, both pass — `ok agenthub/fastmcp/server/httpapp 1.113s` with just this selection.
- `go test ./fastmcp/session_stream/... ./fastmcp/server/httpapp/...` → `ok 1.169s` and `ok 12.838s` (whole packages, no skips). `gofmt -l` on the touched file printed nothing; `go vet ./fastmcp/server/httpapp/... ./fastmcp/session_stream/...` was clean.
