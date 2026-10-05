# 4genthub Go server — authoritative surface inventory

**Status:** authoritative. Every entry below is derived from the Go source at
`agenthub_go/`, not from another document. Dates/HEAD: generated at
`c4ff8d4279971ce5794b9cdc3b469d363c7b19a3`.

**Scope:** the Go service (`agenthub_go`, `cmd/agenthub`) plus the auth route sets it
mounts. `agenthub-frontend` and `agenthub_main` (Python) are out of scope and were not
touched.

**How to read the route table.** Each row's `Registration` is the exact `file:line`
where the route is registered. Paths shown are the **resolved** paths: many
registrations compose the path from a `const base = "…"` declared in the same function,
so a naive `grep HandleFunc` prints `"POST "+base+"/"` instead of `/api/v2/projects/`.
The commands used and the full registration dump are in the acceptance appendix.

**Reproduce:** `cd agenthub_go && rg -n 'mux\.HandleFunc\(' fastmcp/server/httpapp fastmcp/auth`

---

## 1. Mounted routes

**Counts:** **112** registrations in `fastmcp/server/httpapp/**` + **20** in
`fastmcp/auth/{interface,api}` = **132 total registrations**. No routes are registered
outside those packages (`grep -rn 'HandleFunc(' cmd/` → 0 matches; the process only calls
`app.Handler()` at `cmd/agenthub/main.go:52`).

Where a handler is an inline closure wrapping a `routes.*` function, the handler column
names the function that actually performs the work; the registration line is the mount.

### 1.1 Server-level and `app.go`

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/health` | `handleHealth` | `fastmcp/server/httpapp/app.go:112` |
| POST | `/api/v2/projects/` | `routes.CreateProject` | `fastmcp/server/httpapp/app.go:134` |
| GET | `/api/v2/projects/` | `routes.ListProjects` | `fastmcp/server/httpapp/app.go:147` |
| GET | `/api/v2/projects/{id}` | `routes.GetProject` | `fastmcp/server/httpapp/app.go:155` |
| PUT | `/api/v2/projects/{id}` | `routes.UpdateProject` | `fastmcp/server/httpapp/app.go:163` |
| DELETE | `/api/v2/projects/{id}` | `routes.DeleteProject` | `fastmcp/server/httpapp/app.go:184` |
| POST | `/api/v2/projects/{id}/health-check` | `routes.ProjectHealthCheck` | `fastmcp/server/httpapp/app.go:192` |

`App.Handler` (`app.go:111`) is the sole mux builder; it calls `mountRoutes`,
`mountWebSockets`, the five `mountSeat*`/`mountMachineToken` functions, `mountMiscRoutes`,
and the two auth `RegisterRoutes` methods.

### 1.2 Branches — base `/api/v2/branches` (`branch_routes.go:59`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/branches/{$}` | `routes.CreateBranch` | `branch_routes.go:61` |
| GET | `/api/v2/branches/{id}` | `routes.GetBranch` | `branch_routes.go:70` |
| DELETE | `/api/v2/branches/{id}` | `routes.DeleteBranch` | `branch_routes.go:74` |
| POST | `/api/v2/branches/project/{project_id}/summaries` | `routes.GetProjectBranchesWithTaskCounts` | `branch_routes.go:78` |
| POST | `/api/v2/branches/summaries/bulk` | `routes.GetBulkSummaries` | `branch_routes.go:82` |

### 1.3 Tasks — base `/api/v2/tasks` (`task_routes.go:48`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/tasks/` | `routes.CreateUserTask` | `task_routes.go:50` |
| GET | `/api/v2/tasks/` | `routes.ListUserTasks` | `task_routes.go:85` |
| GET | `/api/v2/tasks/stats/summary` | `routes.GetUserTaskStats` | `task_routes.go:99` |
| GET | `/api/v2/tasks/{id}` | `routes.GetUserTask` | `task_routes.go:103` |
| PUT | `/api/v2/tasks/{id}` | `routes.UpdateUserTask` | `task_routes.go:107` |
| DELETE | `/api/v2/tasks/{id}` | `routes.DeleteUserTask` | `task_routes.go:130` |
| POST | `/api/v2/tasks/{id}/complete` | `routes.CompleteUserTask` | `task_routes.go:134` |

### 1.4 Subtasks — base `/api/v2/subtasks` (`subtask_routes.go:12`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/subtasks` | `routes.CreateSubtask` | `subtask_routes.go:14` |
| GET | `/api/v2/subtasks/task/{id}` | `routes.ListSubtasks` | `subtask_routes.go:28` |
| GET | `/api/v2/subtasks/{id}` | `routes.GetSubtask` | `subtask_routes.go:32` |
| PUT | `/api/v2/subtasks/{id}` | `routes.UpdateSubtask` | `subtask_routes.go:36` |
| DELETE | `/api/v2/subtasks/{id}` | `routes.DeleteSubtask` | `subtask_routes.go:49` |
| POST | `/api/v2/subtasks/{id}/complete` | `routes.CompleteSubtask` | `subtask_routes.go:53` |

