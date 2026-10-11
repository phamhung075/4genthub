## The task 'updated' frame is stamped with the user who acted, so a browser can receive it again

### Fixed
- `agenthub_go/fastmcp/task_management/application/facades/task_application_facade.go` — the update broadcast stamped the literal `"system"`, because `UpdateTaskRequest` carries no user id. The gate in `websocket_routes.go` compares that stamp with each connection's own user (Rule 1) and, for `"system"`, falls to an ownership checker **nothing implements** (Rule 2), so every browser was refused while `create`, `complete` and the seat frames delivered — the shape of the operator's report. The stamp now comes from the request context through `f.deps.CurrentUserID`, the same seam `create` reads (wired to `middleware.GetCurrentUserID` in `task_wiring.go:138`); `"system"` remains the stamp for a broadcast with no actor at all.
- The gate is untouched: no exemption for `"system"`, no change to `IsUserAuthorizedForMessage`. That shortcut is pinned by a test rather than a comment.

### Verified
- **SEEN RED FIRST:** `TestTheUpdateBroadcastIsStampedWithTheActingUser`, driving the real facade and the real `UpdateTaskUseCase` over a repository fake, failed on the parent with `the 'updated' frame is stamped user "system", want the acting user "u-actor" ... so EVERY browser is denied`; it passes with the fix.
- The delivery contract is pinned on the other side of the stamp: `TestTaskUpdatedFrameReachesTheActingUsersSocket` asserts a stamped user receives its own task's `updated` frame and that the frame still carries `version 2.0`, `type update`, `payload.entity "task"` and `payload.data.primary` — the fields the client handler keys on — and `TestSystemStampedTaskUpdateIsRefusedForEveryConnection` asserts a `"system"`-stamped task update is refused, not exempted.
- `go test -count=1 ./fastmcp/task_management/application/facades/ ./fastmcp/server/routes/` → **ok** both; `go vet` clean on the facade package; `gofmt -l` prints nothing.
