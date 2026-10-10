## `session_health_tool.go` names the dispatch symbol instead of a line that had rotted

### Fixed
- `agenthub_go/fastmcp/server/session_health_tool.go:6`: the doc comment said the check is dispatched "from the MCP route as `check_session_health` (httpapp/mcp_routes.go:332)". At HEAD the `case "check_session_health"` arm is `mcp_routes.go:386` (`case "get_mcp_status"` is `:380`, the default arm `:492`). **The number is dropped rather than corrected:** the comment now names the dispatch symbol and its file (the MCP route's `case "check_session_health"`, in `httpapp/mcp_routes.go`) — because a symbol cannot rot and this number already did. The citing file carries exactly ONE citation, re-measured here; no other number in it was touched.
