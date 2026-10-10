### Fixed

**TestToolConfigParity expected the Python tool list without manage_seat** (2026-10-03)

- `agenthub_go/fastmcp/task_management/infrastructure/configuration/testdata/tool_cases.json`: the recorded Python output has no `manage_seat`, which is an intentional Go addition (`tool_config.go:23`, env `TOOL_MANAGE_SEAT`, default enabled). The expected `enabled_tools` and `tools` maps now carry `"manage_seat": true` after `call_agent` in all 400 cases (412 occurrences). No production code changed; the rest of the Python parity is untouched.