### 1.5 Sessions — base `/api/v2/sessions` (`session_stream_routes.go:12`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v2/sessions` | `routes.ListSessions` | `session_stream_routes.go:14` |
| GET | `/api/v2/sessions/{id}/events` | `routes.GetSessionEvents` | `session_stream_routes.go:19` |

### 1.6 MCP transport (`mcp_routes.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/mcp` | JSON-RPC dispatcher (`handleJSONRPC`) | `mcp_routes.go:55` |
| GET | `/mcp` | `mcpSSEHandler` (SSE) | `mcp_routes.go:116` |

### 1.7 WebSockets (`ws_mount.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/ws/realtime` | `handleRealtime` | `ws_mount.go:61` |
| GET | `/ws/connector` | `handleConnector` | `ws_mount.go:62` |
| GET | `/ws/sessions/{id}` | `handleSessionViewer` | `ws_mount.go:63` |

### 1.8 MCP registration / metrics (`misc_mount.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/register` | `mcpRegistrationStore.register` | `misc_mount.go:62` |
| POST | `/unregister` | `mcpRegistrationStore.unregisterResponse` | `misc_mount.go:66` |
| GET | `/registrations` | `mcpRegistrationStore.listResponse` | `misc_mount.go:69` |
| GET | `/ws/metrics` | `handleWebSocketMetrics` | `misc_mount.go:72` |

### 1.9 Connections — base `/api/v2/connections` (`routes_mount.go:84`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v2/connections/health` | `routes.HealthCheck` | `routes_mount.go:85` |
| GET | `/api/v2/connections/status` | `routes.ConnectionStatus` | `routes_mount.go:88` |

### 1.10 Alerts — base `/api/v1/alerts` (`routes_mount.go:97`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v1/alerts/rules` | `routes.ListAlertRules` | `routes_mount.go:99` |
| POST | `/api/v1/alerts/rules` | `routes.CreateAlertRule` | `routes_mount.go:102` |
| PUT | `/api/v1/alerts/rules/{rule_id}` | `routes.UpdateAlertRule` | `routes_mount.go:110` |
| DELETE | `/api/v1/alerts/rules/{rule_id}` | `routes.DeleteAlertRule` | `routes_mount.go:118` |
| GET | `/api/v1/alerts/events` | `routes.ListAlertEvents` | `routes_mount.go:122` |
| POST | `/api/v1/alerts/events/{event_index}/acknowledge` | `routes.AcknowledgeAlert` | `routes_mount.go:125` |
| POST | `/api/v1/alerts/check-rules` | `routes.CheckAlertRules` | `routes_mount.go:134` |
| POST | `/api/v1/alerts/test-webhook` | `routes.TestWebhook` | `routes_mount.go:137` |

### 1.11 Performance — base `/api/v1/performance` (`routes_mount.go:150`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v1/performance/metrics/overview` | `routes.GetPerformanceOverview` | `routes_mount.go:151` |
| GET | `/api/v1/performance/metrics/timeseries` | `routes.GetPerformanceTimeseries` | `routes_mount.go:155` |
| GET | `/api/v1/performance/metrics/alerts` | `routes.GetPerformanceAlerts` | `routes_mount.go:159` |
| POST | `/api/v1/performance/metrics/clear-cache` | `routes.ClearPerformanceCache` | `routes_mount.go:163` |

### 1.12 Broadcast

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/broadcast/notify` | `routes.TriggerBroadcast` | `routes_mount.go:172` |

### 1.13 Contexts — base `/api/v2/contexts` (`routes_mount.go:211`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/contexts/{level}` | `routes.CreateContext` | `routes_mount.go:213` |
| GET | `/api/v2/contexts/{level}/{context_id}` | `routes.GetContext` | `routes_mount.go:231` |
| PUT | `/api/v2/contexts/{level}/{context_id}` | `routes.UpdateContext` | `routes_mount.go:236` |
| DELETE | `/api/v2/contexts/{level}/{context_id}` | `routes.DeleteContext` | `routes_mount.go:249` |
| GET | `/api/v2/contexts/{level}/{context_id}/resolve` | `routes.ResolveContext` | `routes_mount.go:253` |
| POST | `/api/v2/contexts/{level}/{context_id}/delegate` | `routes.DelegateContext` | `routes_mount.go:257` |
| POST | `/api/v2/contexts/{level}/{context_id}/insights` | `routes.AddInsight` | `routes_mount.go:270` |
| POST | `/api/v2/contexts/{level}/{context_id}/progress` | `routes.AddProgress` | `routes_mount.go:284` |
| GET | `/api/v2/contexts/{level}/list` | `routes.ListContexts` | `routes_mount.go:293` |
| GET | `/api/v2/contexts/{level}/{context_id}/summary` | `routes.GetContextSummary` | `routes_mount.go:297` |

