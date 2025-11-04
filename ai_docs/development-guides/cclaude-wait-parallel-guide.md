# cclaude-wait-parallel - Parallel Subtask Delegation Guide

## Overview

**cclaude-wait-parallel** is a solution that replicates the Task tool's parallel execution capabilities for cclaude-based delegation. It enables multiple subtasks to run simultaneously with live progress visibility in the orchestrator session.

## Problem Solved

### Original Challenge
- **Task tool**: Built-in platform feature with special parallel execution capabilities
- **cclaude-wait**: Works perfectly for single subtask but sequential for multiple
- **Claude Code limitation**: Multiple Bash tool calls execute sequentially, not in parallel
- **User requirement**: "how build in claude Task tool it working perfect? i want make my cclaude wait work like that"

### Solution Architecture
1. **cclaude-wait-parallel** (bash wrapper): Launches multiple cclaude sessions in parallel
2. **poll_mcp_websocket_parallel.py** (WebSocket multiplexer): Single connection monitors all subtasks
3. **Live progress table**: Real-time updates as events arrive from any subtask
4. **Blocking wait**: Script waits until all subtasks complete before continuing

## Usage

### Basic Syntax
```bash
cclaude-wait-parallel <agent_name> <task_id> <subtask_id1> <subtask_id2> <subtask_id3> [...]
```

### Example: 3 Parallel Subtasks
```bash
# Delegate 3 subtasks to documentation-agent in parallel
cclaude-wait-parallel documentation-agent \
    abc-123-task-uuid \
    sub1-uuid \
    sub2-uuid \
    sub3-uuid
```

### Real-World Example from Testing
```bash
# Create parent task with 3 subtasks
TASK_ID="05f925e9-5eb4-4bba-9996-f37bc2e28d6f"
SUBTASK1="e4875c20-25c6-44da-b22c-2ce166bc6a13"  # Increment .claude/incrementtt
SUBTASK2="3f401e57-a12e-424d-8028-83f91a09882e"  # Increment .claude/incrementtt1
SUBTASK3="41e56603-4aed-456a-ac85-a0b4250aa329"  # Increment .claude/incrementtt2

# Delegate all 3 in parallel
cclaude-wait-parallel documentation-agent "$TASK_ID" "$SUBTASK1" "$SUBTASK2" "$SUBTASK3"
```

## How It Works

### Step 1: Launch cclaude Sessions
```bash
# cclaude-wait-parallel launches all cclaude commands in background
for SUBTASK_ID in "$@"; do
    cclaude "$AGENT_NAME" "subtask_id: $SUBTASK_ID, task_id: $TASK_ID ..." &
    CCLAUDE_PIDS+=($!)
done
```

**Result**: All cclaude sessions start simultaneously in separate terminal windows.

### Step 2: WebSocket Multiplexer Monitors All
```python
# poll_mcp_websocket_parallel.py subscribes to all subtask events
for subtask_id in subtask_ids:
    subscribe_message = {
        "type": "subscribe",
        "scope": "subtask",
        "entity_id": subtask_id
    }
    ws.send(json.dumps(subscribe_message))
```

**Result**: Single WebSocket connection receives events from all subtasks.

### Step 3: Live Progress Display
```python
# SubtaskTracker maintains state for each subtask
class SubtaskTracker:
    subtask_id: str
    status: str  # pending → in_progress → done
    progress_percentage: int  # 0 → 25 → 50 → 75 → 100
    title: str
    is_complete: bool

# Live table updates as events arrive
with Live(create_progress_table(trackers), refresh_per_second=4):
    while not all_complete:
        message = ws.recv()
        # Update tracker, refresh display
```

**Output Example**:
```
📊 Parallel Subtask Progress
┌───┬────────┬──────────────┬───────────────────────────┬──────────────────────────┐
│ # │ Status │ Subtask ID   │ Progress                  │ Title                    │
├───┼────────┼──────────────┼───────────────────────────┼──────────────────────────┤
│ 1 │ ⏳     │ e4875c20...  │ ████████████░░░░░░░░ 50%  │ Increment incrementtt    │
│ 2 │ ⏳     │ 3f401e57...  │ ████████████████░░░░ 75%  │ Increment incrementtt1   │
│ 3 │ ✅     │ 41e56603...  │ ████████████████████ 100% │ Increment incrementtt2   │
└───┴────────┴──────────────┴───────────────────────────┴──────────────────────────┘
```

