# API reference — the written part

agenthub is a cloud service that stores the state of AI work — projects, git branches, tasks,
subtasks, a four-level context hierarchy, a live registry of agents (the `manage_agent` surface),
and the **seat model** that describes who does the work and how they are configured. A separate
client (OpenRig) runs the seats on your machine; this API is where their state lives.

**The route and tool tables on this page are GENERATED from the running code** — every path in them
is a real registration, read from the server's own registration sites at build time, so they cannot
go stale. **Everything in this file is the written part**: authentication, the MCP surface, the seat
model, the error codes. *A table is the code's statement about this server; the prose is ours, which
is why the two are kept apart.*

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

Every route is authenticated with a bearer token in the `Authorization` header, unless a route is
explicitly marked public:

```http
Authorization: Bearer <token>
```

Two kinds of credential are accepted:

| Credential | How it is obtained | Typical use |
| :--- | :--- | :--- |
| **Keycloak access token** | The web app's own OIDC login flow (authorization code). | The browser UI, and any client that logs a human in. |
| **API token** | Created through `POST /api/v2/tokens`. | Scripts, the OpenRig client, MCP clients. |

An API token carries **scopes**; the token endpoints accept an arbitrary scope list and **apply NO
DEFAULT — a token minted without scopes carries none**, so a scope-gated request is refused with
`403`. *(The absence is conservative rather than dangerous: the failure is a refusal, not a
privilege. The Python server carried `scopes: list[str] = Field(default=["read"])`, a Pydantic field
default with no equivalent in a Go struct, so it did not cross the port — which is why this went
unnoticed for as long as it did.)*

### Token lifecycle

The request and response fields for these calls are defined by the handlers under
`agenthub_go/fastmcp/server/httpapp/routes_mount.go` (mount) and `fastmcp/server/routes/`
(token logic); the shapes are not paraphrased here.

### Supabase as the identity provider

When the deployment is configured for Supabase as the identity provider, a second set of routes is
mounted under `/auth/supabase/`:

`POST /auth/supabase/signup`, `POST /auth/supabase/signin`, `POST /auth/supabase/signout`,
`POST /auth/supabase/password-reset`, `POST /auth/supabase/update-password`,
`GET /auth/supabase/verify-token`, `POST /auth/supabase/resend-verification`,
`GET /auth/supabase/oauth/`, `GET /auth/supabase/me`, `GET /auth/supabase/health`.

## Identifiers and conventions

- **Assignees** are written as `@<seat-key>` (or a known role); see the seat model below.
- **Ownership** is checked, not assumed: a session belongs to one account, and asking for another
  account's session id returns `404` rather than `403`, so ids cannot be probed.
- **Path parameters** in the generated tables: `{room}` a room slug, `{seat}` a seat key, `{slug}` a
  module or seat-type slug, `{version}` a concrete version, `{level}` one of the four context levels
  (`global`, `project`, `branch`, `task`), and `{context_id}` the identifier appropriate to that
  level.
- **`{$}`** in a generated path marks an exact match on the collection path — the pattern the mux
  registers — rather than a parameter.

## The MCP surface

### Transport

A client sends a JSON-RPC 2.0 envelope to `POST /mcp`; a bare tool payload is not a request and
fails. When `AUTH_ENABLED=true` (the default), `initialize` and `tools/list` require a bearer
token just like `tools/call`.

### Protocol methods (not tools)

`initialize`, `notifications/initialized`, `ping`, `tools/list`, `resources/list`, `prompts/list`,
`tools/call`. `resources/list` and `prompts/list` return empty lists.

### Published tools

The tool table above is generated: it lists exactly what `tools/list` publishes on this deployment,
with each tool's parameters and actions read from the server itself. Three facts about it are not
derivable from the table and are therefore stated here:

- **`manage_context` is published whenever the server is database-backed.** On a deployment without
  a database it is absent, and its absence is a fact about the deployment rather than a mismatch.
- **The list is not gated by any `TOOL_*` environment variable** — a `ToolConfig` enablement table
  exists in the code, but nothing on the `tools/list` path consults it.
- **Two further names are accepted by `tools/call` but are NOT advertised in `tools/list`**:
  `get_mcp_status` and `check_session_health`. Any other name answers
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

## WebSocket endpoints

An upgrade without a valid token is refused by the application — not by a proxy — with `403` and the
reason text *"Authentication required: pass a bearer token in the token query parameter or the
Authorization header"*; the session viewer closes an upgrade for another account's session with
close code `4004`.

## The seat-composition model

A seat is a durable position; its occupant is the runtime and model currently in it. A seat is
composed from **modules**, versioned and inherited down a scope chain.

### Rooms and seats

A **room** groups seats (it is the pod a client launches). A seat has a key unique within its room,
a **seat type**, an occupant (runtime plus model) and a **permission policy** — one of `locked`,
`standard`, `open`, `yolo`, `none` (default `standard`). Removing a seat is a hard delete; there is
no status column.

### Seat types and versions

A **seat type** is a role template. A version of it pins a default runtime and a set of module
references. A seat either pins a concrete version or follows the latest (`follow_latest`); a
resolved seat is always pinned to a concrete version and recorded as an immutable snapshot.

### Modules and blocks

A **module** has a slug, a kind and immutable **versions**. The kinds are `instruction`, `document`,
`skill`, `tool`, `mcp` and `memory`:

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

A **seat link** is a first-class edge from one seat to another with a kind and an `allow` flag; the
communication policy is enforced from these edges.

### Rendering a room

`GET /api/v2/openrig/rooms/{room}/rigspec` renders a room as an OpenRig RigSpec document, the form a
client launches. `GET /api/v2/openrig/seats/{room}/{seat}` resolves one seat and its rendered files.

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
| `403 Forbidden` | No credential, or a token that lacks the required scope. A WebSocket upgrade is refused the same way, with the reason text quoted in full above. |
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
