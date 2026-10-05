# AGENTS.md migration map (2026-10-05)

The root `AGENTS.md` was slimmed to five things: the hazard note, identity, where context lives,
the universal hard rules, and pointers. Its detail was moved into `ai_docs/` — except the sections
that described retired mechanisms, which were dropped with the reason recorded here.

This is the durable mapping: **old section → new location** (or **dropped, reason**). A reader
following the old structure finds the new home here.

## Kept in AGENTS.md

| New AGENTS.md part | What it is |
|---|---|
| HTML comment | The hazard note (OpenRig writes its own generated AGENTS.md into a rig's launch cwd; launch with the spec cwd). Kept, unchanged in substance. |
| §1 Identity first | `rig whoami --json` is ground truth; re-run after compaction/restart/restore. |
| §2 Where context lives | Pointers to the seat role files (`agents/<seat>/agent.yaml`, `guidance/role.md`), the queue (`rig queue`), and `agenthub_go/NEXT_GEN.md`. |
| §3 Hard rules | The five universal rules (condensed; detail moved — table below). |
| §4 Pointers | Links to the three `ai_docs/agent-system/` files and this map. |

## Moved

| Old AGENTS.md section | New location |
|---|---|
| `# ABSOLUTE PRIORITY: NO COMPATIBILITY CODE ALLOWED` (+ `## CRITICAL RULE: CLEAN CODE ONLY`) | [`repo-agent-rules.md`](./repo-agent-rules.md#clean-code-only--no-compatibility-no-fallbacks); condensed into AGENTS.md §3 rule 1 |
| `## TEST FIXING PRIORITY RULES` | [`repo-agent-rules.md`](./repo-agent-rules.md#test-fixing-priority-and-the-source-of-truth); condensed into AGENTS.md §3 rule 2 |
| `## CLEAN CODE PRINCIPLES` | [`repo-agent-rules.md`](./repo-agent-rules.md#clean-code-principles) |
| `## ABSOLUTE FIRST PRIORITY - KNOW WHICH SEAT YOU ARE` | [`seat-model-and-mcp-surface.md`](./seat-model-and-mcp-surface.md#the-seat-model); condensed into AGENTS.md §1 |
| `## MCP TOOL PERMISSIONS` → "Correct MCP Tool Names" list | [`seat-model-and-mcp-surface.md`](./seat-model-and-mcp-surface.md#published-mcp-tools-source-of-truth-for-tool-names) |
| `## TOOL SCOPE BY SEAT` | [`seat-model-and-mcp-surface.md`](./seat-model-and-mcp-surface.md#tool-scope-by-seat) |
| `## KNOWLEDGE MANAGEMENT` | [`seat-model-and-mcp-surface.md`](./seat-model-and-mcp-surface.md#knowledge-management) and [`repo-agent-rules.md`](./repo-agent-rules.md#docs-conventions) |
| `## TASK DUPLICATION PREVENTION` | [`task-workflow-and-reporting.md`](./task-workflow-and-reporting.md#task-duplication-prevention) |
| `## TIERED TASK WORKFLOW` (Tier 1, Tier 2) | [`task-workflow-and-reporting.md`](./task-workflow-and-reporting.md#tiered-task-workflow) |
| `## MCP TASK MANAGEMENT - PROFESSIONAL REPORTING` | [`task-workflow-and-reporting.md`](./task-workflow-and-reporting.md#reporting-pattern) |
| `## MCP SUBTASKS - GRANULAR PROGRESS` | [`task-workflow-and-reporting.md`](./task-workflow-and-reporting.md#subtasks) |
| `## PRECISE CONTEXT WITH LINE NUMBERS` | [`task-workflow-and-reporting.md`](./task-workflow-and-reporting.md#precise-context-with-line-numbers) |
| `## RECEIVING RESULTS FROM SUB-AGENTS` | [`task-workflow-and-reporting.md`](./task-workflow-and-reporting.md#receiving-results) |
| `## KEY RULES SUMMARY` (rule items) | Split between AGENTS.md §3 and the two detail files |
| Changelog, keep-out and push-approval rules (previously only in the seat role files / shared rules) | [`repo-agent-rules.md`](./repo-agent-rules.md#changelog-duties), [#keep-out-files-and-staging](./repo-agent-rules.md#keep-out-files-and-staging), [#push-approval](./repo-agent-rules.md#push-approval); condensed into AGENTS.md §3 rules 3–5 |

## Dropped

| Old AGENTS.md section | Reason |
|---|---|
| `# agenthub Agent System - CLAUDE AS ENTERPRISE EMPLOYEE` and `## YOUR PROFESSIONAL IDENTITY` ("You are Claude, a professional employee", "No YOLO Mode", "No Silent Work") | Retired framing. Roles are seats now (`rig whoami` + `manage_seat`); the enterprise-employee / role-switching model it described was replaced with the seat model (Request 14). |
| `## MCP TOOL PERMISSIONS` — the "only the principal session has MCP access; team agents have NO MCP access" model | Superseded: each seat receives its own role file at launch and reaches the agenthub MCP tools itself. Only the tool-name list was moved. |
| `## PROXY PATTERN (Tier 3 - Team Agent Config Injection)` | Retired with the sub-agent team model. The `.claude/agents/` library exists only under the uncommitted `.claude` submodule (not in the repo), and the `TeamCreate`/`subagent_type` team mechanism is retired; OpenRig seats replace sub-agent teams. |
| `## TIERED TASK WORKFLOW` Tier 3 team mechanics (`TeamCreate`, spawn, monitor, `TeamDelete`) | Same retirement. Tier 1 and Tier 2 (do the work yourself with MCP tracking) were moved; the team-spawn mechanics were not. |
| `## QUICK REFERENCE` | Superseded by the slim AGENTS.md itself (it was a summary of the legacy tier workflow). |
| `**ORM Locations:** agenthub_main/src/.../*.py` | Not dropped, but corrected: the live ORM/entity path is `agenthub_go/fastmcp/task_management/domain/entities/` (see `repo-agent-rules.md`). The Python backend is retired. |

## Hard rules — before / after

The rules were not weakened in the move. Before → after, condensed in AGENTS.md §3 with the detail
in `repo-agent-rules.md`:

**Clean code.**
- Before: `# ABSOLUTE PRIORITY: NO COMPATIBILITY CODE ALLOWED` … `**YOU MUST NEVER ADD:** - NO BACKWARD COMPATIBILITY … - NO COMPATIBILITY LAYERS` … `**Clean code > Passing tests**`.
- After (AGENTS.md §3.1): "Never add backward compatibility, legacy code, fallback mechanisms, migration helpers, deprecation warnings, version checks or compatibility layers. … **Clean code > passing tests.**" (full list in `repo-agent-rules.md`).

**ORM over tests.**
- Before: `**TESTS ARE NOT THE SOURCE OF TRUTH!**` … `When tests fail: Check ORM model -> … -> NO: fix the code to match ORM -> YES: fix the test to match ORM.`
- After (AGENTS.md §3.2): "The entity/ORM is the source of truth, over the tests. Order: prompt input → ORM/entity model → database → tests → code. … never add compatibility code to make tests pass."

**Changelog duties.**
- Before: the changelog rules lived in the seat role files / shared rules (root `AGENTS.md` did not carry them).
- After (AGENTS.md §3.3): `CHANGELOG.md` for shipped changes, `TEST-CHANGELOG.md` for test-suite changes.

**Keep-out files.**
- Before: "Keep `CLAUDE.md`, `.claude` and `agenthub_go/seatcheck` out of every commit."
- After (AGENTS.md §3.4): "`.claude/` and `agenthub_go/seatcheck` never enter a commit. Stage by explicit path; never `git add -A`." — `CLAUDE.md` dropped from the list because it was renamed to `AGENTS.md` (`f7a809dc`), which is tracked.

**Push approval.**
- Before: "The owner approves every push" (shared rules).
- After (AGENTS.md §3.5): "Never push, deploy or touch production or another rig without the owner's explicit go-ahead."