### Step 4: Wait for All Completions
```python
# Monitoring loop continues until all subtasks complete
while True:
    if all(tracker.is_complete for tracker in trackers):
        break
    # Process WebSocket events
```

### Step 5: Return Aggregated Results
```json
{
  "success": true,
  "task_id": "05f925e9-5eb4-4bba-9996-f37bc2e28d6f",
  "subtask_count": 3,
  "completed_count": 3,
  "subtasks": [
    {
      "subtask_id": "e4875c20-25c6-44da-b22c-2ce166bc6a13",
      "status": "done",
      "progress_percentage": 100,
      "title": "Increment .claude/incrementtt",
      "is_complete": true,
      "completion_data": { ... }
    },
    // ... subtask 2 and 3
  ]
}
```

## Comparison with Other Approaches

| Feature | cclaude-wait-parallel | cclaude (async) | cclaude-wait (single) | Task tool |
|---------|----------------------|-----------------|----------------------|-----------|
| Parallel execution | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| Live progress visibility | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| Aggregated progress view | ✅ Yes | ❌ No | N/A | ✅ Yes |
| Blocking wait | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| Returns results | ✅ JSON | ❌ No | ✅ JSON | ✅ Yes |
| Separate terminals | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| Token cost | ~20k per agent | ~20k per agent | ~20k per agent | Built-in |
| Best for | Task tool replacement | Fire-and-forget | Single subtask | Native feature |

## Technical Details

### File Locations
- **Wrapper script**: `.claude/bin/cclaude-wait-parallel`
- **WebSocket multiplexer**: `.claude/bin/poll_mcp_websocket_parallel.py`
- **Dependencies**: `cclaude`, `poll_mcp_websocket.py` (existing)

### Requirements
- Python 3.8+
- `websocket-client` library
- `rich` library (for display)
- `MCP_API_TOKEN` environment variable
- MCP server running at `http://localhost:8000`

### Environment Variables
```bash
# Required
export MCP_API_TOKEN="your-token-here"

# Optional
export CCLAUDE_WAIT_TIMEOUT=3600  # Default timeout (seconds)
```

### WebSocket Protocol
1. **Connect**: `ws://localhost:8000/ws/task-polling` with Bearer token auth
2. **Subscribe**: Send JSON message per subtask:
   ```json
   {
     "type": "subscribe",
     "scope": "subtask",
     "entity_id": "subtask-uuid"
   }
   ```
3. **Receive**: WebSocket broadcasts events for all subscribed subtasks:
   ```json
   {
     "subtask_id": "uuid",
     "status": "in_progress",
     "progress_percentage": 50,
     "title": "Working on it..."
   }
   ```
4. **Complete**: When `status == "done"`, track completion and wait for others

### Error Handling
- **WebSocket connection failure**: Returns JSON with `"success": false`
- **Timeout**: Configurable via `--timeout` parameter
- **Partial completion**: Returns status of all subtasks even if some fail
- **cclaude process failure**: Doesn't block monitoring (WebSocket sees final status)

## Use Cases

### 1. Parallel File Processing
```bash
# Process multiple files simultaneously
TASK_ID="parent-task-uuid"
SUBTASK1="process-file1-uuid"
SUBTASK2="process-file2-uuid"
SUBTASK3="process-file3-uuid"

cclaude-wait-parallel coding-agent "$TASK_ID" "$SUBTASK1" "$SUBTASK2" "$SUBTASK3"
```

### 2. Distributed Testing
```bash
# Run test suites in parallel
TASK_ID="test-suite-uuid"
UNIT_TESTS="unit-test-subtask-uuid"
INTEGRATION_TESTS="integration-test-subtask-uuid"
E2E_TESTS="e2e-test-subtask-uuid"

cclaude-wait-parallel test-orchestrator-agent "$TASK_ID" \
    "$UNIT_TESTS" "$INTEGRATION_TESTS" "$E2E_TESTS"
```

