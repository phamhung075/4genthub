# The agy bridge takes the seat token from the environment, not argv

Date: 2026-10-19
Task: fd12b946 (`The agy bridge puts the seat's bearer token in mcp-proxy ARGV`)

## What was wrong

The runtime installs agy's MCP server as a `sh -c` line that ran
`mcp-proxy --headers Authorization "Bearer $AGENTHUB_TOKEN" ...`. The shell expanded the
seat's bearer token into the bridge's argv. `/proc/<pid>/cmdline` is world-readable, so every
local user could read the credential with `ps`; the environment (`/proc/<pid>/environ`) is
owner-only. Measured on the live room: the reviewer seat's agy (pid 19835) had a direct child
mcp-proxy (pid 19859) whose argv carried the full JWT.

## What changed

Client commit `82d2a62` (base `516a230`) replaces the header argument with an environment
hand-over: `API_ACCESS_TOKEN="$AGENTHUB_TOKEN" exec mcp-proxy --transport streamablehttp
--headers Accept ... "$AGENTHUB_URL/mcp"`. mcp-proxy 0.10.0 reads `API_ACCESS_TOKEN` from its
own environment (`mcp_proxy/__main__.py:274`) and sets `Authorization: Bearer` itself, so the
token never becomes an argument. A behavioural test puts a stand-in `mcp-proxy` on PATH and
asserts the recorded argv holds no `Bearer` while the environment does; it is red on the old
line and green on the new one. The omp and claude-code install sites are untouched.

## Evidence

- `cargo test --offline --manifest-path rust/agenthub-runtime/Cargo.toml`: 208 passed.
- `go vet ./...` clean; `go test ./...` ok (run by `scripts/build.sh` on this commit).
- The new line, run under the live agy seat's own environment: `initialize` answered
  `agenthub 1.22.0`, `tools/list` returned the nine `agenthub_http` tools.
- Reviewer gate PASS over `516a230..82d2a62` (row `qitem-20261019050105-0008b45fd1d8`).

## Pin

This entry rides the hub pin bump `agenthub_client` → `82d2a62`.
