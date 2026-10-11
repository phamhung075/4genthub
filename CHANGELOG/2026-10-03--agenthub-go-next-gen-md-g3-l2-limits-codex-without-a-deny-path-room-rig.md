### Changed

**`NEXT_GEN.md` records the G3 architect findings** (2026-10-03)

- `agenthub_go/NEXT_GEN.md` G3: L2 limits, codex without a deny path, room = rig identity rule, seatcheck install decision; owner decisions pending. Documentation only, no tests run.

**One list of seat runtimes** (2026-10-03)

- `seat_management/domain/resolver/runtime.go`: `RuntimeClaudeCode`, `RuntimeCodex` and `CheckRuntime`, the single definition of the runtimes the renderer can render. `repositories.ValidateRuntime` (API, MCP `manage_seat`, seat-type versions), `rigspec`, `seedlibrary`, `seedmap` and `seatrenderer` all read it; the four separate lists are gone. A runtime such as `pi` or `omp` is a 400 `unsupported runtime "pi": supported runtimes are "claude-code" and "codex"` on `PUT .../occupant`, `POST .../seats` and `POST /seat-types/{slug}/versions`.