### 1.14 Tokens — base `/api/v2/tokens` (`routes_mount.go:310`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/tokens` | `routes.GenerateTokenHandler` | `routes_mount.go:320` |
| POST | `/api/v2/tokens/` | `routes.GenerateTokenHandler` | `routes_mount.go:321` |
| POST | `/api/v2/tokens/generate` | `routes.GenerateTokenHandler` | `routes_mount.go:322` |
| GET | `/api/v2/tokens` | `routes.ListTokens` | `routes_mount.go:328` |
| GET | `/api/v2/tokens/` | `routes.ListTokens` | `routes_mount.go:329` |
| GET | `/api/v2/tokens/legacy/tokens` | `routes.ListTokens` | `routes_mount.go:330` |
| GET | `/api/v2/tokens/health` | `routes.TokenServiceHealth` | `routes_mount.go:331` |
| GET | `/api/v2/tokens/{token_id}` | `routes.GetTokenDetails` | `routes_mount.go:335` |
| DELETE | `/api/v2/tokens/{token_id}` | `routes.DeleteToken` | `routes_mount.go:339` |
| PATCH | `/api/v2/tokens/{token_id}/revoke` | `routes.RevokeToken` | `routes_mount.go:343` |
| PATCH | `/api/v2/tokens/{token_id}/reactivate` | `routes.ReactivateToken` | `routes_mount.go:347` |
| POST | `/api/v2/tokens/{token_id}/rotate` | `routes.RotateToken` | `routes_mount.go:351` |
| POST | `/api/v2/tokens/validate` | `routes.ValidateTokenEndpoint` | `routes_mount.go:355` |
| POST | `/api/v2/tokens/cleanup` | `routes.CleanupExpiredTokens` | `routes_mount.go:363` |

### 1.15 Summary / remaining task routes (`routes_mount.go:389`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/tasks/summaries` | `routes.GetTaskSummaries` | `routes_mount.go:391` |
| GET | `/api/tasks/{task_id}` | `routes.GetFullTask` | `routes_mount.go:406` |
| GET | `/api/tasks/{task_id}/context/summary` | `routes.GetTaskContextSummary` | `routes_mount.go:410` |
| POST | `/api/subtasks/summaries` | `routes.GetTaskRouteSubtaskSummaries` | `routes_mount.go:416` |
| GET | `/api/performance/metrics` | `routes.GetPerformanceMetrics` | `routes_mount.go:425` |
| POST | `/api/v2/tasks/{task_id}/subtasks/summaries` | `routes.GetUserSubtaskSummaries` | `routes_mount.go:428` |

### 1.16 OpenRig seat management — admin (`seat_admin_mount.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/openrig/rooms` | `handleCreateRoom` | `seat_admin_mount.go:273` |
| GET | `/api/v2/openrig/rooms` | `handleListRooms` | `seat_admin_mount.go:276` |
| DELETE | `/api/v2/openrig/rooms/{room}` | `handleDeleteRoom` | `seat_admin_mount.go:279` |
| GET | `/api/v2/openrig/seat-types` | `handleListSeatTypes` | `seat_admin_mount.go:282` |
| POST | `/api/v2/openrig/seat-types/{slug}/versions` | `handleCreateSeatTypeVersion` | `seat_admin_mount.go:285` |
| GET | `/api/v2/openrig/modules` | `handleListModules` | `seat_admin_mount.go:288` |
| GET | `/api/v2/openrig/modules/{slug}/versions/{version}` | `handleGetModuleVersion` | `seat_admin_mount.go:291` |
| PUT | `/api/v2/openrig/modules/{slug}/versions/{version}` | `handlePutModuleVersion` | `seat_admin_mount.go:294` |
| POST | `/api/v2/openrig/rooms/{room}/seats` | `handleCreateSeat` | `seat_admin_mount.go:297` |
| GET | `/api/v2/openrig/rooms/{room}/seats` | `handleListSeats` | `seat_admin_mount.go:300` |
| DELETE | `/api/v2/openrig/rooms/{room}/seats/{seat}` | `handleRemoveSeat` | `seat_admin_mount.go:303` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/occupant` | `handleSetSeatOccupant` | `seat_admin_mount.go:306` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/permission-policy` | `handleSetSeatPermissionPolicy` | `seat_admin_mount.go:309` |
| PUT | `/api/v2/openrig/rooms/{room}/overlay` | `handleRoomOverlay` | `seat_admin_mount.go:312` |
| GET | `/api/v2/openrig/overlay` | `handleGetCompanyOverlay` | `seat_admin_mount.go:315` |
| PUT | `/api/v2/openrig/overlay` | `handleCompanyOverlay` | `seat_admin_mount.go:318` |
| GET | `/api/v2/openrig/rooms/{room}/overlay` | `handleGetRoomOverlay` | `seat_admin_mount.go:321` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/overlay` | `handleSeatOverlay` | `seat_admin_mount.go:324` |
| GET | `/api/v2/openrig/rooms/{room}/seats/{seat}/overlay` | `handleGetSeatOverlay` | `seat_admin_mount.go:327` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/links` | `handleUpsertSeatLink` | `seat_admin_mount.go:330` |
| GET | `/api/v2/openrig/rooms/{room}/seats/{seat}/links` | `handleListSeatLinks` | `seat_admin_mount.go:333` |
| DELETE | `/api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}` | `handleDeleteSeatLink` | `seat_admin_mount.go:336` |
| GET | `/api/v2/openrig/settings` | `handleGetSettings` | `seat_admin_mount.go:339` |
| PUT | `/api/v2/openrig/settings` | `handlePutSettings` | `seat_admin_mount.go:342` |

