# API reference

agenthub is a cloud service that stores the state of AI work — projects, git branches, tasks,
subtasks, a four-level context hierarchy, a live registry of agents (the `manage_agent` surface),
and the **seat model** that describes who does the work and how they are configured. A separate
client (OpenRig) runs the seats on your machine; this API is where their state lives.

This page documents the HTTP API, the WebSocket endpoints and the MCP server as the running
server actually mounts them. Every path below is a real route; the whole document is generated
from the same source file the repository ships, so what you read here is what the code serves.

## Base URL and placeholders

Three values differ per deployment and are substituted when this page is rendered, so nothing
deployment-specific is written into it:

| Placeholder | Meaning |
| :--- | :--- |
| `{{API_ORIGIN}}` | The origin this deployment answers on. Every HTTP example below is relative to it. |
| `{{MCP_URL}}` | The MCP endpoint URL for this deployment (normally `<origin>/mcp`). |
| `{{VERSION}}` | The deployed version, read from `GET /health` at runtime. |

If a value cannot be obtained at render time the placeholder stays visible rather than being
replaced by a wrong literal.

```bash
export API={{API_ORIGIN}}
export MCP={{MCP_URL}}
```

## Authentication

Every route below is authenticated with a bearer token in the `Authorization` header, unless a
route is explicitly marked public:

```http
Authorization: Bearer <token>
```

Two kinds of credential are accepted:

| Credential | How it is obtained | Typical use |
| :--- | :--- | :--- |
| **Keycloak access token** | The web app's own OIDC login flow (authorization code). | The browser UI, and any client that logs a human in. |
| **API token** | Created through `POST /api/v2/tokens` (below). | Scripts, the OpenRig client, MCP clients. |

An API token carries **scopes**; the token endpoints accept an arbitrary scope list and default
to `["read"]`. A request whose token lacks the required scope is refused with `403`.

### Token lifecycle

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v2/tokens` | Create a token. `POST /api/v2/tokens/` and `POST /api/v2/tokens/generate` are the same handler. |
| `GET` | `/api/v2/tokens` | List the caller's tokens (`GET /api/v2/tokens/` and `GET /api/v2/tokens/legacy/tokens` are the same handler). |
| `GET` | `/api/v2/tokens/health` | Token-service health. |
| `GET` | `/api/v2/tokens/{token_id}` | Token details. |
| `DELETE` | `/api/v2/tokens/{token_id}` | Delete a token. |
| `PATCH` | `/api/v2/tokens/{token_id}/revoke` | Revoke a token without deleting it. |
| `PATCH` | `/api/v2/tokens/{token_id}/reactivate` | Reactivate a revoked token. |
| `POST` | `/api/v2/tokens/{token_id}/rotate` | Rotate the secret in place. |
| `POST` | `/api/v2/tokens/validate` | Validate a token and return its identity and scopes. |
| `POST` | `/api/v2/tokens/cleanup` | Delete expired tokens. |

The request and response fields for these calls are defined by the handlers under
`agenthub_go/fastmcp/server/httpapp/routes_mount.go` (mount) and `fastmcp/server/routes/`
(token logic); the shapes are not paraphrased here.

## Route reference

The server mounts **132** route registrations: 112 in the HTTP app (`fastmcp/server/httpapp`)
and 20 in the auth package (`fastmcp/auth`). They are grouped below by family; paths are the
resolved paths.

### Health

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/health` | Liveness plus the deployed version (`{{VERSION}}`). |

### Projects

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v2/projects/` | Create a project. |
| `GET` | `/api/v2/projects/` | List projects. |
| `GET` | `/api/v2/projects/{id}` | Get one project. |
| `PUT` | `/api/v2/projects/{id}` | Update a project. |
| `DELETE` | `/api/v2/projects/{id}` | Delete a project. |
| `POST` | `/api/v2/projects/{id}/health-check` | Project health metrics. |

### Branches

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v2/branches/{$}` | Create a branch (exact match on the collection path). |
| `GET` | `/api/v2/branches/{id}` | Get one branch. |
| `DELETE` | `/api/v2/branches/{id}` | Delete a branch. |
| `POST` | `/api/v2/branches/project/{project_id}/summaries` | Branch summaries for a project, with task counts. |
| `POST` | `/api/v2/branches/summaries/bulk` | Bulk branch summaries. |

