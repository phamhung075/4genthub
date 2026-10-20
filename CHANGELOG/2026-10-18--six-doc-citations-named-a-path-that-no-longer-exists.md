# Six doc citations named a path that no longer exists

A read-only sweep of the documentation trees on 2026-10-18 (board item `79813f48`) extracted 731 citation
tokens from the 46 `ai_docs/**/*.md` files at `main` and the 68 `skills/**/*.md` files of the client at the pin
main names, and resolved each one against the tracked trees, the derived directories and the files on disk.
198 were dead; 164 of those were repo paths, and after reading every dead token in its paragraph 6 were still
presented as current - the other 158 are correction trails the docs carry themselves, paths belonging to
another tree, or files the skill says it does not vendor.

## Changed

Six citations now name what exists; each replacement's target was opened at the tree the sentence is about.

- `ai_docs/core-architecture/agenthub-system-architecture.md:526` - the `status` parity spec
  `internal/clientsync/status.go` is gone from the client; the verb is `internal/clientlifecycle/lifecycle.go:994`
  (`statusCommand`, registered at `:101`). The sentence's "its test is the parity spec" claim had no live file
  and no dedicated test, so it is dropped rather than re-pointed.
- `ai_docs/core-architecture/rigd-boundaries.md:22` - "the same files exist in BOTH `agenthub_client` and
  `agenthub_go/internal/clientsync`" was false: the server copy was purged in `cbc51bae` with the legacy rig
  client, and the client routes moved to `/api/v2`. The duplication sentence goes with it.
- `ai_docs/operations/complete-operations-guide.md:346` - the "no Redis client" claim cited
  `fastmcp/server/session_store.go:23` and `zpSessionRedisAvailable`, neither of which exists in any Go file.
  The claim still holds (`go.mod` has no redis dependency) and is now cited to
  `fastmcp/task_management/infrastructure/repositories/cached/cache_client.go:7-8`, which states it and injects
  `CacheClient` with `MemoryCache` as the in-process implementation.
- `ai_docs/verification/of4-local-stack.md:173` - `resolver.CheckRuntime`'s callers are
  `repositories/names.go:26` and `seatrenderer/renderer.go:45`; `rigspec/rigspec.go:124` exists nowhere in the
  client at the pin or at its head.
- `ai_docs/agent-system/skill-library.md:233` - the mirror guard is `4genteam team drift-check`
  (`agenthub_client/internal/clientteam/team.go:69`), which compares the sha256 a stored skill block records for
  its source and its mirror (`internal/clientteam/drift.go`); `scripts/skill-edge-digests.generated.json`
  exists in no tree and no script writes it.

The sixth citation is in the client's own `skills/` tree and carries its own entry there.

## Testing

No test: documentation. The sweep and the classification were run to completion and printed their counts
(`python3 /tmp/cite_audit.py` exit 0, then the classifier exit 0); the patched files were then re-extracted and
re-resolved against `main`, the client pin and the client head, and all six former dead tokens resolve.
