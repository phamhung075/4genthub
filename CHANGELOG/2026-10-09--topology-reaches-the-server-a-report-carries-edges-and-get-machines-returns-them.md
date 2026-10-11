## Topology reaches the server: a report carries `edges`, and `GET /machines` returns them

### Added
- `POST /api/v2/openrig/seat-status` accepts `"edges":[{"room","from","to","kind"}]` — one directed link per entry, `kind` one of OpenRig's five (`commpolicy.ValidKind`, so the vocabulary has one home rather than a third copy), `room`/`from`/`to` under the same name rule as room slugs and seat keys, capped at **1000**. A report **replaces** the machine's edge set, like its seats and agents, so a report carrying no `edges` key is accepted and stores the empty set — which is the shape the bridge in flight sends.
- `GET /api/v2/openrig/machines`: every machine body carries `"edges"`, always present (empty when the machine reported none), in the order reported. The wire names the two ends `from` and `to`.
- `machine_edges` (`user_id`, `machine_id`, `room`, `from_seat`, `to_seat`, `kind`; all six are the primary key), registered in `seat_tables.go` and in `seat_management_postgresql.sql`, with `ck_machine_edges_kind` and the distinctness CHECK its sibling `seat_links` carries. The columns are `from_seat`/`to_seat` because `from` and `to` are SQL keywords. **No CASCADE**: `DeleteRoom` removes the room's edges explicitly, and the deletion-paths scenario counts the new table.

### Fixed
- A malformed edge is refused with a 400 that names the field — `edges[0].kind`, `edges[1]: duplicate edge`, `edges[1]: from and to are the same seat` — instead of being stored, silently collapsed by the primary key, or drawn as a self-loop.

### Verified
- **The edgeless report was tested BEFORE the change**: `TestSeatStatusPostWithoutEdgesIsAcceptedAndServesAnEmptyEdgeSet` is written against the HTTP contract only, so it ran against the old server, failed with `the machine body carries no edges key`, and passes now. The other acceptance cases have their own tests: round trip and replace-to-empty (a), malformed edges naming the field and the 1000 cap (d), the unknown-field control inside an `edges` element (c), edges grouped to their own machine and the tenant-and-room-scoped delete (e), plus the admin room-delete assertion that the cascade ran.
- Checks: `gofmt -l` clean, `go build ./...` rc=0, `go vet ./...` rc=0, `go test -count=1 ./...` **144 packages ok**.
- **NOT RUN, and owed to a host with PostgreSQL**: `TestSchemaMigrationIsIdempotentInProcess` and `TestDeletionPathsIntegration` both skip loudly here (`AGENTHUB_TEST_PG_URL` unset, and this machine has no `postgres`/`psql` binary), so this packet's schema-upgrade proof is the in-process idempotence gate plus the two-binary procedure, and neither ran.
- **ORDERING, because it prevents an outage**: the status body is decoded with `DisallowUnknownFields`, so a bridge that sends `edges` to a server without this change gets a 400 on EVERY report — which reads as the machine going offline, not as a rejected field. The server half ships first; the bridge half is held until it is gated.
