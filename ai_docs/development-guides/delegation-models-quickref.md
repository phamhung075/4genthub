# Delegation Models Quick Reference

## When to Use Which Tool

### Decision Tree

```
┌──────────────────────────────────────────┐
│ Need to delegate work to an agent?      │
└──────────────┬───────────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ How many subtasks?   │
    └─────┬────────────┬───┘
          │            │
      ONE │            │ MULTIPLE
          │            │
          ▼            ▼
    ┌─────────┐  ┌─────────────┐
    │ Need    │  │ Need live   │
    │ results?│  │ progress?   │
    └──┬──┬───┘  └──┬──────┬───┘
       │  │         │      │
      YES NO       YES     NO
       │  │         │      │
       ▼  ▼         ▼      ▼
    [WAIT] [ASYNC] [PARALLEL] [ASYNC]
```

### Quick Selection

| Scenario | Tool | Command |
|----------|------|---------|
| **Single subtask, need results** | cclaude-wait | `cclaude-wait agent "subtask_id: xxx, task_id: yyy"` |
| **Single subtask, fire-and-forget** | cclaude | `cclaude agent "subtask_id: xxx, task_id: yyy"` |
| **Multiple subtasks, see live progress** | cclaude-wait-parallel | `cclaude-wait-parallel agent task_id sub1 sub2 sub3` |
| **Multiple subtasks, fire-and-forget** | cclaude (multiple) | `cclaude agent "sub1" & cclaude agent "sub2" &` |
| **Token efficiency, sequential work** | Agent switching | `call_agent("specialized-agent")` |

## Detailed Comparison

### 1. Agent Switching (call_agent)

```python
# Example
mcp__agenthub_http__call_agent("coding-agent")
# Do work directly in this session
# Switch back: call_agent("master-orchestrator-agent")
```

**When to use:**
- ✅ Token efficiency is critical (~1,200 tokens vs ~20k per delegation)
- ✅ Sequential workflow (one step after another)
- ✅ Simple tasks that can be done in current session
- ✅ Production automation scripts

**When NOT to use:**
- ❌ Need separate visible terminal windows
- ❌ Need true parallel execution
- ❌ Want to monitor multiple agents simultaneously

**Characteristics:**
- **Token cost**: ~1,200 tokens (70% savings)
- **Execution**: Sequential only
- **Visibility**: Same session (no separate terminal)
- **Results**: Immediate (work done directly)
- **Parallel**: No (sequential by design)

### 2. cclaude (Async Delegation)

```bash
# Example
cclaude documentation-agent "subtask_id: abc-123, task_id: xyz-456" &
cclaude coding-agent "subtask_id: def-789, task_id: xyz-456" &
# Continue immediately, don't wait for results
```

**When to use:**
- ✅ Fire-and-forget delegation
- ✅ Want visible terminal windows for monitoring
- ✅ Parallel execution (multiple agents working simultaneously)
- ✅ Don't need results in current session

**When NOT to use:**
- ❌ Need to use results in current session
- ❌ Need to wait for completion before continuing
- ❌ Want aggregated live progress display

**Characteristics:**
- **Token cost**: ~20k per agent
- **Execution**: Parallel (true concurrency)
- **Visibility**: Separate terminal per agent
- **Results**: None (fire-and-forget)
- **Parallel**: Yes (unlimited)
- **Blocking**: No

### 3. cclaude-wait (Sync Delegation - Single)

```bash
# Example
RESULT=$(cclaude-wait documentation-agent "subtask_id: abc-123, task_id: xyz-456")
echo "$RESULT" | jq '.completion_summary'
```

**When to use:**
- ✅ Single subtask delegation
- ✅ Need results in current session
- ✅ Want to see live progress (25% → 50% → 75% → 100%)
- ✅ Sequential workflow (wait for one before starting next)
- ✅ Result-dependent logic

**When NOT to use:**
- ❌ Multiple subtasks that should run in parallel
- ❌ Fire-and-forget scenarios

**Characteristics:**
- **Token cost**: ~20k per agent
- **Execution**: Sequential (blocks until complete)
- **Visibility**: Separate terminal + live progress in orchestrator
- **Results**: JSON (complete data)
- **Parallel**: No (designed for single subtask)
- **Blocking**: Yes

**Live Progress Example:**
```
📊 Progress Updates
⏳ 25% - Reading file...
⏳ 50% - Parsing data...
⏳ 75% - Writing results...
✅ 100% - Completed!

{
  "success": true,
  "status": "done",
  "completion_summary": "Successfully processed file..."
}
```

### 4. cclaude-wait-parallel (Sync Delegation - Multiple)

```bash
# Example
cclaude-wait-parallel documentation-agent \
    task-id \
    subtask1-id \
    subtask2-id \
    subtask3-id
```

