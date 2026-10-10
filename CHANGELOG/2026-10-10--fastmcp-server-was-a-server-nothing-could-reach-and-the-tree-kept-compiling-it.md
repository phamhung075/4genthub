## fastmcp/server was a server nothing could reach, and the tree kept compiling it

### Changed
- `agenthub_go/fastmcp/server/*.go` **DELETED**: **26 files, 17 of them source and 9 of them test.** `go list -deps` over the module reports **no package depending on `agenthub/fastmcp/server`**. The live server is `fastmcp/server/httpapp`, and this package was the first-draft port of Python's `server/` whose own test referenced `MCPHeaderValidationMiddleware` while nothing else did. The `httpapp`, `routes`, `metrics` and `cache` subpackages are **untouched** - separate packages, and `cache` has its own row.
- `agenthub_go/MIGRATION.md`: the 18 rows that mapped this Python package's files now read `removed-unreachable` instead of `done`, so the table no longer claims a live Go port for a package the tree does not have.

### Verified
- **Green AFTER the deletion, in the worktree it was applied to:** `gofmt -l` over the tracked Go files -> nothing; `go build ./...` -> rc 0; `go vet ./...` -> rc 0; `go test ./...` -> **141 packages ok, 0 FAIL**. The deletion cannot break a caller because there is no caller: `go list -deps` names none, which is the whole argument.

### Found by
- Row `47cd8f1c` (the second cascade of the auth cutover).
