## Changed

- `agenthub_client` pin moves `f5f102d` -> `46b8b6e` (1 commit), fast-forwarded so the reviewer's gated sha is the landed sha.

### Fixed

- An `agy` seat mounts the agenthub MCP server: `start_seat` installs the seat's server into agy's own `~/.gemini/config/mcp_config.json`, beside the guard hook it already installs there. The runtime writes the seat's `mcp.json` for every runtime, but that file is omp's own convention and agy's argv names no config file - measured 2026-10-15 on the agy run (hub `d143f23b`), the live agy pane carried no `agenthub_http` tools, so a seat in that runtime could not call `manage_task`, `manage_context`, `call_seat` or the queue at all.
- The entry is a command, not a URL: agy's HTTP transport would need the seat's token written into a file agy applies to every session on the machine. It reads `$AGENTHUB_URL`/`$AGENTHUB_TOKEN` at connect time, starts nothing when `AGENTHUB_SEAT` is unset, keeps the owner's own `deepseek` server entry through the merge, and is idempotent.

Validated: gated PASS by the reviewer at `46b8b6e`, driven from the artifact the code itself wrote - agy 1.4.0 parses the installed entry, the bridge answers `initialize` (agenthub 1.22.0) and `tools/list` with the nine tools as this seat, `AGENTHUB_SEAT` unset starts nothing, a dead daemon fails in 5s instead of hanging, and no token sits in agy's file. Two nits carried rather than waived: the first write re-serialises the owner's file (key order and trailing newline; idempotent after it), and the commit carries no hub-task trailer, which this pin commit names instead (`223f8b12-6ff2-43b0-9b89-7de250b69fcd`).

Deferred, not failed: the fix's live acceptance criterion - a live agy seat actually mounting the nine tools - needs the fix landed, then `rebuild+install` of the client runtime, then a reseat onto agy; the last two are the owner's acts. The failure mode to check for is silence, not an error: if agy sanitises the environment it hands the spawned server, the entry starts nothing and raises nothing, so the check is that the tools APPEAR.