### Tasks

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v2/tasks/` | Create a task. |
| `GET` | `/api/v2/tasks/` | List tasks. |
| `GET` | `/api/v2/tasks/stats/summary` | Task statistics for the caller. |
| `GET` | `/api/v2/tasks/{id}` | Get one task. |
| `PUT` | `/api/v2/tasks/{id}` | Update a task. |
| `DELETE` | `/api/v2/tasks/{id}` | Delete a task. |
| `POST` | `/api/v2/tasks/{id}/complete` | Complete a task. |

Assignees are written as `@<seat-key>` (or a known role); see the seat model below.

### Subtasks

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v2/subtasks` | Create a subtask. |
| `GET` | `/api/v2/subtasks/task/{id}` | List a task's subtasks. |
| `GET` | `/api/v2/subtasks/{id}` | Get one subtask. |
| `PUT` | `/api/v2/subtasks/{id}` | Update a subtask. |
| `DELETE` | `/api/v2/subtasks/{id}` | Delete a subtask. |
| `POST` | `/api/v2/subtasks/{id}/complete` | Complete a subtask. |

### Contexts

The context hierarchy has four levels: `global`, `project`, `branch`, `task`. `{level}` is one
of those, and `{context_id}` is the identifier appropriate to the level.

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v2/contexts/{level}` | Create a context. |
| `GET` | `/api/v2/contexts/{level}/{context_id}` | Get a context. |
| `PUT` | `/api/v2/contexts/{level}/{context_id}` | Update a context. |
| `DELETE` | `/api/v2/contexts/{level}/{context_id}` | Delete a context. |
| `GET` | `/api/v2/contexts/{level}/{context_id}/resolve` | Resolve with inherited parent data. |
| `POST` | `/api/v2/contexts/{level}/{context_id}/delegate` | Delegate data to another level. |
| `POST` | `/api/v2/contexts/{level}/{context_id}/insights` | Append an insight. |
| `POST` | `/api/v2/contexts/{level}/{context_id}/progress` | Append a progress note. |
| `GET` | `/api/v2/contexts/{level}/list` | List the caller's contexts at a level. |
| `GET` | `/api/v2/contexts/{level}/{context_id}/summary` | Summary of a context. |

### Sessions

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/v2/sessions` | List the caller's streamed sessions. |
| `GET` | `/api/v2/sessions/{id}/events` | Read a session's recorded events. |

A session belongs to one account; asking for another account's session id returns `404`, not
`403`, so ids cannot be probed.

### Seats, rooms, modules and overlays

