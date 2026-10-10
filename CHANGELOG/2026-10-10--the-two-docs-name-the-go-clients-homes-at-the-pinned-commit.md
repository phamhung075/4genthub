## The two docs name the Go client's homes at the pinned commit, not the retired Python package

### Fixed
- `README.md:137` and the three `Module` cells beneath it (`:141`-`:143`): the client is the **Go module** `agenthub_client/` built as the `4genteam` command, whose dispatch table names one package per verb (`agenthub_client/cmd/4genteam/main.go:98-106`), and the three verbs' homes are `internal/clientsync`, `internal/clientbridge` and `internal/clientteam`. It read `agenthub_client/pyproject.toml:13`, `agenthub_client/src/agenthub_client/cli.py:259-275` and the three `.py` modules.
- `README.md:149`: the no-MCP shell door runs the Go implementation `agenthub_client/internal/clientfeedback/feedback.go`, registered with the other verbs at `cmd/4genteam/main.go:105`.
- `agenthub_go/NEXT_GEN.md:57`: the two halves talk through `internal/clientsync`, `internal/clientbridge` and `internal/clientteam`.
- `agenthub_go/NEXT_GEN.md:240` and `:241`: the feedback box carries the door's citation twice, and both are repointed — the shell door is the Go implementation, and the door's flags are `feedback.go:189-199`.
- `agenthub_go/NEXT_GEN.md:415`: the `cmd_publish_skills` citation is `agenthub_client/internal/clientteam/publish.go:204`, whose port prints the same `plan: publish-skills …` line at `:222`.

### Verified
- Read at the pinned client commit `eaa6ba73608cbb24c43cc442be4353fe20e5187d` (superproject `df257e01`, the pin this change is true against): `cmd/4genteam/main.go:105` is `registry = append(registry, clientfeedback.Commands()...)`; `internal/clientfeedback/feedback.go:189-199` is the six flags `--layer`, `--text`, `--room`, `--seat`, `--session`, `--url`; the three cited packages hold **35 + 17 + 15 files**; and `git -C agenthub_client ls-tree -r --name-only eaa6ba7 | grep -cE '\.py$|pyproject\.toml'` is **0**.
- Every remaining mention of `agenthub_client/src/agenthub_client` in these two files sits inside its own dated CORRECTED clause, which keeps the retired path visible as history rather than deleting it.
- **Not run:** no test asserts these sentences. The checker the lead named for them is feedback-dev's citation check in `--diff` mode.