Note: the mutating rows are wrapped in `seatMutation(kind, action, fn)` (a broadcast +
audit wrapper), except `handleCreateRoom`/`handleListRooms` and the GETs.

### 1.17 OpenRig seat management — seat resolution / machine / status / rigspec

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v2/openrig/seats/{room}/{seat}` | `handleResolveSeat` | `seat_mount.go:98` |
| POST | `/api/v2/openrig/seat-types/seed` | `handleSeedSeatTypes` | `seat_mount.go:101` |
| GET | `/api/v2/openrig/rooms/{room}/rigspec` | `handleRoomRigSpec` | `seat_rigspec_mount.go:107` |
| POST | `/api/v2/openrig/machines` | `handleRegisterMachine` | `machine_token_mount.go:35` |
| DELETE | `/api/v2/openrig/machines/{machine}/token` | `handleRevokeMachineToken` | `machine_token_mount.go:38` |
| POST | `/api/v2/openrig/seat-status` | `handlePostSeatStatus` (`machineAuthed`) | `seat_status_mount.go:91` |
| GET | `/api/v2/openrig/machines` | `handleListMachines` | `seat_status_mount.go:94` |

### 1.18 Auth — `/api/auth/*` (`fastmcp/auth/interface/auth_endpoints.go:1087`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/auth/register` | `AuthController.Register` | `auth_endpoints.go:1103` |
| POST | `/api/auth/login` | `AuthController.Login` | `auth_endpoints.go:1117` |
| POST | `/api/auth/refresh` | `AuthController.RefreshToken` | `auth_endpoints.go:1131` |
| POST | `/api/auth/dev-login` | `AuthController.DevLogin` | `auth_endpoints.go:1145` |
| POST | `/api/auth/logout` | `AuthController.Logout` | `auth_endpoints.go:1154` |
| GET | `/api/auth/provider` | `AuthController.GetProviderConfig` | `auth_endpoints.go:1165` |
| POST | `/api/auth/registration-success` | `AuthController.HandleRegistrationSuccess` | `auth_endpoints.go:1169` |
| GET | `/api/auth/verify` | inline (provider echo) | `auth_endpoints.go:1175` |
| GET | `/api/auth/password-requirements` | inline | `auth_endpoints.go:1180` |
| POST | `/api/auth/validate-password` | `ValidatePasswordRequirements` | `auth_endpoints.go:1199` |

### 1.19 Auth — Supabase (`fastmcp/auth/api/supabase_endpoints.go:333`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/auth/supabase/signup` | `SupabaseAuthController.SignUp` | `supabase_endpoints.go:349` |
| POST | `/auth/supabase/signin` | `SupabaseAuthController.SignIn` | `supabase_endpoints.go:363` |
| POST | `/auth/supabase/signout` | `SupabaseAuthController.SignOut` | `supabase_endpoints.go:377` |
| POST | `/auth/supabase/password-reset` | `SupabaseAuthController.PasswordReset` | `supabase_endpoints.go:391` |
| POST | `/auth/supabase/update-password` | `SupabaseAuthController.UpdatePassword` | `supabase_endpoints.go:405` |
| GET | `/auth/supabase/verify-token` | `SupabaseAuthController.VerifyToken` | `supabase_endpoints.go:424` |
| POST | `/auth/supabase/resend-verification` | `SupabaseAuthController.ResendVerification` | `supabase_endpoints.go:438` |
| GET | `/auth/supabase/oauth/` | `SupabaseAuthController.GetOAuthURL` | `supabase_endpoints.go:452` |
| GET | `/auth/supabase/me` | `SupabaseAuthController.VerifyToken` | `supabase_endpoints.go:463` |
| GET | `/auth/supabase/health` | `SupabaseAuthController.HealthCheck` | `supabase_endpoints.go:477` |

---

## 2. MCP tool surface

### 2.1 How this was established

The server binary and a throwaway Postgres could not be started on this host (no
`postgres`/`pg_ctl`/`initdb`/`psql` binaries: `which postgres pg_ctl initdb psql` →
empty). The live registry was therefore taken from **the code that builds the list**, and
corroborated with the repository's own registry test, which drives the real registered
`POST /mcp` handler through `httptest`:

```
cd agenthub_go
GOCACHE=$PWD/.gocache/rig-surface TMPDIR=$PWD/.gotmp \
  go test ./fastmcp/server/httpapp/ \
  -run 'TestMCPToolsListMatchesGolden|TestMCPToolsListPublishesManageSeat|TestMCPToolsListPublishesCallSeat|TestConnectionToolDefinition' -v
```

Raw output:

```
=== RUN   TestMCPToolsListPublishesCallSeat
--- PASS: TestMCPToolsListPublishesCallSeat (0.00s)
=== RUN   TestMCPToolsListPublishesManageSeat
--- PASS: TestMCPToolsListPublishesManageSeat (0.00s)
=== RUN   TestConnectionToolDefinition
--- PASS: TestConnectionToolDefinition (0.00s)
=== RUN   TestMCPToolsListMatchesGolden
--- PASS: TestMCPToolsListMatchesGolden (0.00s)
PASS
ok  	agenthub/fastmcp/server/httpapp	0.014s
```

The `tools/list` result is built by `App.getMCPToolsList`
(`fastmcp/server/httpapp/mcp_routes.go:236`), which does exactly two things:

1. iterates `DDDCompliantMCPTools.ToolDefinitions()`
   (`fastmcp/task_management/interface/ddd_compliant_mcp_tools.go:218`), and
2. appends three schemas `ToolDefinitions` does not carry (`mcp_routes.go:249-274`).

There is no other filter or source.

### 2.2 MCP protocol methods (NOT tools)

`handleJSONRPC` (`fastmcp/server/httpapp/mcp_routes.go:150`) implements these JSON-RPC
methods. They are the protocol layer and MUST NOT be listed as tools:

`initialize`, `notifications/initialized`, `ping`, `tools/list`, `resources/list`,
`prompts/list`, `tools/call` (all in `handleJSONRPC`, `mcp_routes.go:150-220`).

`initialize` and `tools/list` additionally require a bearer token when
`AUTH_ENABLED=true` (default), enforced in `authorizeMCPMethod` (`mcp_routes.go:126`).
`resources/list` and `prompts/list` return empty lists.

### 2.3 Published tools (`tools/list`)

Nine tool names, always present except `manage_context` (see note):

| Tool | Source | File:line |
|---|---|---|
| `manage_task` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:220` |
| `manage_subtask` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:224` |
| `manage_context` | `ToolDefinitions` (conditional) | `ddd_compliant_mcp_tools.go:230` |
| `manage_project` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:236` |
| `manage_git_branch` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:241` |
| `manage_agent` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:246` |
| `manage_seat` | appended schema | `mcp_routes.go:257` (`ManageSeatToolName`, `manage_seat_controller.go:12`) |
| `call_seat` | appended schema | `mcp_routes.go:266` (`CallSeatToolName`, `call_seat_controller.go:14`) |
| `manage_connection` | appended schema | `mcp_routes.go:274` (`connectionToolDefinition`, `mcp_connection_tool.go:39`) |

Note: `manage_context` is emitted only when `ContextController != nil`; the constructor
sets it when `DatabaseAvailable` is true (`ddd_compliant_mcp_tools.go:107-111`), and
`app.go:66` passes `DatabaseAvailable: true`. So on a wired server all nine are present.

`tools_golden.json`
(`fastmcp/task_management/interface/testdata/tools_golden.json`) contains only the six
Python-registry tools; `TestMCPToolsListMatchesGolden` asserts the wire list equals golden
plus the three appended names.

### 2.4 Dispatch-only names (callable via `tools/call`, NOT advertised by `tools/list`)

`dispatchMCPTool` (`mcp_routes.go:303`) also handles two legacy names that are **not**
published in `tools/list`:

- `get_mcp_status` (`mcp_routes.go:326`)
- `check_session_health` (`mcp_routes.go:333`)

Anything else returns `{"error":"Unknown tool: <name>"}` (`mcp_routes.go:435`, `default`).

### 2.5 Configuration gating — important negative finding

The Python-derived `ToolConfig` subsystem still exists in Go
(`fastmcp/task_management/infrastructure/configuration/tool_config.go:22`) with a
`TOOL_*` enablement table (`manage_project`, `manage_task`, `manage_subtask`,
`manage_agent`, `manage_seat`, `manage_document`, `update_auto_rule`, `validate_rules`,
`regenerate_auto_rule`, `validate_tasks_json`, `create_context_file`, `manage_context`).

**In this Go server that table does not gate `tools/list`.** Evidence:
`DDDCompliantMCPTools` constructs a `ToolConfig` and passes it to controllers
(`ddd_compliant_mcp_tools.go:62`), but the only method any caller invokes on it is
`IsWorkflowGuidanceEnabled()` (`git_branch_mcp_controller.go:176`,
`subtask_mcp_controller.go:336`, `agent_mcp_controller.go:249`). `GetEnabledTools` has no
caller outside `fastmcp/config` (its `ToolRegistry`/`ToolConfigLoader` are unused by the
HTTP path). `ToolDefinitions()` and `getMCPToolsList` read no environment variable.
Therefore `TOOL_*` and the six phantom names (`manage_document`, `update_auto_rule`,
`validate_rules`, `regenerate_auto_rule`, `validate_tasks_json`, `create_context_file`)
have no effect and are never advertised.

A cross-check inventory produced by the reviewer at the same HEAD stated the tool list is
`TOOL_*`-gated. That claim is **not supported by the Go source**; this document records the
code as authoritative and flags the discrepancy in §5.

---

## 3. Tables

The runtime table registry is `database.Tables` (base package,
`fastmcp/task_management/infrastructure/database/models.go:589`). Two packages append to
it in `init()`; `ProductionTables` is deliberately separate.

### 3.1 Core task-side — `Tables` in `models.go` (20)

| Table | Model | Declaration |
|---|---|---|
| `agent_sessions` | `AgentSession` | `models.go:590` |
| `agents` | `Agent` | `models.go:605` |
| `api_tokens` | `APIToken` | `models.go:623` |
| `context_delegations` | `ContextDelegation` | `models.go:640` |
| `context_inheritance_cache` | `ContextInheritanceCache` | `models.go:669` |
| `global_contexts` | `GlobalContext` | `models.go:693` |
| `labels` | `Label` | `models.go:712` |
| `missed_notifications` | `MissedNotification` | `models.go:723` |
| `projects` | `Project` | `models.go:738` |
| `templates` | `Template` | `models.go:750` |
| `agent_session_events` | `AgentSessionEvent` | `models.go:771` |
| `project_contexts` | `ProjectContext` | `models.go:783` |
| `project_git_branchs` | `ProjectGitBranch` | `models.go:805` |
| `branch_contexts` | `BranchContext` | `models.go:823` |
| `tasks` | `Task` | `models.go:844` |
| `subtasks` | `Subtask` | `models.go:880` |
| `task_assignees` | `TaskAssignee` | `models.go:914` |
| `task_contexts` | `TaskContext` | `models.go:927` |
| `task_dependencies` | `TaskDependency` | `models.go:952` |
| `task_labels` | `TaskLabel` | `models.go:962` |

### 3.2 Auth tables — appended to `Tables` via `init()`

| Table | Model | Declaration | Registered by |
|---|---|---|---|
| `users` | `User` | `fastmcp/auth/infrastructure/database/models_auth.go:58` | `models_auth.go:155` |
| `user_token_balances` | `UserTokenBalance` | `models_auth.go:120` | `models_auth.go:155` |
| `email_tokens` | `EmailTokenModel` | `fastmcp/auth/infrastructure/repositories/email_token_repository.go:53` | `email_token_repository.go:86` |

### 3.3 Seat-management tables — appended to `Tables` via `init()`

Declared in `fastmcp/seat_management/infrastructure/database/seat_tables.go`
(`seatManagementDatabaseTables`); appended at `seat_tables.go:309`. The same 13 tables are
declared as DDL in
`fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql`.

| Table | Model | Declaration (Go) | SQL |
|---|---|---|---|
| `modules` | `ModuleORM` | `seat_tables.go:14` | `seat_management_postgresql.sql:32` |
| `module_versions` | `ModuleVersionORM` | `seat_tables.go:33` | `:47` |
| `seat_types` | `SeatTypeORM` | `seat_tables.go:56` | `:63` |
| `seat_type_versions` | `SeatTypeVersionORM` | `seat_tables.go:76` | `:79` |
| `rooms` | `RoomORM` | `seat_tables.go:99` | `:96` |
| `seats` | `SeatORM` | `seat_tables.go:119` | `:112` |
| `overlays` | `OverlayORM` | `seat_tables.go:152` | `:135` |
| `seat_links` | `SeatLinkORM` | `seat_tables.go:184` | `:160` |
| `resolved_seats` | `ResolvedSeatORM` | `seat_tables.go:210` | `:180` |
| `seat_settings` | `SeatSettingsORM` | `seat_tables.go:235` | `:198` |
| `machines` | `MachineORM` | `seat_tables.go:247` | `:207` |
| `machine_tokens` | `MachineTokenORM` | `seat_tables.go:261` | `:219` |
| `seat_status` | `SeatStatusORM` | `seat_tables.go:281` | `:234` |

### 3.4 `ProductionTables` — declared but NOT appended to `Tables` (6)

`fastmcp/task_management/infrastructure/database/models_prod.go:96`. The file's header
(`models_prod.go:8-12`) states these are intentionally not appended (they reference the
auth `users` table and would mis-order DDL). They are therefore **not** created by
`CreateTables`.

| Table | Model | Declaration |
|---|---|---|
| `agent_import_history` | `AgentImportHistory` | `models_prod.go:97` |
| `applied_migrations` | `AppliedMigration` | `models_prod.go:118` |
| `token_transactions` | `TokenTransaction` | `models_prod.go:135` |
| `user_agent_configurations_md` | `UserAgentConfigurationMd` | `models_prod.go:162` |
| `user_api_tokens` | `UserAPIToken` | `models_prod.go:182` |
| `user_sessions` | `UserSession` | `models_prod.go:217` |

### 3.5 Totals

- `database.Tables` at runtime: 20 (core) + 3 (auth) + 13 (seat) = **36 tables**.
- Plus `ProductionTables`: **6** tables declared but not registered for creation.
- Every table in §3.1–3.4 carries a `user_id` column except `applied_migrations`
  (a migration ledger; `models_prod.go:118`).

---

## 4. Gone list

Each entry states the exact command and its result. "NO MATCH" = the command exited with
no output.

| Retired item | How established it is gone | Command | Result |
|---|---|---|---|
| `agenthub_main/agent-library` (Python agent library) | directory absent on disk and untracked in git; removed by commit `60bcdb68` | `ls agenthub_main/agent-library` ; `git ls-files 'agenthub_main/agent-library*' \| wc -l` ; `git log --oneline -1 -S'agent-library' -- agenthub_main` | `No such file or directory` ; `0` ; `60bcdb68 refactor(agents): remove the Python agent library and agent management (T8 Python half)` |
| `call_agent` **tool** (MCP tool "load agent instructions") | no tool definition, absent from `tools_golden.json`, and the test suite asserts its absence | `grep -rn 'Name: *"call_agent"' agenthub_go --include='*.go' \| grep -v .gomodcache` ; `grep -n 'removed call_agent tool' agenthub_go --include='*_test.go'` | `NO MATCH` ; `call_seat_mcp_test.go:62: t.Fatal("tools/list still publishes the removed call_agent tool")` |
| `/api/v2/openrig/agents` route | no registration anywhere in the Go tree | `grep -rn 'openrig/agents' agenthub_go --include='*.go' \| grep -v .gomodcache` | `NO MATCH` |
| `agent_templates` table | no declaration in Go models/DDL or in the production SQL | `grep -rn 'agent_templates' agenthub_go --include='*.go' --include='*.sql'` ; `grep -rn 'agent_templates' agenthub_main --include='*.sql'` | `NO MATCH` (both) |
| `user_agent_instances` table | same as above | `grep -rn 'user_agent_instances' agenthub_go --include='*.go' --include='*.sql'` ; `grep -rn 'user_agent_instances' agenthub_main --include='*.sql'` | `NO MATCH` (both) |

**Distinction that must not be collapsed:** `call_agent` the **tool** is gone, but
`call_agent` remains a **parameter/field of the `manage_agent` tool** (register/update):
`ddd_compliant_mcp_tools.go:249`, `agent_mcp_controller/unified_agent_description.go:101`,
`tool_input_schemas.go:126`. That field is deliberate and still live. A sentence about one
must not be read as a sentence about the other.

---

## 5. Contradictions between existing docs and the code

These are the rewrite worklist. Every claim below is checked against the source in this
document.

1. **`ai_docs/api-integration/mcp-tools-api-complete.md`** — wrong tool inventory:
   - line 13 and §"call_agent" (lines 385-407) document the **`call_agent` tool** as live.
     There is no such tool (`Name: "call_agent"` → NO MATCH); the tool was removed
     (`b0d441bd refactor(mcp): remove the Go call_agent tool, its routes and wiring`).
   - line 14 documents `manage_connection`; the doc lists 8 tools and omits `manage_seat`
     and `call_seat`, which the live registry publishes (§2.3).
   - line 16's "all tools require `action`" is false for `call_seat`/`manage_connection`.

2. **`ai_docs/api-behavior/api-parameter-handling-complete.md`** — describes parameter
   coercion across "All controllers" and example calls to `manage_context`; it is not a
   surface list, but it shares the tool set above and predates the seat tools.

3. **`ai_docs/architecture-design/Architecture_Technique.md`** — architectural claims
   that contradict the Go server:
   - line 33: "32+ specialized agents"; line 49: "PostgreSQL (local), **SQLite
     (fallback)**"; line 256/317/755/793: **SQLAlchemy** ORM models and Alembic
     migrations. The Go server is Postgres-only with generated `TableDef` metadata
     (`models.go`) and no SQLite or SQLAlchemy code path.
   - Its API/MCP/DB sections describe the Python implementation this Go service replaced.

4. **`agenthub_go/PROD_READINESS_REPORT.md`** (repo root of the Go module, not `ai_docs`)
   — item B4 states the MCP wiring "is not the real one", `tools/list` returns stub
   schemas, and `GET /mcp` is not SSE. At this HEAD the opposite is true:
   `getMCPToolsList` builds from `ToolDefinitions()` (`mcp_routes.go:236`), the golden
   registry test passes, and `GET /mcp` is `mcpSSEHandler` (`mcp_routes.go:116`). B6's
   "eight production tables unknown to the Go models" is also stale: `models_prod.go`
   now declares six of them.

5. **Cross-check `/tmp/inv.md`** (reviewer inventory, same HEAD `c4ff8d42`) — three
   divergences from the code:
   - It says the live tool list is `TOOL_*`-gated. The Go `tools/list` path never reads
     `TOOL_*`; the config table is constructed but only `IsWorkflowGuidanceEnabled` is
     consumed (§2.5).
   - It lists `initialize` and `ping` among dispatch cases. They are `handleJSONRPC`
     protocol methods, not dispatch cases and not tools (§2.2).
   - Its route count is 112 (httpapp only) and it prints base paths without the
     trailing segment (e.g. all five `/api/v2/branches` rows). The source has 112
     httpapp registrations **plus 20 auth registrations = 132**; resolved full paths are
     in §1.
   - Its table sections omit the three auth tables and the six `ProductionTables`.

---

## Appendix A — acceptance commands

Run from `/home/daihu/__projects__/4genthub/agenthub_go` unless noted.

```bash
# Every route registration (the source of §1)
grep -rn 'mux.HandleFunc(\|mux.Handle(' --include='*.go' fastmcp/server/httpapp | grep -v '_test.go'
grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/auth | grep -v '_test.go'
# Counts: 112 httpapp + 20 auth = 132
grep -rn 'mux.HandleFunc(\|mux.Handle(' --include='*.go' fastmcp/server/httpapp | grep -v '_test.go' | wc -l
grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/auth | grep -v '_test.go' | wc -l

# No other mount sites exist
grep -rn 'HandleFunc(' --include='*.go' cmd | grep -v '_test.go' | wc -l   # 0

# MCP registry (see raw output in §2.1)
GOCACHE=$PWD/.gocache/rig-surface TMPDIR=$PWD/.gotmp \
  go test ./fastmcp/server/httpapp/ \
  -run 'TestMCPToolsListMatchesGolden|TestMCPToolsListPublishesManageSeat|TestMCPToolsListPublishesCallSeat|TestConnectionToolDefinition' -v

# Base-path constants resolved in §1
grep -rn 'const base' --include='*.go' fastmcp/server/httpapp | grep -v '_test.go'

# Tables
grep -n '^\t{Name: "' fastmcp/task_management/infrastructure/database/models.go
grep -n '^\t{Name: "' fastmcp/task_management/infrastructure/database/models_prod.go
grep -n '^\t{Name: "' fastmcp/seat_management/infrastructure/database/seat_tables.go
grep -n '^\t{Name: "' fastmcp/auth/infrastructure/database/models_auth.go
grep -n '^\t{Name: "' fastmcp/auth/infrastructure/repositories/email_token_repository.go

# Gone list (see §4)
grep -rn 'openrig/agents' agenthub_go --include='*.go' | grep -v .gomodcache          # NO MATCH
grep -rn 'Name: *"call_agent"' agenthub_go --include='*.go' | grep -v .gomodcache     # NO MATCH
grep -rn 'agent_templates\|user_agent_instances' agenthub_go --include='*.go' --include='*.sql'  # NO MATCH
ls agenthub_main/agent-library                                                        # No such file or directory
```