These routes are the seat model. `{room}` is a room slug, `{seat}` a seat key, `{slug}` a module
or seat-type slug and `{version}` a concrete version.

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v2/openrig/rooms` | Create a room. |
| `GET` | `/api/v2/openrig/rooms` | List rooms. |
| `DELETE` | `/api/v2/openrig/rooms/{room}` | Delete a room. |
| `POST` | `/api/v2/openrig/rooms/{room}/seats` | Create a seat. |
| `GET` | `/api/v2/openrig/rooms/{room}/seats` | List a room's seats. |
| `DELETE` | `/api/v2/openrig/rooms/{room}/seats/{seat}` | Remove a seat (a hard delete). |
| `PUT` | `/api/v2/openrig/rooms/{room}/seats/{seat}/occupant` | Set a seat's occupant (runtime and model). |
| `PUT` | `/api/v2/openrig/rooms/{room}/seats/{seat}/permission-policy` | Set a seat's permission policy. |
| `GET` | `/api/v2/openrig/seat-types` | List seat types. |
| `POST` | `/api/v2/openrig/seat-types/{slug}/versions` | Publish a seat-type version. |
| `POST` | `/api/v2/openrig/seat-types/seed` | Seed the built-in seat types. |
| `GET` | `/api/v2/openrig/modules` | List modules. |
| `GET` | `/api/v2/openrig/modules/{slug}/versions/{version}` | Read one module version. |
| `PUT` | `/api/v2/openrig/modules/{slug}/versions/{version}` | Publish (or re-publish) a module version. |
| `PUT` | `/api/v2/openrig/overlay` | Write the company overlay. |
| `GET` | `/api/v2/openrig/overlay` | Read the company overlay. |
| `PUT` | `/api/v2/openrig/rooms/{room}/overlay` | Write a room overlay. |
| `GET` | `/api/v2/openrig/rooms/{room}/overlay` | Read a room overlay. |
| `PUT` | `/api/v2/openrig/rooms/{room}/seats/{seat}/overlay` | Write a seat overlay. |
| `GET` | `/api/v2/openrig/rooms/{room}/seats/{seat}/overlay` | Read a seat overlay. |
| `PUT` | `/api/v2/openrig/rooms/{room}/seats/{seat}/links` | Create or update a link from a seat. |
| `GET` | `/api/v2/openrig/rooms/{room}/seats/{seat}/links` | List a seat's links. |
| `DELETE` | `/api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}` | Delete one link. |
| `GET` | `/api/v2/openrig/settings` | Read the caller's settings. |
| `PUT` | `/api/v2/openrig/settings` | Write the caller's settings. |

### Seat resolution, machines and status

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/v2/openrig/seats/{room}/{seat}` | Resolve one seat and its rendered files. |
| `GET` | `/api/v2/openrig/rooms/{room}/rigspec` | Render a room as an OpenRig RigSpec document. |
| `POST` | `/api/v2/openrig/machines` | Register a machine (returns a machine token). |
| `GET` | `/api/v2/openrig/machines` | List the caller's machines and their sync state. |
| `DELETE` | `/api/v2/openrig/machines/{machine}/token` | Revoke a machine token. |
| `POST` | `/api/v2/openrig/seat-status` | Report a seat's observed status (machine-authenticated). |

### Task and performance summary routes

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/tasks/summaries` | Task summaries. |
| `GET` | `/api/tasks/{task_id}` | Full task. |
| `GET` | `/api/tasks/{task_id}/context/summary` | A task's context summary. |
| `POST` | `/api/subtasks/summaries` | Subtask summaries. |
| `POST` | `/api/v2/tasks/{task_id}/subtasks/summaries` | A task's subtask summaries for the caller. |
| `GET` | `/api/performance/metrics` | Performance metrics. |

### Connections, alerts and performance

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/v2/connections/health` | Connection health. |
| `GET` | `/api/v2/connections/status` | Connection status. |
| `GET` | `/api/v1/alerts/rules` | List alert rules. |
| `POST` | `/api/v1/alerts/rules` | Create an alert rule. |
| `PUT` | `/api/v1/alerts/rules/{rule_id}` | Update an alert rule. |
| `DELETE` | `/api/v1/alerts/rules/{rule_id}` | Delete an alert rule. |
| `GET` | `/api/v1/alerts/events` | List alert events. |
| `POST` | `/api/v1/alerts/events/{event_index}/acknowledge` | Acknowledge an event. |
| `POST` | `/api/v1/alerts/check-rules` | Evaluate the rules now. |
| `POST` | `/api/v1/alerts/test-webhook` | Send a test webhook. |
| `GET` | `/api/v1/performance/metrics/overview` | Performance overview. |
| `GET` | `/api/v1/performance/metrics/timeseries` | Performance time series. |
| `GET` | `/api/v1/performance/metrics/alerts` | Performance alerts. |
| `POST` | `/api/v1/performance/metrics/clear-cache` | Clear the performance cache. |

