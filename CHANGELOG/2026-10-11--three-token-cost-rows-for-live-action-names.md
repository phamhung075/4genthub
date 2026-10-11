## Three token-cost rows the sweep over-deleted, because their operations are still live action names

### The finding, and the premise checked rather than copied
The item-3 sweep in `5ab853d1` deleted ten token-cost rows that priced retired operations (67 -> 57, its test moved with them). Three of the ten price operations that are STILL live action names: `assign_agent` and `unassign_agent` (`fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/factories/operation_factory.go:50`, dispatched at `:97` and `:99`) and `rebalance_agents` (`project_mcp_controller/factories/operation_factory.go:44`, dispatched at `:121`).

Checked in BOTH directions before writing anything:
- The gap is real and SILENT: `GetOperationCost` (`fastmcp/auth/config/token_costs.go:88`) returns the caller's default when a key is missing, and BOTH callers pass `1` (`token_consumption_helper.go:89`, `token_consumption_service.go:55`). A missing key therefore costs 1 instead of 3, 2 and 5.
- The seven rows that stay deleted really are gone: `assign_agent_branch`, `unassign_agent_branch`, `register_agent`, `get_agent`, `list_agents`, `update_agent` and `unregister_agent` have no live action name anywhere in the Go tree, and the agent registry retired with item 3.

Latent, not live, and that too was verified rather than assumed: nothing reachable consults the table today - no controller, dispatch, route or frontend - which is why it did not hold the push.

### The change
The three rows are back where they were, with the values taken from the commit that removed them rather than invented: `{"rebalance_agents", 5}` closing the project block after `validate_integrity`, and `{"assign_agent", 3}` plus `{"unassign_agent", 2}` in the agent block between `get_subtask` and the context operations. The table holds 60 rows again.

### Tests
`token_costs_test.go`'s two length pins move 57 -> 60, and its `cases` map gains the three operations with their costs - so the file asserts the VALUES the caller reads rather than only the row count, because a count passes for a wrong restored value and these three fail.

Falsification induced and DELETED rather than asserted: with the updated test copied into a clean pre-fix worktree at `9ebb454f`, both pins fail (`TOKEN_COSTS length = 57, want 60` and `copy length = 57, want 60`); on this tree all five cases in the package pass.

### Verified
`gofmt -l` empty on both touched files; `go vet ./fastmcp/auth/config/` clean; `go build ./...` rc 0; `go test -count=1 ./fastmcp/auth/config/` ok, 5/5 cases.

### Found by
The reviewer's O3 verdict follow-up (`qitem-20261010230048`); the values and the row positions come from `5ab853d1`'s own diff rather than from memory.
