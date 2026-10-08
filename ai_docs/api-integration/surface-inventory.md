# 4genthub Go server — authoritative surface inventory

**Status:** authoritative. Every entry below is derived from the Go source at
`agenthub_go/`, not from another document. Dates/HEAD: generated at
`c4ff8d4279971ce5794b9cdc3b469d363c7b19a3`.

**Update 2026-10-05 (NEXT_GEN D5, teams/sharing).** §1.20 and the two team rows of §3.3
were added and every count updated: registrations 132 -> **140**, runtime `Tables` 36 ->
**38**. This delta was generated on top of `b0a1f510`; the rest of the file is unchanged
from the `c4ff8d42` snapshot. **The registration figure is now 141** — the seat-type create
route (`POST /api/v2/openrig/seat-types`) was added after that snapshot; §1 carries the
current count with its pattern and date.

**Scope:** the Go service (`agenthub_go`, `cmd/agenthub`) plus the auth route sets it
mounts. `agenthub-frontend` and `agenthub_main` (Python) are out of scope and were not
touched.

**How to read the route table.** Each row's `Registration` is the exact `file:line`
where the route is registered. Paths shown are the **resolved** paths: many
registrations compose the path from a `const base = "…"` declared in the same function,
so a naive `grep HandleFunc` prints `"POST "+base+"/"` instead of `/api/v2/projects/`.
**Resolve them with the generator rather than by hand:** `cd agenthub_go && go run ./cmd/apirefgen` follows each `RegisterRoutes` call into the package that owns it and prints `<n> routes, <n> tools`; pass `-out /tmp/apiref.ts` to read the resolved list without writing the frontend artefact. At `db9d2bc3` it emitted **143 routes, 10 tools**, independently matching this section's count and resolving the function-scoped bases above (e.g. `/api/v2/tasks/{id}/events`). Writing a regex for this is how a reader reinvents the bug this paragraph describes — three such attempts on 2026-10-08 produced junk path keys while reporting plausible counts.
The commands used and the full registration dump are in the acceptance appendix.

**Reproduce:** `cd agenthub_go && grep -rn "mux\.HandleFunc(" --include='*.go' --exclude='*_test.go' fastmcp/server/httpapp fastmcp/auth | wc -l` -> **143** (httpapp 123, auth 20), re-run at `db9d2bc3`; the same command returned **145** (httpapp 125) before `e6829b32` removed the two always-500 task routes. *`rg` is NOT installed in this environment, so the earlier `rg -n` form could not run here, and it also counted `*_test.go` registrations — 125 at `db9d2bc3` rather than the figure's 123; the tests-inclusive count for `httpapp` is now the number the no-tests figure used to be, which is how this line rots silently if it is quoted without its date.* The command above is the one that produced the number.*

---

## 1. Mounted routes