### Broadcast

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v2/broadcast/notify` | Broadcast a notification. |

### Authentication routes

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register. |
| `POST` | `/api/auth/login` | Log in. |
| `POST` | `/api/auth/refresh` | Refresh a session. |
| `POST` | `/api/auth/dev-login` | Development login. |
| `POST` | `/api/auth/logout` | Log out. |
| `GET` | `/api/auth/provider` | The configured identity provider. |
| `POST` | `/api/auth/registration-success` | Post-registration hook. |
| `GET` | `/api/auth/verify` | Verify a session. |
| `GET` | `/api/auth/password-requirements` | The active password rules. |
| `POST` | `/api/auth/validate-password` | Validate a candidate password. |

When the deployment is configured for Supabase as the identity provider, a second set is mounted
under `/auth/supabase/`: `POST /auth/supabase/signup`, `POST /auth/supabase/signin`,
`POST /auth/supabase/signout`, `POST /auth/supabase/password-reset`,
`POST /auth/supabase/update-password`, `GET /auth/supabase/verify-token`,
`POST /auth/supabase/resend-verification`, `GET /auth/supabase/oauth/`, `GET /auth/supabase/me`,
`GET /auth/supabase/health`.

### WebSocket endpoints

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/ws/realtime` | The client's live event stream. |
| `GET` | `/ws/connector` | The session-stream connector's socket. |
| `GET` | `/ws/sessions/{id}` | A browser viewer for one session. |

An upgrade without a valid token is refused by the application with `403 Authentication
required`; the session viewer closes an upgrade for another account's session with close code
`4004`.

### MCP registration and metrics

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/register` | Register an MCP client. |
| `POST` | `/unregister` | Unregister an MCP client. |
| `GET` | `/registrations` | List registered clients. |
| `GET` | `/ws/metrics` | WebSocket metrics. |

## The MCP surface

### Transport

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/mcp` | JSON-RPC 2.0 request/response. Named here as `{{MCP_URL}}`. |
| `GET` | `/mcp` | The SSE transport. |

A client sends a JSON-RPC 2.0 envelope to `POST /mcp`; a bare tool payload is not a request and
fails. When `AUTH_ENABLED=true` (the default), `initialize` and `tools/list` require a bearer
token just like `tools/call`.

### Protocol methods (not tools)

`initialize`, `notifications/initialized`, `ping`, `tools/list`, `resources/list`,
`prompts/list`, `tools/call`. `resources/list` and `prompts/list` return empty lists.

### Published tools

`tools/list` publishes exactly these nine tools:

| Tool | Purpose |
| :--- | :--- |
| `manage_task` | Task lifecycle. |
| `manage_subtask` | Subtasks and their progress. |
| `manage_context` | The four-level context hierarchy. |
| `manage_project` | Projects. |
| `manage_git_branch` | Git branches. |
| `manage_agent` | The agent registry. |
| `manage_seat` | Seats: `list`, `get`, `set_occupant`. |
| `call_seat` | Resolve one exact seat and its rendered context files. |
| `manage_connection` | Health check. |

`manage_context` is published whenever the server is database-backed. The list is not gated by
any `TOOL_*` environment variable. Two further names are accepted by `tools/call` but are **not**
advertised in `tools/list`: `get_mcp_status` and `check_session_health`; any other name answers
`{"error": "Unknown tool: <name>"}`.

