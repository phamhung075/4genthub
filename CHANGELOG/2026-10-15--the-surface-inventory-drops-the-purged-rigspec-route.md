## The surface inventory drops the purged rigspec route, and the census goes green on main

### Fixed

- `ai_docs/api-integration/surface-inventory.md`: **§1's census was RED on main — `rows 148 / stale 6 / unresolved 1`, the three failures in `scripts/tests/test_census_audits.py` — and the ONE UNRESOLVED was the whole cause.** `inv:286 GET /api/v2/rooms/{room}/rigspec` cited `seat_rigspec_mount.go:105`, and **`cbc51bae` ("refactor: purge the legacy rig client; client routes move to /api/v2") deleted that file** (`0 230` on the path) with the route it mounted. **The row is struck, §1.17's title no longer says `/ rigspec`, and the removal is a §4 gone-list entry carrying its own commands and results** — struck rather than kept as a tombstone, because the inventory lists what exists and §4 is the section whose job it is to establish what is gone.
- The same purge is the count movement: `httpapp` registrations `136 -> 135`, so §1's Reproduce line heads with **155 (httpapp 135, auth 20)** and `scripts/COUNTS-AUDIT.py`'s `EXPECTED` follows the TREE to 135. **Re-derived, not adjusted**: the same pattern returns **136** at `df5e9069` (`cbc51bae^`) and **135** at `1a5d4ddc`, and the purge's `--numstat` on that path is a pure delete.
- The six STALE rows (`inv:77`-`82`, the `/api/v2/projects` family in `app.go`) were pointer drift, not wrong methods. `CI= python3 scripts/CITATION-AUDIT.py --write` rewrote them (`rewrote 6 citations`, touching only the inventory) and the checking mode then reads **`rows 147 stale 0 unresolved 0`** — 147 rather than 148 because the struck row left the count.

### Changed

- `agenthub_go/fastmcp/server/httpapp/ws_mount_test.go`: **the orphan-cite class the lead's row named is gone, and the file was swept for the class in the same pass** (it holds one such comment and three numbers: `:680`, `(:701)`, `(:748)`; all three are gone). `TestRealtimeDispatchAcceptsExactlyPingHeartbeatAndSubscribe`'s comment makes the same claim, anchored to its sentences, and says WHY the numbers went: they named `agenthub_main/src/fastmcp/server/routes/websocket_routes.py`, deleted with the Python backend by `a50929c6`, so a number there resolves for no reader — **and a bare `:NNN` resolves for no reader even when its file exists.**

### Testing

- `CI= python3 scripts/CITATION-AUDIT.py` -> `rows 147  stale 0  unresolved 0`, rc 0, at the committed tip; the instrument is the one a gate runs, and its `--write` mode was used outside a gate, as its own header requires.
- `python3 scripts/COUNTS-AUDIT.py` -> rc 0, "all numbers re-derived and matching"; the `httpapp` row now reads `135  135  135  matches`.
- `python3 -m pytest scripts/tests -q` -> **97 passed** at the committed tip. The three that were failing are `test_census_audits.py`'s own HEAD assertion, which exports the COMMITTED revision by construction — so they could pass only once the fix was HEAD, which is why the suite is measured after the commit rather than before it.
- `gofmt -l agenthub_go/fastmcp/server/httpapp/ws_mount_test.go` prints nothing and `go test ./fastmcp/server/httpapp/` exits 0: the touched case still pins the same accepted set, and no assertion was weakened to make the comment edit look green.
