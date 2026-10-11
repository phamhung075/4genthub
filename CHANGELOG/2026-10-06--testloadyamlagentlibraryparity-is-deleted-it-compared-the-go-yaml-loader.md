### Removed

**The unrunnable agent-library parity test, its fixture section, and the dead generation flag** (2026-10-06)

- `TestLoadYAMLAgentLibraryParity` is deleted. It compared the Go YAML loader against PyYAML for every file in `agenthub_main/agent-library`, and it **SKIPPED** - measured, not read off the skip - because that directory no longer exists. A test whose only input is gone cannot run again, so it is a deletion rather than a skip.
- The fixture it alone used is gone with it: `testdata/ordered_decode_cases.json` lost its `files` section (343 entries, **every one** an agent-library path). The file is SHARED - `TestLoadYAMLEdgeParity` reads `edge` (27 entries) and `TestDecodeJSONParity` reads `json` (20) - so only the parity test's section was removed and the other two are untouched.
- `generateRules` is dropped from the GetTask path: the use case's `Execute`, the service interface and implementation, the test fake, and **four call sites that only the compiler found** (a grep for the flag name missed them because they call positionally). Nothing read it inside `Execute` since the docs generator was removed, and no tool argument ever set it, so no behaviour changes.
- Stale bytecode for the deleted Python sources (`agent_routes`, `agent_invocation_handler`, `agent_doc_generator`) removed; all three are untracked and gitignored (`__pycache__/`), so nothing tracked was deleted as a side effect.
- Before and after, same package: the entities tests report **34 results with 1 SKIP -> 33 results with 0 SKIP**; the whole `task_management` tree passes, `go vet` and `go build` are clean, and `gofmt` reports nothing on the touched files.

**`healthVersion` 0.0.22 — the deploy marker for packet 4** (2026-10-06)

- Bumped from 0.0.21 in `agenthub_go/fastmcp/server/httpapp/http.go`. Packet 4 is no longer comment-only: it carries the AI-refusal surfacing, the pin label wording and the feedback channel, so a push without a marker could not be confirmed from outside. After the push, production must report **0.0.22**; the dashboard bundle hash must also move off `index-DQeJSJ5C.js`, and both containers must be replaced.
- Validated at the pre-bump tip in a separate worktree: `go build ./...` clean, `go vet ./fastmcp/server/...` clean, `go test ./...` -> 137 packages ok, 0 failed.

**`healthVersion` 0.0.21 — the deploy marker for this packet** (2026-10-06)

- Bumped from 0.0.20 in `agenthub_go/fastmcp/server/httpapp/http.go`. `/health` reporting the new value is the only external proof a deploy landed (the Docker build context has no `.git`, so no commit id can be embedded): after the push, production must read **0.0.21**. Packet 2 is the evidence that this is a check rather than a ceremony — it was confirmed from outside in seconds by reading the version, which a push without the bump could not have been.
- The marker has a second use, now proven twice: it DATES A RUNNING PROCESS. `/health` on a live container names the commit it is running, which answers a vintage question about a running service in one command.
- No test change was needed, CHECKED rather than assumed: `http_health_test.go:97` asserts the reported version against the CONSTANT rather than a pinned literal, and a grep for the old value across the Go tree returns nothing.
