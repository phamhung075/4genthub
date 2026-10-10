### Changed

**`NEXT_GEN.md` records the live verification run and open items** (2026-10-03)

- `agenthub_go/NEXT_GEN.md`: tester results (scratch rigs only), five open items and an owner action on a possibly exposed token. Documentation only, no tests run.

**gofmt** (2026-10-03)

- `agenthub_go/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/subtask_mcp_controller.go`: formatted two type-switch cases (layout only, no behavior change). `gofmt -l` over `agenthub_go` now lists nothing outside the vendored module cache `.gomodcache`.