**When to use:**
- ✅ Multiple subtasks that should run in parallel
- ✅ Want to see live progress for ALL subtasks
- ✅ Need aggregated results when all complete
- ✅ Replicate Task tool's parallel execution behavior
- ✅ Time-sensitive workflows (67% time savings vs sequential)

**When NOT to use:**
- ❌ Single subtask (use cclaude-wait instead)
- ❌ Fire-and-forget (use cclaude async instead)
- ❌ Extremely token-constrained (use agent switching)

**Characteristics:**
- **Token cost**: ~20k per agent (~60k for 3 subtasks)
- **Execution**: Parallel (all start simultaneously)
- **Visibility**: Separate terminals + aggregated live progress table
- **Results**: JSON (aggregated data for all subtasks)
- **Parallel**: Yes (designed for multiple subtasks)
- **Blocking**: Yes (waits for ALL to complete)

**Live Progress Example:**
```
📊 Parallel Subtask Progress
┌───┬────────┬──────────────┬───────────────────────────┬──────────────────────┐
│ # │ Status │ Subtask ID   │ Progress                  │ Title                │
├───┼────────┼──────────────┼───────────────────────────┼──────────────────────┤
│ 1 │ ⏳     │ e4875c20...  │ ████████████░░░░░░░░ 50%  │ Increment file 1     │
│ 2 │ ⏳     │ 3f401e57...  │ ████████████████░░░░ 75%  │ Increment file 2     │
│ 3 │ ✅     │ 41e56603...  │ ████████████████████ 100% │ Increment file 3     │
└───┴────────┴──────────────┴───────────────────────────┴──────────────────────┘

{
  "success": true,
  "subtask_count": 3,
  "completed_count": 3,
  "subtasks": [...]
}
```

## Performance Comparison

### Time Performance

```
Scenario: 3 subtasks @ 60 seconds each
─────────────────────────────────────

Agent Switching (Sequential):
├─ Subtask 1: 60s
├─ Subtask 2: 60s
└─ Subtask 3: 60s
Total: 180 seconds

cclaude-wait (Sequential):
├─ Subtask 1: 60s (separate terminal)
├─ Subtask 2: 60s (separate terminal)
└─ Subtask 3: 60s (separate terminal)
Total: 180 seconds

cclaude (Parallel, async):
├─ Subtask 1: 60s ┐
├─ Subtask 2: 60s ├─ All running simultaneously
└─ Subtask 3: 60s ┘
Total: 60 seconds (67% faster!)
No live progress aggregation in orchestrator

cclaude-wait-parallel (Parallel, sync):
├─ Subtask 1: 60s ┐
├─ Subtask 2: 60s ├─ All running simultaneously
└─ Subtask 3: 60s ┘
Total: 60 seconds (67% faster!)
WITH live progress aggregation in orchestrator
```

### Token Performance

```
Scenario: 3 subtasks
────────────────────

Agent Switching: ~1,200 tokens total (70% savings)
  ├─ call_agent("agent"): ~400 tokens
  ├─ Work in session: 0 tokens (direct execution)
  └─ Switch back: ~400 tokens

cclaude (async): ~60,000 tokens total
  ├─ Subtask 1: ~20,000 tokens
  ├─ Subtask 2: ~20,000 tokens
  └─ Subtask 3: ~20,000 tokens

cclaude-wait: ~60,000 tokens total
  └─ Same as cclaude (async)

cclaude-wait-parallel: ~60,000 tokens total
  └─ Same as cclaude but with live progress aggregation
```

## Use Case Matrix

| Use Case | Best Tool | Why |
|----------|-----------|-----|
| **Refactor single file** | Agent switching | Token efficient, sequential work |
| **Process 10 files independently** | cclaude-wait-parallel | Parallel execution, live progress |
| **Run test suites (unit, integration, e2e)** | cclaude-wait-parallel | Parallel, need results |
| **Deploy to staging, wait for health check** | cclaude-wait | Sequential, need results |
| **Trigger 5 deployments, don't wait** | cclaude (async) | Fire-and-forget, parallel |
| **Generate docs after code change** | Agent switching | Sequential, token efficient |
| **Update frontend + backend + docs** | cclaude-wait-parallel | Parallel, see progress |
| **Simple bug fix** | Agent switching | Token efficient |
| **Complex bug requiring specialized agent** | cclaude-wait | See progress, get results |

## Architecture Patterns

### Pattern 1: Sequential Pipeline
```bash
# Use agent switching for token efficiency
call_agent("coding-agent")
# Write code
call_agent("test-orchestrator-agent")
# Run tests
call_agent("documentation-agent")
# Update docs
call_agent("master-orchestrator-agent")
# Review
```