### Calling a tool

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "manage_seat",
    "arguments": { "action": "list", "room": "my-room" }
  },
  "id": "1"
}
```

A tool answers with its own JSON object, `{"success": true, ...}` or
`{"success": false, "error": "..."}`; a tool that is not wired on this deployment answers
`{"error": "<Tool>Controller not initialized"}`. The tool argument schemas are defined in
`agenthub_go/fastmcp/task_management/interface/tool_input_schemas.go` and the seat controllers
under `fastmcp/seat_management/interface/mcp_controllers/`.

## The seat-composition model

A seat is a durable position; its occupant is the runtime and model currently in it. A seat is
composed from **modules**, versioned and inherited down a scope chain.

### Rooms and seats

A **room** groups seats (it is the pod a client launches). A seat has a key unique within its
room, a **seat type**, an occupant (runtime plus model) and a **permission policy** — one of
`locked`, `standard`, `open`, `yolo`, `none` (default `standard`). Removing a seat is a hard
delete; there is no status column.

### Seat types and versions

A **seat type** is a role template. A version of it pins a default runtime and a set of module
references. A seat either pins a concrete version or follows the latest (`follow_latest`); a
resolved seat is always pinned to a concrete version and recorded as an immutable snapshot.

### Modules and blocks

A **module** has a slug, a kind and immutable **versions**. The kinds are `instruction`,
`document`, `skill`, `tool`, `mcp` and `memory`:

- `instruction`, `document`, `skill` and `memory` are guidance content rendered into the seat.
- `tool` narrows the permissions available inside a mounted MCP server.
- `mcp` is one whole MCP server to mount for the seat. Its content is one JSON object:

```json
{
  "name": "example",
  "type": "http",
  "url": "https://mcp.example.com/mcp",
  "headers": { "Authorization": "Bearer ${EXAMPLE_TOKEN}" }
}
```

or, for a stdio server:

```json
{ "name": "filesystem", "type": "stdio", "command": "npx", "args": ["-y", "server-filesystem", "/tmp"] }
```

A block never carries a secret value: a header or environment value references an `${ENV_VAR}`
instead, and a credential-shaped literal in the content is refused with `422`. The platform's own
MCP server is referenced as `${AGENTHUB_MCP_URL}` in a block.

### Overlays

An **overlay** changes a catalog at a scope: company, room or seat. Its ordered operations are
`add`, `remove`, `override` and `pin`. Resolution folds them in order — company, then room, then
seat.

### Links

A **seat link** is a first-class edge from one seat to another with a kind and an `allow` flag;
the communication policy is enforced from these edges.

### Rendering a room

`GET /api/v2/openrig/rooms/{room}/rigspec` renders a room as an OpenRig RigSpec document, the
form a client launches. `GET /api/v2/openrig/seats/{room}/{seat}` resolves one seat and its
rendered files.

## Errors and status codes

HTTP routes answer an error as a JSON object with a single `detail` field:

```json
{ "detail": "room \"my-room\" already exists" }
```

The status codes and the situations that produce them, grounded in the handlers:

| Status | When |
| :--- | :--- |
| `400 Bad Request` | Invalid input — a missing required field, an unknown module kind (`kind "x" is not a module kind`), content outside `1`–`65536` bytes, a link to a seat itself. |
| `401 Unauthorized` | A credential was presented and rejected. |
| `403 Forbidden` | No credential, or a token that lacks the required scope. A WebSocket upgrade is refused the same way (`Authentication required`). |
| `404 Not Found` | The resource does not exist or belongs to another account. |
| `409 Conflict` | A uniqueness or immutability clash — a room or seat that already exists, or a module version re-published with different content. |
| `422 Unprocessable Entity` | A well-formed request the server refuses on content — a credential-shaped literal in a module (`secret detected in content`), a module reference that is not in the catalog, a value that cannot be parsed to its declared type. |
| `500 Internal Server Error` | An unexpected server fault. |

MCP failures use JSON-RPC error codes instead — `-32700` parse error, `-32601` method not found,
`-32602` invalid params, `-32603` internal error — or, inside a successful `tools/call`, a tool
result of `{"success": false, "error": "..."}`.

## Version and health

```bash
curl -sS "$API/health"
```

`GET /health` reports liveness and the deployed version, `{{VERSION}}`. Poll it to confirm a
deployment.