**Counts (DATED — carry the date and the pattern, per the counting rule).** **RE-MEASURED 2026-10-08 by go-dev, after the owner ruled both always-500 task routes removed: the `httpapp` figure falls `125 -> 123`, exactly the two removed registrations (`GET /api/v2/tasks/stats/summary` in `task_routes.go` and `GET /api/tasks/{task_id}` in `routes_mount.go`), under the same pattern and scope stated below. The auth half is unchanged at 20, so the total falls `145 -> 143`. The two rows are struck from the tables in this file, and the task-route line references below are renumbered by the same four-line deletion.** **CORRECTED 2026-10-06 (docs duty pass 3): the figure this paragraph has carried since it was written was TWO SHORT. The same pattern returns **125** registrations in `httpapp` + **20** in `fastmcp/auth/{interface,api}` = **145 total.** **RE-MEASURED 2026-10-08 at HEAD `88d27758`, with the control that makes it a drift figure rather than a preference:** **the identical pattern run at `6dc06203` returns 124 — the previous figure, REPRODUCED — and HEAD returns 125: exactly ONE registration was added, and it is named here.** *The addition is `GET /api/v2/tasks/{id}/events` (`task_routes.go:107`), the task-event ledger's read route, which is the `O1a` board row and the only `mux.HandleFunc(` line the two commits differ by `+1` on.* The auth half is unchanged at 20. **Pattern and scope, stated because the previous Reproduce line used a WIDER scope than the figure: non-test `.go` files under `fastmcp/server/httpapp` and `fastmcp/auth`.** AND THE TREE HAD NOT MOVED — the check that makes this a documentation shortfall rather than drift: the identical pattern run at this file's own last commit (**`6dc06203`**) already returns **124**, with **0 registration lines added or removed** between that commit and the tip (compare the `mux.HandleFunc(` line sets). **The two missing registrations are the friction channel's**, now documented in **§1.21** (`seat_feedback_mount.go:73`, `:76`) — which is also why the earlier **122** figure and the sentence built on it (`the 2026-10-05 figure below plus PUT /api/v2/openrig/rooms/{room}/team`) do not close arithmetically.** The earlier dated figures below are kept as the snapshots they are and were **not** re-derived in this pass.** **THESE COUNTS ARE RE-DERIVABLE IN ONE COMMAND, WHICH IS THE POINT OF THEM BEING NUMBERS AT ALL: `COUNTS-AUDIT.py`, **beside the seat area at `/home/daihu/.openrig/agenthub-seats/4genthub-min/COUNTS-AUDIT.py` and deliberately NOT in this repository — so a seat runs it and CI cannot**, re-runs every headline figure this document states — the two registration counts, the tool counts, the table counts, the 39 total and the SQL statement count — and exits non-zero when any of them differs from the tree. It is read-only by construction (no `--write` at all), so a gate may run it as it stands. **Both halves of it have been seen to work: it exits 0 on the tree it currently describes, and `python3 COUNTS-AUDIT.py --self-test` perturbs one expectation by one and REQUIRES the audit to notice — that is the control, because a checker never seen to fail is the same object as no checker at all. It was in fact RED before `e6829b32`: its `httpapp` expectation still read 124 while the tree had moved to 125 when `O1a` added `GET /{id}/events`, so the number it was one behind on was found by running it, not by reading it. The expectation now reads 123, which is what both the tree and this paragraph state.** At HEAD **2026-10-06** *(as this paragraph was first written)*, the same pattern gave **122** registrations in `httpapp` + **20** in `fastmcp/auth/{interface,api}` = **142 total**: the 2026-10-05 figure below plus `PUT /api/v2/openrig/rooms/{room}/team` (the D5 room-sharing route, `seat_admin_mount.go:301`). At HEAD **2026-10-05**, the pattern `grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/server/httpapp | grep -v _test.go` gives **121** registrations across 15 files, plus **20** in `fastmcp/auth/{interface,api}` = **141 total registrations**. The earlier figure — **120** in `httpapp` + 20 = **140 total** — was the snapshot at `c4ff8d42`, before the seat-type create route (`POST /api/v2/openrig/seat-types`, `seat_admin_mount.go:307` today) was added; the two counts differ by that one route, not by a wrong method. No routes are registered outside those packages (`grep -rn 'HandleFunc(' cmd/` → 0 matches; the process only calls `app.Handler()` at `cmd/agenthub/main.go:52`).

Where a handler is an inline closure wrapping a `routes.*` function, the handler column
names the function that actually performs the work; the registration line is the mount.

**CITATION RE-DERIVATION (2026-10-06, docs duty pass 3) — the `file:line` in every `§1.*` row was re-resolved against the tree rather than trusted.** The method: for each row, read the file's own `base` const, resolve the row's path, and match it to the registration that actually carries that method+path; then compare with the cited number. **21 of the 144 route rows cited a line that was no longer the registration** — `app.go` had drifted 10–11 lines and `seat_mount.go` 73, because **a `file:line` is a pointer that rots every time code is added above it, while the mount files that had not changed still matched exactly** (which is what distinguishes drift from a wrong method). All 21 now cite their registration line, and the check is repeatable: re-resolve, compare, report the set. **Scope: §1's route rows, §2's citations, §5's two quoted-report cites and §3's table citations were all re-derived in this pass (see §3.6 for the table half); §4's gone-list holds commands rather than citations and was NOT re-run.** **The audit is repeatable rather than a one-off: it is kept as `CITATION-AUDIT.py` beside the seat area, with the false-positive caveat in its docstring — its `loose` matches are hypotheses, and three of the first run's reports were exactly that.**

Path convention for the Registration column: paths are relative to `agenthub_go/`; from
§1.2 on, the column gives the BASENAME (`branch_routes.go:61`) because the section header
already names the full file, while §1.1 and §1.6–§1.12 give the path from `agenthub_go/`.
Both forms point at the same kind of thing — the line that registers the route.

### 1.1 Server-level and `app.go`

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/health` | `handleHealth` | `fastmcp/server/httpapp/app.go:122` |
| POST | `/api/v2/projects/` | `routes.CreateProject` | `fastmcp/server/httpapp/app.go:146` |
| GET | `/api/v2/projects/` | `routes.ListProjects` | `fastmcp/server/httpapp/app.go:159` |
| GET | `/api/v2/projects/{id}` | `routes.GetProject` | `fastmcp/server/httpapp/app.go:167` |
| PUT | `/api/v2/projects/{id}` | `routes.UpdateProject` | `fastmcp/server/httpapp/app.go:175` |
| DELETE | `/api/v2/projects/{id}` | `routes.DeleteProject` | `fastmcp/server/httpapp/app.go:196` |
| POST | `/api/v2/projects/{id}/health-check` | `routes.ProjectHealthCheck` | `fastmcp/server/httpapp/app.go:204` |

**The project-creation contract, STATED rather than implied — `POST /api/v2/projects/` (the trailing slash is part of the route) accepts `application/x-www-form-urlencoded` ONLY.** `app.go:135` registers it and `:137-144` reads it with `_ = r.ParseForm()` and `r.PostForm.Get("name")`: **`name` is required and `description` is optional**, and neither a JSON body nor a multipart body is read at all. **A JSON or multipart request is therefore refused with the SAME `422` that reports `body.name` missing**, because `ParseForm` reads neither encoding — so the refusal names a **MISSING FIELD** rather than the **ENCODING**, which is why two independent callers concluded they had a payload problem when they had a content-type problem. The application itself sends exactly this shape (`agenthub-frontend/src/services/apiV2.ts:475` posts `name`/`description` with `Content-Type: application/x-www-form-urlencoded`, and its flow measures **200** end to end), so **the route is not wrong — it was merely unstated.** **THE REUSABLE HALF: A REFUSAL THAT NAMES THE WRONG CAUSE COSTS A CALLER THE SAME TIME AS A SILENT FAILURE** — the same family as the reason text that never reached the chip, the preview read that looked truncated, and the grep that looked absent from the wrong field; and this is that family's **cheapest instance to fix, because the fix is a documented contract rather than a change to the refusal.**

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
| GET | `/api/v2/tasks/{id}` | `routes.GetUserTask` | `task_routes.go:99` |
| GET | `/api/v2/tasks/{id}/events` | `routes.GetTaskEvents` | `task_routes.go:103` |
| PUT | `/api/v2/tasks/{id}` | `routes.UpdateUserTask` | `task_routes.go:113` |
| DELETE | `/api/v2/tasks/{id}` | `routes.DeleteUserTask` | `task_routes.go:136` |
| POST | `/api/v2/tasks/{id}/complete` | `routes.CompleteUserTask` | `task_routes.go:140` |

**DRIFT FOUND AND REPAIRED 2026-10-08 at HEAD `88d27758` (docs duty pass 4).** *Three rows in the table above cited a line that is no longer a registration (`PUT {id}` 107->117, `DELETE {id}` 130->140, `complete` 134->144) and one route had no row at all.* **The control that names the cause rather than assuming it: every moved row moved by EXACTLY +10, and the insertion that did it is the `GET /{id}/events` route — one registration plus its closure, added above them.** *So this is the rotted-pointer class the §1 citation pass predicted, reproduced on schedule, and the fix is a line number, not a re-reading of the table.* **Re-resolve a row by reading the file's own `base` const and matching the row's method+path to the registration that carries it — never by trusting the number.**

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
| POST | `/mcp` | JSON-RPC dispatcher (`handleJSONRPC`) | `mcp_routes.go:74` |
| GET | `/mcp` | `mcpSSEHandler` (SSE) | `mcp_routes.go:139` |

### 1.7 WebSockets (`ws_mount.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/ws/realtime` | `handleRealtime` | `ws_mount.go:68` |
| GET | `/ws/connector` | `handleConnector` | `ws_mount.go:69` |
| GET | `/ws/sessions/{id}` | `handleSessionViewer` | `ws_mount.go:70` |

**DECLARED OUT OF SCOPE — THE THREE UNMOUNTED OLD-PROTOCOL WEBSOCKET ENDPOINTS (owner decision, 2026-10-06).** **The old-protocol surface served by `fastmcp/websocket/server.go` is NOT mounted on the live handler:** it registers **`/ws/{user_id}`** (`server.go:92`), **`/ws/health`** and **`/ws/stats`** (`server.go:93-94`) on **its own app**, and **nothing outside that package constructs it** (`NewWebSocketServer` has no non-test caller — the only imports of the package elsewhere are `wslib` for the `WebSocket` type, in `ws_mount.go:37` and `server/routes/websocket_routes.go:25`). **THE OWNER DECLARED THESE THREE OUT OF SCOPE RATHER THAN MOUNTING THEM, which is the honest closure of the parity claim: THE PORT IS COMPLETE FOR THE SURFACE IN USE, with `/ws/{user_id}`, `/ws/health` and `/ws/stats` DELIBERATELY EXCLUDED** — so nothing reads as though the old protocol is fully served. **AND IT IS A DECISION RATHER THAN AN OMISSION:** mounting them would have added endpoints **nothing consumes**, and **the owner chose the honest label over the tidier-looking port.**

### 1.8 MCP registration / metrics (`misc_mount.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/register` | `mcpRegistrationStore.register` | `misc_mount.go:63` |
| POST | `/unregister` | `mcpRegistrationStore.unregisterResponse` | `misc_mount.go:67` |
| GET | `/registrations` | `mcpRegistrationStore.listResponse` | `misc_mount.go:70` |
| GET | `/ws/metrics` | `handleWebSocketMetrics` | `misc_mount.go:73` |

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
| GET | `/api/tasks/{task_id}/context/summary` | `routes.GetTaskContextSummary` | `routes_mount.go:406` |
| POST | `/api/subtasks/summaries` | `routes.GetTaskRouteSubtaskSummaries` | `routes_mount.go:412` |
| GET | `/api/performance/metrics` | `routes.GetPerformanceMetrics` | `routes_mount.go:421` |
| POST | `/api/v2/tasks/{task_id}/subtasks/summaries` | `routes.GetUserSubtaskSummaries` | `routes_mount.go:424` |

### 1.16 OpenRig seat management — admin (`seat_admin_mount.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/openrig/rooms` | `handleCreateRoom` | `seat_admin_mount.go:292` |
| GET | `/api/v2/openrig/rooms` | `handleListRooms` | `seat_admin_mount.go:295` |
| DELETE | `/api/v2/openrig/rooms/{room}` | `handleDeleteRoom` | `seat_admin_mount.go:298` |
| PUT | `/api/v2/openrig/rooms/{room}/team` | `handleSetRoomTeam` | `seat_admin_mount.go:301` |
| GET | `/api/v2/openrig/seat-types` | `handleListSeatTypes` | `seat_admin_mount.go:304` |
| POST | `/api/v2/openrig/seat-types` | `handleCreateSeatType` | `seat_admin_mount.go:307` |
| POST | `/api/v2/openrig/seat-types/{slug}/versions` | `handleCreateSeatTypeVersion` | `seat_admin_mount.go:310` |
| GET | `/api/v2/openrig/modules` | `handleListModules` | `seat_admin_mount.go:313` |
| GET | `/api/v2/openrig/modules/{slug}/versions/{version}` | `handleGetModuleVersion` | `seat_admin_mount.go:316` |
| PUT | `/api/v2/openrig/modules/{slug}/versions/{version}` | `handlePutModuleVersion` | `seat_admin_mount.go:319` |
| POST | `/api/v2/openrig/rooms/{room}/seats` | `handleCreateSeat` | `seat_admin_mount.go:322` |
| GET | `/api/v2/openrig/rooms/{room}/seats` | `handleListSeats` | `seat_admin_mount.go:325` |
| DELETE | `/api/v2/openrig/rooms/{room}/seats/{seat}` | `handleRemoveSeat` | `seat_admin_mount.go:328` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/occupant` | `handleSetSeatOccupant` | `seat_admin_mount.go:331` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/permission-policy` | `handleSetSeatPermissionPolicy` | `seat_admin_mount.go:334` |
| PUT | `/api/v2/openrig/rooms/{room}/overlay` | `handleRoomOverlay` | `seat_admin_mount.go:337` |
| GET | `/api/v2/openrig/overlay` | `handleGetCompanyOverlay` | `seat_admin_mount.go:340` |
| PUT | `/api/v2/openrig/overlay` | `handleCompanyOverlay` | `seat_admin_mount.go:343` |
| GET | `/api/v2/openrig/rooms/{room}/overlay` | `handleGetRoomOverlay` | `seat_admin_mount.go:346` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/overlay` | `handleSeatOverlay` | `seat_admin_mount.go:349` |
| GET | `/api/v2/openrig/rooms/{room}/seats/{seat}/overlay` | `handleGetSeatOverlay` | `seat_admin_mount.go:352` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/links` | `handleUpsertSeatLink` | `seat_admin_mount.go:355` |
| GET | `/api/v2/openrig/rooms/{room}/seats/{seat}/links` | `handleListSeatLinks` | `seat_admin_mount.go:358` |
| DELETE | `/api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}` | `handleDeleteSeatLink` | `seat_admin_mount.go:361` |
| GET | `/api/v2/openrig/settings` | `handleGetSettings` | `seat_admin_mount.go:364` |
| PUT | `/api/v2/openrig/settings` | `handlePutSettings` | `seat_admin_mount.go:367` |

**Update 2026-10-06 (D5 sharing).** `PUT /api/v2/openrig/rooms/{room}/team` (`handleSetRoomTeam`) is new — it is the route that shares one room, read-only, with one team's members, or makes it private again — and **every Registration line in this section was refreshed from the source in the same pass**, because that insertion shifted them all; all 26 rows were then re-checked one by one against the registrations they cite.

**Update 2026-10-05 (docs truth-audit).** The `POST /api/v2/openrig/seat-types` row was **missing** (the D3 create-a-seat-type route, `seat_admin_mount.go:307`) and every Registration line in this section was stale by the insertion; both are corrected here from the source at HEAD, which is why this section went from 24 to 25 rows.

Note: the mutating rows are wrapped in `seatMutation(kind, action, fn)` (a broadcast +
audit wrapper), except `handleCreateRoom`/`handleListRooms` and the GETs.

### 1.17 OpenRig seat management — seat resolution / machine / status / rigspec

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v2/openrig/seats/{room}/{seat}` | `handleResolveSeat` | `seat_mount.go:184` |
| POST | `/api/v2/openrig/seat-types/seed` | `handleSeedSeatTypes` | `seat_mount.go:187` |
| GET | `/api/v2/openrig/rooms/{room}/rigspec` | `handleRoomRigSpec` | `seat_rigspec_mount.go:105` |
| POST | `/api/v2/openrig/machines` | `handleRegisterMachine` | `machine_token_mount.go:41` |
| DELETE | `/api/v2/openrig/machines/{machine}/token` | `handleRevokeMachineToken` | `machine_token_mount.go:44` |
| POST | `/api/v2/openrig/seat-status` | `handlePostSeatStatus` (`machineAuthed`) | `seat_status_mount.go:95` |
| GET | `/api/v2/openrig/machines` | `handleListMachines` | `seat_status_mount.go:98` |

