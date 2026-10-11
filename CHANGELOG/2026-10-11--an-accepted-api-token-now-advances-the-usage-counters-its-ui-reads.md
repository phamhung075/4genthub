## An accepted API token now advances the usage counters its own UI reads

### What changed
G3, the Python-removal gate whose oracle had a behaviour the Go port lost: on an authenticated
API-token request the deleted Python advanced `api_tokens.usage_count` and `last_used_at`
(`DualAuthMiddleware`), and Go accepted the same token while writing nothing — so the token UI read
two fields no writer touched (`server/routes/token_router.go:64-65`) and three ported pieces sat
dead: `TokenRepository.UpdateTokenUsage` (`task_management/infrastructure/repositories/token_repository.go:151-156`),
`TokenUsageTrackingService`, and `DualAuthMiddleware.validateAPIToken`, whose own comment said the
bump "is not ported" (`auth/middleware/dual_auth_middleware.go:246-248`).

**The live path, stated because the row asked whether it is live at all: the API-token path IS live
in Go.** `POST /mcp` for `initialize`/`tools/list` (`server/httpapp/mcp_routes.go:160`), the
JSON-RPC bearer site (`:360`) and the realtime socket (`ws_mount.go:118`) all call
`auth.ValidateTokenUniversal`, whose first branch validates a `type=api_token` JWT through
`validateUnifiedAPIToken`. **What was missing was the write, not the path.**

- `fastmcp/auth/unified_token_validator.go`: a package-level seam
  `APITokenUsageRecorder func(ctx, tokenID)` plus `recordAPITokenUsage`, called from
  `validateUnifiedAPIToken` on acceptance with `result.TokenID` — which is the JWT's `jti`, the
  `api_tokens` row id the creation path mints (`token_application_facade.go:138-178`). The function
  now takes the `ctx` its caller always had.
- `fastmcp/server/httpapp/app.go`: `NewApp` wires the seam to the repository the token facade
  already writes through (`infrarepos.NewTokenRepository(sessions)` →
  `TokenRepository.UpdateTokenUsage`). A boot-time construction failure logs
  `api token usage recorder is NOT wired` rather than failing the boot; a per-request failure is
  swallowed, exactly as the ported Python swallowed it, because a usage counter must never refuse a
  request that has already been authenticated.

### Verified
- The reproduction ran BEFORE the wiring, on this seat's own cluster
  (`AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55451/postgres`), through the real
  route and the real repository:
  `go test -count=1 -run TestAuthenticatedAPITokenRequestAdvancesItsUsageCounters ./fastmcp/server/httpapp/`
  → `--- FAIL ... before usage_count=0 last_used_at=<nil>, after usage_count=0 last_used_at=<nil>` —
  the token was **accepted** (the request reached the assertion at HTTP 200) and the counters did
  not move.
- The same command after the wiring → `--- PASS`.
- `gofmt -l` over the tracked `.go` files prints nothing; `go build ./...` rc 0; `go vet ./...` rc 0;
  `go test -count=1 ./fastmcp/auth/...` all packages ok; `go test -count=1 ./fastmcp/server/httpapp/`
  green with the cluster set (the database cases run rather than skip).

### What this does NOT do
No per-operation `usage_stats`: `TokenUsageTrackingService` and the `usage_stats` column stay
unwired, which the row named as a separate decision, not this one.

No change to the `mcp_`-prefixed in-memory token path, which already had its own writer
(`auth/services/mcp_token_service.go`'s `mcpTokenUpdateUsage`), and none to the UI, which now reads
fields that move.

`DualAuthMiddleware` itself stays unwired — no construction site outside its own file — so its
`validateAPIToken` remains dead code; deleting it is a separate call, not this row's.

Row: `qitem-20261011001613-eb76dc4c9484798a` (G3 marker class table, filed by the lead).
