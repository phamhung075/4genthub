## The room body names the caller's standing: `role`

## 2026-10-10 - the room body gains `role` (go-dev; web-dev's ASK, row qitem-20261010202810-666fe51fdba0ec91)

### Added
- `role` on every room body: `teamrepositories.RoleOwner` when the room's own owner column is the caller, `RoleViewer` otherwise. The vocabulary is the one the teams route already emits (`team_mount.go:157`), so a room row and a team row name the same fact the same way - a second spelling (`owned: true`) would be a second source of truth for one concept.
- Three call sites, each of which already held the caller: `seat_admin_mount.go:643` (create), `:659` (list), `:755` (the share echo). The body builder now takes the caller id; no route, method, request body or error shape changed, and `team_id` is unchanged.

### Why
`ORMRoomRepository.List` returns the caller's own rooms PLUS the rooms shared with their teams, and `team_id` is non-empty for BOTH an owner of a shared room and a viewer reading it. So on `/seats` a viewer's shared room was indistinguishable from their own: any client default ships one of two wrong states - either it hides a control the server honors for the owner, or it offers one the server refuses with 404 (the room row already offered Delete room and Add seat to a viewer; `TestSeatAdminViewerCannotMutate` proves the refusal).

The value is derived server-side from the ownership the write paths already authorize on: a mutation matches `"user_id"` = the caller, and `SetTeam` answers `ErrRoomNotOwned` otherwise. The wire therefore cannot say `owner` for a caller those routes would 404 on, which is the property that matters - a client-side derivation would have had to guess from `team_id`, which is exactly the field that cannot answer it.

### Verified
- RED FIRST, then GREEN: `TestSeatAdminRoomRole`, applied against HEAD's `seat_admin_mount.go` in a throwaway worktree at `42de79c2`, fails with `the shared room read role <nil> to a member, want "viewer"`; with the change it passes. Both runs are `agenthub/fastmcp/server/httpapp`.
- `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test ./fastmcp/server/httpapp/ -count=1` -> `ok` 110.077s (full package, PG-backed cases included).
- `go build ./...` rc 0; `gofmt -l` empty on both touched files.
- `python3 scripts/COUNTS-AUDIT.py` rc 0 ("all numbers re-derived and matching"); `python3 scripts/CITATION-AUDIT.py` rc 0 ("rows 145 stale 0 unresolved 0"). The change adds no route and moves no cited line.

### Not run
- No push, no deploy, no production read or write.
- `agenthub-frontend/src/docs/apiReference.ts` was NOT regenerated, deliberately: it lists routes and tools, and this change adds neither. Regenerating would have been churn.