**DRIFT FOUND AND REPAIRED 2026-10-08 (same pass as §1.3).** *Both rows in this section cited a line no longer in the file (`seat-status` 91->95, `machines` 94->98).* **The control: both moved by EXACTLY +4 — four lines were added above them in one change, so the drift is one insertion rather than two coincidences.**

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

### 1.20 Teams — base `/api/v2/openrig/teams` (`team_mount.go`)

Added by NEXT_GEN D5 (teams and sharing, slice 1). `{team}` is the team slug, looked up
within the caller's memberships.

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/openrig/teams` | `handleCreateTeam` | `team_mount.go:72` |
| GET | `/api/v2/openrig/teams` | `handleListTeams` | `team_mount.go:75` |
| GET | `/api/v2/openrig/teams/{team}` | `handleGetTeam` | `team_mount.go:78` |
| DELETE | `/api/v2/openrig/teams/{team}` | `handleDeleteTeam` | `team_mount.go:81` |
| GET | `/api/v2/openrig/teams/{team}/members` | `handleListTeamMembers` | `team_mount.go:84` |
| POST | `/api/v2/openrig/teams/{team}/members` | `handleAddTeamMember` | `team_mount.go:87` |
| PATCH | `/api/v2/openrig/teams/{team}/members/{user}` | `handleUpdateTeamMember` | `team_mount.go:90` |
| DELETE | `/api/v2/openrig/teams/{team}/members/{user}` | `handleRemoveTeamMember` | `team_mount.go:93` |

### 1.21 Friction channel — base `/api/v2/openrig/feedback` (`seat_feedback_mount.go`)

**Added to this inventory on 2026-10-06 (docs duty pass 3): these two registrations were MOUNTED and were not documented here**, which is what made §1's count two short (§1's corrected counts paragraph carries the measurement).

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/openrig/feedback` | `handleSubmitSeatFeedback` (inline closure behind `seatFeedbackAuthed`) | `seat_feedback_mount.go:73` |
| GET | `/api/v2/openrig/feedback` | `handleListSeatFeedback` (inline closure behind `authed`) | `seat_feedback_mount.go:76` |