### Pattern 2: Parallel Fan-Out
```bash
# Use cclaude-wait-parallel for parallel execution + visibility
cclaude-wait-parallel coding-agent "$TASK_ID" \
    "$FRONTEND_SUBTASK" \
    "$BACKEND_SUBTASK" \
    "$DOCS_SUBTASK"
# All complete → continue with integration
```

### Pattern 3: Fire-and-Forget
```bash
# Use cclaude async for background work
cclaude documentation-agent "task_id: $DOCS_TASK" &
cclaude deployment-agent "task_id: $DEPLOY_TASK" &
# Continue immediately, monitor via MCP
```

### Pattern 4: Hybrid Approach
```bash
# Parallel execution where needed, sequential for dependencies
call_agent("master-orchestrator-agent")
# Create MCP tasks

# Phase 1: Parallel implementation
cclaude-wait-parallel coding-agent "$TASK_ID" \
    "$COMPONENT_A" "$COMPONENT_B" "$COMPONENT_C"

# Phase 2: Sequential integration (requires Phase 1 results)
call_agent("coding-agent")
# Integrate components

# Phase 3: Parallel testing
cclaude-wait-parallel test-orchestrator-agent "$TASK_ID" \
    "$UNIT_TESTS" "$INTEGRATION_TESTS" "$E2E_TESTS"

call_agent("master-orchestrator-agent")
# Final review
```

## Technical Considerations

### Resource Limits

| Tool | Max Parallel | Memory Impact | Terminal Windows |
|------|-------------|---------------|------------------|
| Agent switching | 1 (sequential) | Low (same session) | 0 |
| cclaude | Unlimited* | High (N sessions) | N |
| cclaude-wait | 1 | Medium (1 session) | 1 |
| cclaude-wait-parallel | Unlimited* | High (N sessions) | N |

*Practical limit: System resources (CPU, RAM, terminal capacity)

### Network Considerations

| Tool | WebSocket Connections | API Calls |
|------|----------------------|-----------|
| Agent switching | 0 | call_agent only |
| cclaude | 0 | Task creation |
| cclaude-wait | 1 per subtask | Task creation + polling |
| cclaude-wait-parallel | 1 total (shared) | Task creation + multiplexed polling |

### Error Recovery

| Tool | Error Handling | Retry Capability |
|------|----------------|------------------|
| Agent switching | Immediate | Manual |
| cclaude | None (fire-and-forget) | Manual via MCP |
| cclaude-wait | JSON error in results | Manual |
| cclaude-wait-parallel | Partial results + error details | Manual |

## Best Practices

### 1. Start with Agent Switching
```bash
# Default to token-efficient approach
call_agent("specialized-agent")
# Only escalate to delegation if:
# - Need separate terminal visibility
# - Need true parallel execution
# - Task too complex for single session
```

### 2. Use cclaude-wait-parallel for Time-Sensitive Work
```bash
# When time matters more than tokens
cclaude-wait-parallel agent task \
    subtask1 subtask2 subtask3
# 67% time savings vs sequential
```

### 3. Combine Approaches for Complex Workflows
```bash
# Orchestrator planning (token efficient)
call_agent("master-orchestrator-agent")

# Parallel implementation (time efficient)
cclaude-wait-parallel coding-agent task sub1 sub2 sub3

# Sequential review (token efficient)
call_agent("code-reviewer-agent")
```

### 4. Monitor Resource Usage
```bash
# Check terminal count
tmux list-sessions | wc -l

# Check memory usage
ps aux | grep cclaude | wc -l

# Limit parallel execution if needed
MAX_PARALLEL=5
if [ $(jobs -r | wc -l) -ge $MAX_PARALLEL ]; then
    wait  # Wait for some to complete
fi
```

## Troubleshooting

### Problem: Too many terminal windows
**Solution**: Use agent switching for sequential work, reserve cclaude-wait-parallel for truly parallel tasks

### Problem: High token costs
**Solution**: Prefer agent switching (~1,200 tokens) over delegation (~20k tokens per agent)

### Problem: Need both parallel execution AND token efficiency
**Solution**: No perfect solution - choose based on priority:
- Time-critical → cclaude-wait-parallel
- Token-critical → Agent switching (sequential)

### Problem: WebSocket connection issues
**Solution**: Check MCP server running, verify `MCP_API_TOKEN` set, ensure WebSocket endpoint accessible

## References

- **Agent Switching**: CLAUDE.md → "Agent Switching Model"
- **cclaude**: `.claude/bin/cclaude`
- **cclaude-wait**: `.claude/bin/cclaude-wait`
- **cclaude-wait-parallel**: `.claude/bin/cclaude-wait-parallel`
- **Architecture Guide**: `ai_docs/development-guides/parallel-execution-architecture.md`
- **Parallel Guide**: `ai_docs/development-guides/cclaude-wait-parallel-guide.md`
