## The published-tools rows no instrument reads: audited by hand, five anchors repaired

### Changed
- `ai_docs/api-integration/surface-inventory.md` — §2.3's published-tools table is the one table
  `scripts/S3-REDERIVE.py` declares **outside both instruments** (10 rows, 15 anchors, skipped by
  `CITATION-AUDIT.py` because its row shape needs a METHOD where this table puts a tool NAME). All 15
  anchors were resolved by hand against the tree: **ten exact, five stale** — the five in `mcp_routes.go`
  (`302 → 304`, `311 → 313`, `320 → 322`, `328 → 330`, bare `:324 → :326`).
- The same sweep re-resolved every other live `mcp_routes.go` pointer in §2.1–§2.4: `MCPToolsList`
  `275 → 277`, the `len(defs)+4` line `285 → 287`, the four appends `301/310/319/328 →
  303/312/321/330`, `handleJSONRPC` `174 → 176`, `authorizeMCPMethod` `146 → 148`, `dispatchMCPTool`
  `347 → 349`, `get_mcp_status` `380 → 405`, `check_session_health` `386 → 411`, unknown-tool `default`
  `492 → 518`. The two dated passes above keep their own numbers as their record; a dated
  re-resolution note records the mapping.

### Verified
- Each new number was read from the file, not computed: `grep -n` for `ManageSeatToolName`,
  `CallSeatToolName`, `SubmitFeedbackToolName`, `connectionToolDefinition`, `dispatchMCPTool`,
  `func (a *App) MCPToolsList`, `authorizeMCPMethod`, `handleJSONRPC`, `get_mcp_status`,
  `check_session_health` and `Unknown tool`, then the cited lines printed one by one.
- The control against a blanket renumbering holds: §1.6's `mcp_routes.go:76` and `:141` did not move and
  `CITATION-AUDIT.py` still reads its 145 rows fresh, while the dispatch region drifted +25/+25/+26.
- After the edit: `S3-REDERIVE.py` `FRESH 66` rc=0, `COUNTS-AUDIT.py` rc=0, `CITATION-AUDIT.py`
  `rows 145 stale 0 unresolved 0` rc=0.

Seat: 4genthub-min-writer@4genthub-min
