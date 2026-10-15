# Communication links allowed across all runtimes, and minimum team topology edges published

### What changed
1. **Removed runtime restriction on allowing communication links**:
   In `agenthub_go/fastmcp/server/httpapp/seat_admin_mount.go`, `handleUpsertSeatLink` previously rejected non-`claude-code` runtimes (such as `omp` or `codex`) with `400: allowing communication links are restricted to claude-code seats: runtime "<r>" has no verified deny path`.
   This restriction has been removed so any seat runtime (including `omp` and `codex`) can hold allowing communication links (`seat_links`), matching the owner's decision to support all active agent runtimes.
2. **Updated test suite**:
   `TestSeatAdminLinkRestrictedToClaudeCodeSeats` in `agenthub_go/fastmcp/server/httpapp/seat_admin_mount_test.go` was updated to assert that allowing links to/from `codex` and `omp` are permitted and return HTTP 200.
3. **Topology edges reported for `4genthub-min`**:
   The topology edges representing delegations, collaborations, and escalations between `lead`, `go-dev`, `reviewer`, `fe-dev`, and `architect` are now reported to `/api/v2/seat-status` and visible in `GET /api/v2/machines`.

### Verified
- `go test ./fastmcp/server/httpapp/...` passed cleanly (1.75s).
- Changes committed and pushed to `origin/main` (`bcfbb1fa`).
- Verified edge resolution on cloud endpoints (`https://api.4genthub.com/api/v2/machines`): 13 directed links for `4genthub-min` resolved.
