# Seat model and MCP surface

> The authoritative list of mounted
> routes, tables and MCP tools is `ai_docs/api-integration/surface-inventory.md`; this file is the
> agent-facing summary.

## Identity first

Run `4genteam whoami --json`. It returns your rig, seat, peers, edges and transcript path, and it
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
Identity comes from `4genteam whoami --json`; a seat's resolved config comes from `manage_seat` /
`call_seat`.

An occupant change is **recorded durably**: `set_occupant` writes one append-only
`seat_occupant_changes` row in the same transaction as the `seats` overwrite, naming the
authenticated actor, the instant, the seat and the previous and next runtime/model — so who
switched a seat, when and from what to what is answerable after the fact, through
`GET /api/v2/rooms/{room}/seats/{seat}/occupant-history`. The row is the stored occupant the next
launch reads; a running seat keeps the runtime it launched with
(`ai_docs/core-architecture/seat-occupant-record.md`).

## Tool scope by seat

A seat's tool scope comes from its seat type and its runtime. The source is the nine embedded seat
types in `agenthub_go/fastmcp/seat_management/domain/seedlibrary/seat-types/` — `architect`,
`debugger`, `developer`, `lead`, `planner`, `researcher`, `reviewer`, `tester`, `writer` — resolved
per seat by the Go seat service.

Rules:

- Know your seat first: `4genteam whoami --json`.
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
mcp__agenthub_http__manage_seat        # Seats: list, get, set_occupant
mcp__agenthub_http__call_seat          # Resolve one exact seat
mcp__agenthub_http__submit_feedback    # Report friction (room, seat, session, layer, text)
mcp__agenthub_http__manage_connection  # Health check
```

**The live registry publishes NINE tools, and this list is the nine.** `manage_agent` is not one of them:
it was retired 2026-10-10 (`76b800b9` — the tool, the `agents` table and the 32-role registry together),
and `agenthub_go/fastmcp/server/httpapp/manage_agent_absent_test.go` fails the build if it is published
again. **How the nine arise, so a reader can check rather than count:** five are carried by
`ToolDefinitions` (`agenthub_go/fastmcp/task_management/interface/ddd_compliant_mcp_tools.go:218,222,228,234,239` —
`manage_task`, `manage_subtask`, `manage_context`, `manage_project`, `manage_git_branch`), and **four more
are appended by `MCPToolsList` (`agenthub_go/fastmcp/server/httpapp/mcp_routes.go:277`)** because their
controllers own their schemas: `manage_seat` (`:303`), `call_seat` (`:312`), `submit_feedback` (`:321`) and
`manage_connection` (`:330`, built at `:326` by `connectionToolDefinition()`). `manage_context` is emitted
only when the context controller is wired, which a database-backed server does. **Measured 2026-10-14 with
the generator rather than by hand:** `cd agenthub_go && go run ./cmd/apirefgen -out /tmp/apiref.ts` ->
`156 routes, 9 tools`, and the nine names in its output are exactly the block above. `tools/list` is not
gated by any `TOOL_*` environment variable. See `ai_docs/api-integration/mcp-tools-api-complete.md` for the
per-tool arguments.

> **Superseded.** The earlier AGENTS.md section "MCP TOOL PERMISSIONS" stated that only the
> principal session has MCP access and that team agents have none, and described a "Proxy Pattern"
> that injected config into sub-agent teams. That model is retired: each seat receives its own role
> file at launch and reaches the agenthub MCP tools itself. There is no config-injection proxy.

## Knowledge management

- Project documentation: `ai_docs/` (kebab-case folders, one topic per folder).
- Index: `git ls-files 'ai_docs/**/*.md'` — the tracked tree is the index; nothing to hand-edit.
- Search existing docs before creating new ones.
