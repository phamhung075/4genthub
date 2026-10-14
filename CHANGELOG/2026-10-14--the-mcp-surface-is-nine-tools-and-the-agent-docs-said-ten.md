# The MCP surface is nine tools, and the agent-facing docs said ten

## What was wrong
`manage_agent` was retired 2026-10-10 (`76b800b9`, with the `agents` table and the 32-role registry) and
`fastmcp/server/httpapp/manage_agent_absent_test.go` fails the build if it is published again. The docs a
seat or the client's own LLM is told to read still described it as live, and five of them stated a count
that is false at HEAD.

| file | said | now says |
|---|---|---|
| `AGENTS.md:77` | "the ten published MCP tools" | "the nine published MCP tools" |
| `AGENTS.md:89-91` | "the **ten** `agenthub_http` tools (`call_seat`, `manage_agent`, …)" | the nine, with the retirement and the `@<seat_key>` identity named |
| `ai_docs/agent-system/seat-model-and-mcp-surface.md:52` | `mcp__agenthub_http__manage_agent` in the published block | removed |
| same, `:59-66` | "publishes TEN tools, and this list is the ten", with a six-entry `ToolDefinitions` decomposition | "publishes NINE", five entries, anchors re-resolved |
| same, `:71-72` | quotes the generator as "`143 routes, 10 tools`" | "`156 routes, 9 tools`" |
| `CLAUDE.local.md:159`, `.gemini/gemini.local.md:129` | MCP row: "project agents registered, assigned and rebalanced via `manage_agent`" | "9 published tools" with the seats, feedback and connection list |
| `.gemini/commands/init-local.toml:16` | THE GENERATOR: "`manage_agent` registers, assigns, updates and unregisters project agents" | the nine, as a re-derived surface, never `manage_agent` as live |
| `ai_docs/core-architecture/agenthub-system-architecture.md:58`, `:121`, `:321` | registry rows "managed through `manage_agent`"; ten tools registered; "`manage_agent` is the agent registry" | retirement named with its commit; nine registered; the row dropped |
| `ai_docs/setup-guides/complete-setup-guide.md:344-354` | §5.3 "Assign Agents to Branch" calling `manage_agent(action="register"/"assign")`, which at HEAD returns `Unknown tool` | §5.3 assigns through `manage_task(… assignees="@go-dev")`, and names the branch-level verbs that refuse and why |
| `ai_docs/operations/seat-approval-and-the-startup-call.md:71` | a per-command deny for `mcp__agenthub_http_manage_agent` | KEPT, with a note that it is inert and that dropping it is a client change, not a docs one |

The generator was fixed with the rest, because it renders two of the files above: the 2026-10-09 changelog
records that fixing the output without its generator is the error that recurs.

## The figures, re-derived at HEAD rather than decremented
`cd agenthub_go && go run ./cmd/apirefgen -out /tmp/apiref.ts` -> `156 routes, 9 tools`, and the nine
names it writes are `manage_task`, `manage_subtask`, `manage_context`, `manage_project`,
`manage_git_branch`, `manage_seat`, `call_seat`, `submit_feedback`, `manage_connection`. The
`ToolDefinitions` anchors had already SHIFTED, so they were re-resolved rather than counted down:
`ddd_compliant_mcp_tools.go:218,222,228,234,239` — five entries, not six. The four appended schemas are
`mcp_routes.go:303` (`manage_seat`), `:312` (`call_seat`), `:321` (`submit_feedback`) and `:330`
(`manage_connection`, built at `:326` by `connectionToolDefinition()`), appended by `MCPToolsList`
(`:277`). The absence is pinned, not asserted: `manage_agent_absent_test.go` fails if `tools/list`
publishes `manage_agent` or `call_agent`, and holds three landmarks so an empty registry cannot pass it.

Two sentences the draft carried were corrected by measurement instead of kept: `manage_git_branch`'s
`unassign_agent` answers `UNASSIGNMENT_FAILED: Failed to unassign agent: Agent facade not configured`
(`git_branch_application_facade.go:441`), not the assign string, and the client's `RenderConfig` is
`clientpolicy/policy.go:175` at the pinned `b1a553eb` (the `:174` earlier in that file is the `eaa6ba7`
reading, where the whole render block sits one line higher).

## Scope, and what was deliberately left alone
`CHANGELOG/**`, `mcp-tools-api-complete.md`'s already-retired sections and `surface-inventory.md`'s dated
passes (its pass 9 already carries nine) are untouched, as are the retired Python tree and `.claude/`
(keep-out). `NEXT-GEN2.md` was dirty with another seat's work and is not in this commit.

Three live-tense sites carry the same false claim and were outside the named scope; they are reported
rather than fixed quietly: `README.md` (nine occurrences, including "through the `manage_agent` MCP
tool"), `agenthub_client/docs/AGENT-SETUP.md:422` ("mounts ten tools"), and
`ai_docs/api-integration/mcp-tools-api-complete.md:20` ("publishes **ten** tools" — the row above it is
struck through, the count sentence is not).

## Evidence
`git show --numstat` on this commit: eight files, seven documents and this record. The generator run
above; `sed -n`/`read` of every cited line; `git show eaa6ba7:internal/clientpolicy/policy.go` for the
pinned-versus-old reading.
