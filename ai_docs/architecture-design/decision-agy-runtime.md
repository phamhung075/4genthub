Decision: Add the `agy` (Gemini/Antigravity) runtime to the 4genthub Go backend
Context: The backend must support the `agy` runtime for Gemini-powered seats so `manage_seat set_occupant` can record it. Like `codex`, it requires no Claude fragments.
Options:
- Option A (Explicit exclusion in renderer): Add `agy` to `resolver.CheckRuntime`, the API status enum, and the MCP schema. In `seatrenderer.RenderSeat`, explicitly reject `codex` and `agy` from receiving Claude fragments via a shared predicate. In `names.ValidateOccupant`, reject Claude models for both `codex` and `agy`.
- Option B (Implicit exclusion in renderer): Same additions, but rely on the existing positive `if seat.Runtime == resolver.RuntimeClaudeCode` check in `seatrenderer` to naturally omit Claude fragments for `agy`. Update only comments in the renderer.
Recommendation: Option B. The renderer already operates positively (giving Claude fragments only to `claude-code`); keeping this behavior is simpler and less error-prone. We should also enforce that Claude models are rejected on the `agy` runtime in `ValidateOccupant` for safety.
Interfaces:
- `resolver.CheckRuntime`: Output changes to accept `"agy"` and error message is widened.
- `names.ValidateOccupant`: Input now rejects `claude-` models when runtime is `agy`.
- `seat_status_mount.go (seatRuntimes)`: Input map accepts `"agy": true`.
- `manage_seat_controller.go`: MCP schema description includes `"agy"`.
Risks: Tests enforcing the exact two-runtime error message will fail and must be updated. A machine reporting `agy` status could be rejected if the API enum is missed. Detect by ensuring all tests in `resolver`, `names`, `seatrenderer`, `httpapp`, and `mcp_controllers` are updated and pass.
Handoff: Handing off to `go-dev` (via the lead) to implement the runtime additions and test updates.
