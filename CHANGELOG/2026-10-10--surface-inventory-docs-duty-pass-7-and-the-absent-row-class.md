## Docs duty pass 7: the surface inventory gains the seat-pin route, and a class of defect neither count instrument can see

Writer seat, at `42de79c2`, after that commit added one route and shifted 28 citations.

### Added
- **`PUT /api/v2/openrig/rooms/{room}/seats/{seat}/pin`** (`seat_admin_mount.go:362`, handler `handleSetSeatPin`) joins the §1.16 table in file order, between `permission-policy` and `overlay`. It was the **only** live route with no row: §1 held **144 rows for 145 registrations**.

### Changed
- **§1's counts now read `145 = 125 httpapp + 20 auth`** (the Reproduce line, re-run at `42de79c2`), from `144 = 124 + 20` at `a7990665`. The MCP tool count is unchanged at **10**. `scripts/COUNTS-AUDIT.py`'s `EXPECTED` for `httpapp` route registrations moved **124 -> 125** with the move recorded in its own comment, which is where previous passes recorded theirs.
- **28 drifted `file:line` citations re-resolved** in `ai_docs/api-integration/surface-inventory.md` by that file's own tool, in its writing mode outside any gate: `CI= python3 scripts/CITATION-AUDIT.py --write` -> `rewrote 28 citations`, touching only that document. The drift is all in the family `42de79c2` edited — `seat_admin_mount.go` **+5..+8** below the inserted registration and its closure, `mcp_routes.go` **+2**.

### Verified
- `python3 scripts/COUNTS-AUDIT.py` -> **exit 0**, all eleven headline rows matching the tree and the document.
- `python3 scripts/CITATION-AUDIT.py` -> **exit 0**, `rows 145  stale 0  unresolved 0` (before the rewrite: `rows 145  stale 28  unresolved 0`, exit 1).
- **The join, which is the new control**: every `| METHOD | \`path\` |` row of §1 extracted and matched against the generator's own emitted list (`cd agenthub_go && go run ./cmd/apirefgen -out /tmp/api2.ts` -> `wrote /tmp/api2.ts: 145 routes, 10 tools`) -> `doc rows 145 | live 145 | doc-not-live 0 | live-not-doc 0`. Before this pass the same command read `doc rows 144 | live 145 | live-not-doc [PUT .../seats/{seat}/pin]`.

### Why the join is now recorded in the document
`COUNTS-AUDIT.py` compares counts and `CITATION-AUDIT.py` compares pointers; **neither notices a row that is simply absent**, and when one is absent both instruments agree with each other while the table is short by one. That is the shape this pass found, so §1 now names the join and the two commands that reproduce it.
