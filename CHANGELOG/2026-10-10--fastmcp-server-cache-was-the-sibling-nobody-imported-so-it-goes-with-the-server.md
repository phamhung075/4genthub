## fastmcp/server/cache was the sibling nobody imported, so it goes with the server package

### Changed
- `agenthub_go/fastmcp/server/cache/*.go` **DELETED** (2 files): `go list -deps` over the module reports **no package importing `agenthub/fastmcp/server/cache`** - the only line in the import graph that mentions it is the package's own dependency list - and an import-path grep outside the package is empty. It was the cache half of the same first-draft `server/` port that `68affa97` retired, carrying `CacheInvalidationHooks` and `RedisCacheManager` that nothing constructs. Deleted rather than carried as dead weight, and **not folded into that commit**: one dead package per commit, so a red check points at one cause.

### Verified
- **No importer, measured before the deletion** - the claim that has to hold, because a package deleted on a claim is how a live one gets deleted: `go list -deps` names no importer, and `grep -rn "fastmcp/server/cache" --include=*.go` outside the package returns nothing.
- **Green AFTER, in this worktree:** `gofmt` nothing; `go build ./...` rc 0; `go vet ./...` rc 0; `go test ./...` **141 packages ok / 0 FAIL**.
- **One transient red, named rather than hidden:** a first `go test ./...` after the deletion reported **7 FAIL** (`cmd/blockdrift` and six others), `blockdrift` failing on a guide hash divergence. Those packages depend on the deleted package **0 times**, and the same packages pass with the deletion in place once another seat's concurrent guide edit settled - so the red was a moving worktree, not this deletion. Stated because an unexplained red in this run would otherwise be read as this change's.

### Found by
- Row `9a30e883`; found while deleting `fastmcp/server/` (row `47cd8f1c`) and left alone there on purpose.