### 3. Multi-Component Updates
```bash
# Update frontend, backend, docs simultaneously
TASK_ID="update-all-uuid"
FRONTEND="frontend-subtask-uuid"
BACKEND="backend-subtask-uuid"
DOCS="docs-subtask-uuid"

cclaude-wait-parallel coding-agent "$TASK_ID" \
    "$FRONTEND" "$BACKEND" "$DOCS"
```

## Limitations

1. **Token Cost**: Each cclaude session costs ~20k tokens (same as regular cclaude)
2. **Terminal Dependency**: Requires separate terminal windows for each agent
3. **MCP Server Required**: Must have WebSocket server running
4. **Maximum Parallelism**: Limited by system resources and terminal capabilities
5. **No Inter-Agent Communication**: Subtasks work independently (by design)

## Advantages Over Single Bash with &

### Problem with Single Bash + &
```bash
# This approach doesn't wait or show live progress
cclaude-wait agent1 "subtask1" > /tmp/result1.json &
cclaude-wait agent2 "subtask2" > /tmp/result2.json &
cclaude-wait agent3 "subtask3" > /tmp/result3.json &
wait  # Waits but no live progress visibility
```

### cclaude-wait-parallel Solution
- ✅ Live progress table updates in orchestrator session
- ✅ See which subtasks are at 25%, 50%, 75%, 100%
- ✅ Know when each completes
- ✅ Aggregated JSON results returned to caller
- ✅ Proper error handling and timeout management

## Future Enhancements

### Planned Features
1. **Progress streaming to file**: Save progress history for post-analysis
2. **Email/Slack notifications**: Alert when all complete
3. **Dynamic subtask addition**: Add more subtasks while others running
4. **Resource management**: Limit concurrent cclaude sessions
5. **Retry failed subtasks**: Automatic retry with backoff

### Experimental Features
1. **Inter-agent messaging**: Allow subtasks to communicate via MCP context
2. **Dependency resolution**: Wait for specific subtasks before starting others
3. **Priority scheduling**: High-priority subtasks get resources first
4. **Result aggregation**: Combine subtask outputs into single deliverable

## Troubleshooting

### WebSocket Connection Fails
```bash
# Check MCP server is running
curl http://localhost:8000/health

# Verify token is set
echo $MCP_API_TOKEN
```

### No Live Progress Updates
```bash
# Check rich library installed
pip install rich websocket-client

# Verify WebSocket endpoint
curl -i -N -H "Connection: Upgrade" \
    -H "Upgrade: websocket" \
    http://localhost:8000/ws/task-polling
```

### Timeout Issues
```bash
# Increase timeout
export CCLAUDE_WAIT_TIMEOUT=7200  # 2 hours

# Or pass explicitly
cclaude-wait-parallel --timeout=7200 agent task sub1 sub2 sub3
```

### Subtasks Not Completing
1. Check separate terminal windows (cclaude sessions)
2. Verify agents are working (not blocked on user input)
3. Check MCP task status via API:
   ```bash
   curl http://localhost:8000/api/tasks/{task_id}/subtasks
   ```

## Credits

**Original Request**: "how build in claude Task tool it working perfect? i want make my cclaude wait work like that"

**Solution**: Implemented WebSocket multiplexer pattern to achieve Task tool's parallel execution with live progress visibility, solving Claude Code's sequential Bash execution limitation.

**Testing**: Successfully tested with 3 parallel subtasks incrementing separate counter files, demonstrating true parallel execution with live progress updates.

## References

- **cclaude**: `.claude/bin/cclaude` (base delegation script)
- **cclaude-wait**: `.claude/bin/cclaude-wait` (single subtask with wait)
- **poll_mcp_websocket.py**: `.claude/bin/poll_mcp_websocket.py` (WebSocket monitoring)
- **MCP Task Management**: `mcp__agenthub_http__manage_task`, `manage_subtask`
- **WebSocket API**: `ws://localhost:8000/ws/task-polling`
