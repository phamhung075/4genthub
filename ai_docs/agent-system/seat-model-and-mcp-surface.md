# Seat model and MCP surface

> Moved out of the root `AGENTS.md` on 2026-10-05 (see
> [`agents-md-migration-map.md`](./agents-md-migration-map.md)). The authoritative list of mounted
> routes, tables and MCP tools is `ai_docs/api-integration/surface-inventory.md`; this file is the
> agent-facing summary.

## Identity first

Run `rig whoami --json`. It returns your rig, pod, member, peers, edges and transcript path, and it
is the ground truth for where you are. A startup overlay can be stale; re-run it after any
compaction, restart or restore.

## The seat model

A **seat** is the durable position (role, address, lineage, pinned version). The **occupant** is the
brain currently sitting in it (a runtime plus a model). Address an exact seat through the seat
model — the surface that works today:

- `mcp__agenthub_http__manage_seat` `action="list", room="<room>"` — every seat in a room: id, seat
  type, pinned version, runtime, model, permission policy.
- `mcp__agenthub_http__manage_seat` `action="get", room="<room>", seat="<seat>"` — one exact seat.
- `mcp__agenthub_http__manage_seat` `action="set_occupant"` — switch that seat's runtime and model.
- `mcp__agenthub_http__call_seat` `room="<room>", seat="<seat>"` — resolve a seat's config and its
  rendered context files.

There is no per-agent template lookup: the 32-agent template library was removed (Request 14, T6).
Identity comes from `rig whoami --json`; a seat's resolved config comes from `manage_seat` /
`call_seat`.

## Tool scope by seat

A seat's tool scope comes from its seat type and its runtime. The source is the nine embedded seat
types in `agenthub_go/fastmcp/seat_management/domain/seedlibrary/seat-types/` — `architect`,
`debugger`, `developer`, `lead`, `planner`, `researcher`, `reviewer`, `tester`, `writer` — resolved
per seat by the Go seat service.

Rules:

- Know your seat first: `rig whoami --json`.
- Never assume you have a tool another seat type has; read the seat's rendered files before relying
  on a capability.
- If you need a tool your seat lacks, route the work to a seat that has it.

## Published MCP tools (source of truth for tool names)

```
mcp__agenthub_http__manage_task        # Tasks
mcp__agenthub_http__manage_subtask     # Subtasks
mcp__agenthub_http__manage_context     # Context hierarchy
mcp__agenthub_http__manage_project     # Projects
mcp__agenthub_http__manage_git_branch  # Branches
mcp__agenthub_http__manage_agent       # Agent registry
mcp__agenthub_http__manage_seat        # Seats: list, get, set_occupant
mcp__agenthub_http__call_seat          # Resolve one exact seat
mcp__agenthub_http__submit_feedback    # Report friction (room, seat, session, layer, text)
mcp__agenthub_http__manage_connection  # Health check
```

**The live registry publishes TEN tools, and this list is the ten** — corrected 2026-10-09 at
`734b2072` because the block above named nine while the sentence below claimed ten: `submit_feedback`
was missing (it became a published tool when the friction channel landed, and
`ai_docs/api-integration/mcp-tools-api-complete.md` — the list this file defers to — already carries
all ten). **How the ten arise, so a reader can check rather than count:** six are carried by
`ToolDefinitions` (`agenthub_go/fastmcp/task_management/interface/ddd_compliant_mcp_tools.go:223-249` —
`manage_task`, `manage_subtask`, `manage_context`, `manage_project`, `manage_git_branch`,
`manage_agent`), and **four more are appended by `MCPToolsList`
(`agenthub_go/fastmcp/server/httpapp/mcp_routes.go:265`)** because their controllers own their
schemas: `manage_seat` (`:302`), `call_seat` (`:311`), `submit_feedback` (`:320`) and
`manage_connection` (`:324`, from `connectionToolDefinition()`). `manage_context` is emitted only when
the context controller is wired, which a database-backed server does. **Re-measured at this commit
with the generator rather than by hand:** `cd agenthub_go && go run ./cmd/apirefgen -out
/tmp/apiref.ts` -> `143 routes, 10 tools`. `tools/list` is not gated by any `TOOL_*` environment
variable. See `ai_docs/api-integration/mcp-tools-api-complete.md` for the per-tool arguments.

> **Superseded.** The earlier AGENTS.md section "MCP TOOL PERMISSIONS" stated that only the
> principal session has MCP access and that team agents have none, and described a "Proxy Pattern"
> that injected config into sub-agent teams. That model is retired: each seat receives its own role
> file at launch and reaches the agenthub MCP tools itself. There is no config-injection proxy.

## Knowledge management

- Project documentation: `ai_docs/` (kebab-case folders, one topic per folder).
- Index: `ai_docs/index.json` — machine-generated, never hand-edit.
- Search existing docs before creating new ones.
