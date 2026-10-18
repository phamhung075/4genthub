# A DB error denies ownership in every environment

## Fixed

- `agenthub_go/fastmcp/server/routes/websocket_routes.go`: `CheckResourceOwnership` no longer reads
  `ENVIRONMENT`. The branch that delivered a system-stamped cross-user frame whenever the value was
  exactly `development` - and fired only when `Ownership` was nil or an ownership query errored - is
  deleted. A nil checker or a failed query now denies, everywhere: a refusal answers the frame with
  `authorization_denied`, so a string can no longer decide an authorization outcome. `wrEnv` and its
  now-unused `os`/`strings` imports went with it.
- `agenthub_go/fastmcp/server/httpapp/ownership_wiring.go`: the wiring's own comments no longer promise
  an environment answer for "cannot tell"; `rowExists` returns the error and the caller denies on it.

## Tests

- New `TestAQueryErrorDeniesInEveryEnvironment` (internal `websocket_ownership_checker_test.go`): a
  checkered checker that errors must NOT deliver the frame under `ENVIRONMENT=development` or
  `production`, and the connection must still be told. Red before the fix: `development delivered the
  frame while the ownership query errored`; green after.
- The existing checker tests (`TestTheOwnershipCheckerDecidesASystemStampedFrame`,
  `TestTheEnvironmentStringDoesNotDecideWhenTheCheckerAnswers`) stay green; `websocket_task_update_test.go`'s
  header now names the deletion instead of describing the fallback as live.

## Verification

- `gofmt -l` on both packages: empty; `go vet`: clean.
- `go test ./fastmcp/server/routes/... ./fastmcp/server/httpapp/...`: pass.

Owning task: 092e908f-14f4-43ed-b386-67d52629a070 (Ownership R1).
