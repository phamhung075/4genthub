# 💻 CODE AGENT SCRIPT - Task Workflow Schema
you must correct probleme on  dhafnck_mcp_main/docs/architecture/working/RCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V7.md
## Workflow Steps

- **Step 1: Initialize** - Load @coding_agent and verify MCP tool permissions
- **Step 2: GetNextTask** - Retrieve next task  on dhafnck_mcp_main/docs/architecture/working/ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V7.md
- **Step 3: MarkInProgress** - Update task status to "in_progress" 
- **Step 4: ReadContext** - Load branch and task context for current state
- **Step 5: ExecuteWork** - Process task based on type (read files, apply fixes, validate)
- **Step 6: UpdateContext** - Save progress to branch context (files modified, changes applied)
- **Step 7: ValidateChanges** - Check files exist, no syntax errors, tests pass
- **Step 8: CompleteTask** - Mark task complete with summary and testing notes
- **Step 9: CheckForMore** - Look for additional tasks assigned to agent on dhafnck_mcp_main/docs/architecture/working/ARCHITECTURE_COMPLIANCE_REPORT_2025-08-28_V7.md
- **Step 10: Loop** - Return to Step 2 if tasks available, else exit

## State Transitions

- **Pending** → In Progress (when agent picks up task)
- **In Progress** → Blocked (if dependencies or errors)
- **In Progress** → Completed (when work finished successfully)
- **Blocked** → In Progress (when blocker resolved)
- **Completed** → Final (no further transitions)

## Error Recovery

- **OnFailure** - Log error, update status to blocked, notify planner
- **Retry** - Wait 60 seconds, attempt task again (max 3 retries)
- **Escalate** - After max retries, delegate to planner agent

## Context Schema

- **BranchContext** - Progress percentage, files modified list, violations fixed count
- **TaskContext** - Start/end timestamps, duration, success boolean
- **SharedContext** - Blockers list, next steps, agent notes

## Validation Points

- **BeforeStart** - Verify agent permissions, task assignment, context access
- **DuringWork** - File accessibility, syntax validity, dependency availability  
- **BeforeComplete** - All changes applied, tests passing, lint clean
- **AfterComplete** - Context updated, summary provided, files documented

## Integration Points

- **PlannerAgent** - Receive task assignments, send completion status
- **TestAgent** - Trigger on task complete, provide modified files list
- **ContextSystem** - Update on each operation, read before task start
- **MonitoringAgent** - Report progress, errors, and blockers