**Auth — read from the mount rather than assumed.** The **POST accepts a machine token OR a user token** (`seat_feedback_mount.go:7` states the pair, `:18-21` states why: the row is written under the token's own user id, so a machine token cannot write outside its tenant), and the order is load-bearing: `seatFeedbackAuthed` (`:91`) tries the machine-token store first (`:100`), because a machine token is an exact hash match while the user path can resolve a token that is not a user token when the auth layer's development fallback is running (`:83-89`); an invalid machine token **falls through to the user path** (`:110`, "Not a machine token: the user path gets it"), while a machine-token **lookup failure is an error** (`:112`) rather than a fall-through. The **GET takes a user token** only (`authed`).

**Request shape — defined at `seat_feedback_mount.go:64-70`** (`seatFeedbackSubmission`: `room`, `seat`, `layer`, `text` required; `session` optional). The `layer` vocabulary is the DDL's closed set (`runtime`, `openrig`, `cloud`, `seat-context`, `workspace`, `other`) rather than a list in this document; the credential scan and the page that groups by layer are described once in `README.md`'s *Rig and OpenRig workflow* section. **The third door onto the same writer is the MCP tool `submit_feedback` (§2.3) and the fourth is `scripts/seat_feedback.sh`.**

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
(`fastmcp/server/httpapp/mcp_routes.go:257`), which does exactly two things:

1. iterates `DDDCompliantMCPTools.ToolDefinitions()`
   (`fastmcp/task_management/interface/ddd_compliant_mcp_tools.go:221`), and
2. appends **four** schemas `ToolDefinitions` does not carry — `manage_seat`, `call_seat`, `submit_feedback` and the connection tool (`mcp_routes.go:278`, `:287`, `:296`, `:305`).

There is no other filter or source.

**Citations re-derived and one claim corrected (2026-10-06, docs duty pass 3).** Every line above was re-resolved against the tree rather than trusted: `getMCPToolsList` had moved **236 → 257** and `ToolDefinitions` **218 → 221**; and **the appended count read THREE where the code appends FOUR** — `tools := make([]map[string]any, 0, len(defs)+4)` (`mcp_routes.go:262`) with four appends (`:278`, `:287`, `:296`, `:305`) — **which this same document's §2.3 table and §2.5 already called four, so this section was contradicting its own table as well as the code.** The stale range `249-274` is now the four real lines.

### 2.2 MCP protocol methods (NOT tools)

`handleJSONRPC` (`fastmcp/server/httpapp/mcp_routes.go:173`) implements these JSON-RPC
methods. They are the protocol layer and MUST NOT be listed as tools:

`initialize`, `notifications/initialized`, `ping`, `tools/list`, `resources/list`,
`prompts/list`, `tools/call` (all in `handleJSONRPC`, `mcp_routes.go:173`).

`initialize` and `tools/list` additionally require a bearer token when
`AUTH_ENABLED=true` (default), enforced in `authorizeMCPMethod` (`mcp_routes.go:145`).
`resources/list` and `prompts/list` return empty lists.

### 2.3 Published tools (`tools/list`)

Ten tool names, always present except `manage_context` (see note):

| Tool | Source | File:line |
|---|---|---|
| `manage_task` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:223` |
| `manage_subtask` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:227` |
| `manage_context` | `ToolDefinitions` (conditional) | `ddd_compliant_mcp_tools.go:233` |
| `manage_project` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:239` |
| `manage_git_branch` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:244` |
| `manage_agent` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:249` |
| `manage_seat` | appended schema | `mcp_routes.go:279` (`ManageSeatToolName`, `manage_seat_controller.go:12`) |
| `call_seat` | appended schema | `mcp_routes.go:288` (`CallSeatToolName`, `call_seat_controller.go:14`) |
| `submit_feedback` | appended schema | `mcp_routes.go:297` (`SubmitFeedbackToolName`, `submit_feedback_controller.go:18`; args `room, seat, session, layer, text`) |
| `manage_connection` | appended schema | `mcp_routes.go:301` (`connTool, err := connectionToolDefinition()`, appended at `:305`; definition `mcp_connection_tool.go:39`) |

Note: `manage_context` is emitted only when `ContextController != nil`; the constructor
sets it when `DatabaseAvailable` is true (`ddd_compliant_mcp_tools.go:110-114`), and
`app.go:71` passes `DatabaseAvailable: true`. So on a wired server all ten are present.
**Measured at HEAD `763b8196` (2026-10-06): a booted server answers `tools/list` with exactly
these ten names.**

`tools_golden.json`
(`fastmcp/task_management/interface/testdata/tools_golden.json`) contains only the six
Python-registry tools; `TestMCPToolsListMatchesGolden` filters the **four** names the Go server
appends (`manage_seat`, `call_seat`, `submit_feedback`, `manage_connection`) and asserts the
rest equals golden.

### 2.4 Dispatch-only names (callable via `tools/call`, NOT advertised by `tools/list`)

`dispatchMCPTool` (`mcp_routes.go:324`) also handles two legacy names that are **not**
published in `tools/list`:

- `get_mcp_status` (`mcp_routes.go:357`)
- `check_session_health` (`mcp_routes.go:363`)

Anything else returns `{"error":"Unknown tool: <name>"}` (`mcp_routes.go:469`, `default`).

### 2.5 Configuration gating — important negative finding

The Python-derived `ToolConfig` subsystem still exists in Go
(`fastmcp/task_management/infrastructure/configuration/tool_config.go:22`) with a
`TOOL_*` enablement table (`manage_project`, `manage_task`, `manage_subtask`,
`manage_agent`, `manage_seat`, `manage_document`, `update_auto_rule`, `validate_rules`,
`regenerate_auto_rule`, `validate_tasks_json`, `create_context_file`, `manage_context`).

**In this Go server that table does not gate `tools/list`.** Evidence:
`DDDCompliantMCPTools` builds a `ToolConfig` and passes it to controllers
(`ddd_compliant_mcp_tools.go:65`, `cfg, err := configuration.NewToolConfig(...)`), but the only method any caller invokes on it is
`IsWorkflowGuidanceEnabled()` (`git_branch_mcp_controller.go:176`,
`subtask_mcp_controller.go:336`, `agent_mcp_controller.go:249` — all three verified present). `GetEnabledTools` has no
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

### 3.3 Seat-management and team tables — appended to `Tables` via `init()`

Declared in `fastmcp/seat_management/infrastructure/database/seat_tables.go` (`seatDatabaseTables`, **14 entries**, `seat_tables.go:16`) and
`team_tables.go` (`teamManagementDatabaseTables`, **2 entries**, `team_tables.go:24`). **The two are composed and registered in ONE place** — `seatManagementDatabaseTables` (`seat_tables.go:357`, `append([]taskdb.TableDef{}, teamManagementDatabaseTables...)` then `seatDatabaseTables...`) and the package's `init()` (`seat_tables.go:362`). **`team_tables.go` contains no `init()` and does not append; an earlier version of this section cited an append at `team_tables.go:56`, which does not exist.** The same **16** tables are declared as DDL in
`fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql`: **the 14 seat tables plus the 2 team tables** (note for a reader counting
statements: `grep -c 'CREATE TABLE IF NOT EXISTS'` returns **17** because the file's header
COMMENT at line 6 contains that phrase; `grep -cE '^CREATE TABLE IF NOT EXISTS'` -> **16**, one per table, and no
table is declared twice). **BOTH FIGURES IN THIS PARAGRAPH MOVED WHEN `seat_feedback` LANDED** — the 15/16 pair that stood here was the 15-table state, and the one-table difference is precisely the table this section did not list.

| Table | Model | Declaration (Go) | SQL |
|---|---|---|---|
| `modules` | `ModuleORM` | `seat_tables.go:17` | `seat_management_postgresql.sql:46` |
| `module_versions` | `ModuleVersionORM` | `seat_tables.go:36` | `:61` |
| `seat_types` | `SeatTypeORM` | `seat_tables.go:59` | `:77` |
| `seat_type_versions` | `SeatTypeVersionORM` | `seat_tables.go:79` | `:93` |
| `teams` | `TeamORM` | `team_tables.go:25` | `:121` |
| `team_members` | `TeamMemberORM` | `team_tables.go:45` | `:135` |
| `rooms` | `RoomORM` | `seat_tables.go:102` | `:159` |
| `seats` | `SeatORM` | `seat_tables.go:125` | `:177` |
| `overlays` | `OverlayORM` | `seat_tables.go:158` | `:200` |
| `seat_links` | `SeatLinkORM` | `seat_tables.go:190` | `:225` |
| `resolved_seats` | `ResolvedSeatORM` | `seat_tables.go:216` | `:245` |
| `seat_settings` | `SeatSettingsORM` | `seat_tables.go:241` | `:263` |
| `seat_feedback` | `SeatFeedbackORM` | `seat_tables.go:317` | `:278` |
| `machines` | `MachineORM` | `seat_tables.go:253` | `:296` |
| `machine_tokens` | `MachineTokenORM` | `seat_tables.go:267` | `:308` |
| `seat_status` | `SeatStatusORM` | `seat_tables.go:287` | `:323` |

**`seat_feedback` IS THE ROW THIS DOCUMENT WAS MISSING (added 2026-10-06, pass 3).** It is registered (`seat_tables.go:317`), declared in the DDL (`:278`), and read by `NewORMSeatFeedbackRepository` over `seat_feedback` (`seat_management/infrastructure/repositories/orm/seat_feedback_repository.go:25`, `:47`); **`app.go:61-63` records that the boot needs the table registered, which is why it is in the composition rather than beside the routes.** **Its absence is what made §3.5's total one short and §3.3's SQL count one under the file's own `grep -cE`.**

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

- `database.Tables` at runtime: 20 (core) + 3 (auth) + **14** (seat) + 2 (team) = **39 tables** — **corrected from 38 on 2026-10-06 (pass 3): the inventory had never listed `seat_feedback`, which is the fourteenth seat table (§3.3).**
- Plus `ProductionTables`: **6** tables declared but not registered for creation.
- **Both totals, and every count in this document, are re-derived by `COUNTS-AUDIT.py` beside the seat area — read-only, non-zero on any difference, safe to run in a gate (§1 carries the same pointer).**
- Every table in §3.1–3.4 carries a `user_id` column except `applied_migrations`
  (a migration ledger; `models_prod.go:118`).

### 3.6 Re-derivation of this section (2026-10-06, docs duty pass 3)

**Every citation in §3.1–§3.4 was re-measured against the tree rather than trusted, and the section was found ONE TABLE SHORT AND STALE IN EVERY LINE NUMBER OF §3.3.** (a) **`seat_feedback` was missing entirely** — registered at `seat_tables.go:317`, declared in the DDL at `:278`, read by `NewORMSeatFeedbackRepository` (`seat_feedback_repository.go:25`, `:47`); **with it the seat block is 14 tables and the runtime registry is 39, not 38.** (b) **Every `seat_tables.go`, `team_tables.go` and SQL line number in §3.3 was stale** — the Go cites by 3–36 lines, the SQL cites by 12–66. (c) **`team_tables.go:56`, cited as an append site, does not exist**: `team_tables.go` has no `init()` at all; the composition and the single append are `seat_tables.go:357` and `:362`. **§3.1, §3.2 and §3.4 came through clean — the 20 core entries, the three auth entries and the six `ProductionTables` matched name-for-name and line-for-line — and that is the control that says this method finds real drift rather than inventing it.** **The counting method is worth keeping: entries are counted at DEPTH 1 of each registry's literal (`{Name: "...", Model: ...}`), because a plain `grep -c 'Name:'` counts every COLUMN and reports 572 for a 20-table registry.** **§4's gone-list holds commands and their outputs rather than citations; those were not re-run in this pass.**

---

## 4. Gone list

Each entry states the exact command and its result. "NO MATCH" = the command exited with
no output.

| Retired item | How established it is gone | Command | Result |
|---|---|---|---|
| `agenthub_main/agent-library` (Python agent library) | directory absent on disk and untracked in git; removed by commit `60bcdb68` | `ls agenthub_main/agent-library` ; `git ls-files 'agenthub_main/agent-library*' \| wc -l` ; `git log --oneline -1 -S'agent-library' -- agenthub_main` | `No such file or directory` ; `0` ; `60bcdb68 refactor(agents): remove the Python agent library and agent management (T8 Python half)` |
| `call_agent` **tool** (MCP tool "load agent instructions") | no tool definition, absent from `tools_golden.json`, and the test suite asserts its absence | `grep -rn 'Name: *"call_agent"' agenthub_go --include='*.go' \| grep -v .gomodcache` ; `grep -n 'removed call_agent tool' agenthub_go --include='*_test.go'` | `NO MATCH` ; `call_seat_mcp_test.go:64: t.Fatal("tools/list still publishes the removed call_agent tool")` *(line corrected from `:62` on re-execution, 2026-10-06)* |
| `/api/v2/openrig/agents` route | no registration anywhere in the Go tree | `grep -rn 'openrig/agents' agenthub_go --include='*.go' \| grep -v .gomodcache` | `NO MATCH` |
| `agent_templates` table | no declaration in Go models/DDL or in the production SQL | `grep -rn 'agent_templates' agenthub_go --include='*.go' --include='*.sql'` ; `grep -rn 'agent_templates' agenthub_main --include='*.sql'` | `NO MATCH` (both) |
| `user_agent_instances` table | same as above | `grep -rn 'user_agent_instances' agenthub_go --include='*.go' --include='*.sql'` ; `grep -rn 'user_agent_instances' agenthub_main --include='*.sql'` | `NO MATCH` (both) |

**RE-EXECUTED 2026-10-06 (docs duty pass 3) — every command in this table was run again and its result compared with the text above.** **All five entries still hold**: the directory is absent and untracked, the removal commit is still `60bcdb68`, `call_agent` has no tool definition, and `openrig/agents`, `agent_templates` and `user_agent_instances` all return nothing in both trees. **One line number had moved and is corrected in the table: the assertion is at `call_seat_mcp_test.go:64`, not `:62`** — the same drift class as §1–§3, caught here by re-running rather than by re-deriving, which is why the two are different jobs. **And the distinction's three citations were verified by READING the lines rather than by grepping for the word**: `ddd_compliant_mcp_tools.go:249` is the `manage_agent` definition, `unified_agent_description.go:101` is `props.Set("call_agent", …)`, and `tool_input_schemas.go:126` is the `call_agent` schema entry — **so the tool is gone and the field is live, exactly as the note says.**

**Distinction that must not be collapsed:** `call_agent` the **tool** is gone, but
`call_agent` remains a **parameter/field of the `manage_agent` tool** (register/update):
`ddd_compliant_mcp_tools.go:249`, `agent_mcp_controller/unified_agent_description.go:101`,
`tool_input_schemas.go:126`. That field is deliberate and still live. A sentence about one
must not be read as a sentence about the other.

---

## 5. Contradictions between existing docs and the code — ALL CLOSED

This section was the rewrite worklist for owner directive (A). Every item below has been
corrected; each entry keeps the original finding so the audit trail survives, and names
the correction. The checks themselves are unchanged and re-runnable from Appendix A.

1. **`ai_docs/api-integration/mcp-tools-api-complete.md`** — **CLOSED** (`95ffca45`).
   The original finding: it documented the removed `call_agent` **tool** as live, listed
   eight tools and omitted `manage_seat` and `call_seat`, and claimed every tool requires
   `action`. The file now carries the ten published tools (`manage_seat` at line 13,
   `call_seat` at line 14), a `### call_agent — retired` section, and an explicit note
   that the two seat tools and `manage_connection` take no `action`.
2. **`ai_docs/api-behavior/api-parameter-handling-complete.md`** — **CLOSED**. The original
   finding: it shared the old tool set and predated the seat tools. It now carries a
   `Seat (manage_seat, call_seat)` row and states that the seat tools are the exception
   to the `action` rule.
3. **`ai_docs/architecture-design/Architecture_Technique.md`** — **CLOSED** (`95ffca45`
   and the 2026-10-06 truth-audit). The original finding: "32+ specialized agents", a
   **SQLite (fallback)** claim, and SQLAlchemy/Alembic described as the persistence path.
   The Python module tree and its SQLAlchemy examples are now covered by the
   **Retired implementation note** at line 224; the Database Layer states the Go
   `TableDef`/Postgres-only reality; the development, test and directory sections point at
   `agenthub_go`; and the "4-tier" framing appears only as the `{level}` set of the
   mounted `/api/v2/contexts/{level}` routes.
4. **`agenthub_go/PROD_READINESS_REPORT.md`** (Go module root, not `ai_docs`) —
   **SUPERSEDED IN PLACE** (`95ffca45`). A status block above the blocker table marks B4
   and B6 as no longer describing HEAD (`getMCPToolsList` builds from
   `ToolDefinitions()`, `mcp_routes.go:236`; `GET /mcp` is `mcpSSEHandler`,
   `mcp_routes.go:116`; `models_prod.go` declares six `ProductionTables` — **the two line numbers are the REPORT'S, taken at `c4ff8d42`; the live ones are `mcp_routes.go:257` and `:138` (re-derived 2026-10-06, pass 3), and the report's block is left as the dated quotation it is**), while the
   original findings stay visible as the dated record they are.
5. **Cross-check `/tmp/inv.md`** (reviewer inventory, HEAD `c4ff8d42`) — retained for its
   method only. Its three divergences from the code are settled in this document: the
   `TOOL_*` gating claim in §2.5, `initialize`/`ping` as protocol methods rather than
   dispatch cases in §2.2, and the route count in §1 (its 112 was `httpapp`-only; the
   current figure is 121 + 20 = 141). Its table sections omit the three auth tables and
   the six `ProductionTables`, both carried in §3.

---

## Appendix A — acceptance commands

Run from `/home/daihu/__projects__/4genthub/agenthub_go` unless noted.

**Why every count below carries its command:** a count of text is not a count of structure, and four conflations found in this rig are the reason — an `httpapp`-only glob read as the whole tree (which hid the 20 auth registrations), a registration read as its truncated `base + suffix` tail, a header COMMENT counted as a `CREATE TABLE` statement (the unanchored 14 versus the anchored 13), and `initialize` read as a dispatch case when it is a `handleJSONRPC` protocol method. Each count below is therefore the structurally anchored form, and where two counts of one thing disagree, the discrepancy is evidence to CHECK rather than a story to tell.

```bash
# Every route registration (the source of §1)
grep -rn 'mux.HandleFunc(\|mux.Handle(' --include='*.go' fastmcp/server/httpapp | grep -v '_test.go'
grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/auth | grep -v '_test.go'
# Counts: 121 httpapp + 20 auth = 141
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
grep -n '^\t{Name: "' fastmcp/seat_management/infrastructure/database/team_tables.go
grep -n '^\t{Name: "' fastmcp/auth/infrastructure/database/models_auth.go
grep -n '^\t{Name: "' fastmcp/auth/infrastructure/repositories/email_token_repository.go

# Gone list (see §4)
grep -rn 'openrig/agents' agenthub_go --include='*.go' | grep -v .gomodcache          # NO MATCH
grep -rn 'Name: *"call_agent"' agenthub_go --include='*.go' | grep -v .gomodcache     # NO MATCH
grep -rn 'agent_templates\|user_agent_instances' agenthub_go --include='*.go' --include='*.sql'  # NO MATCH
ls agenthub_main/agent-library                                                        # No such file or directory
```
