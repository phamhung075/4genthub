# MCP Hint System Implementation Guide

## Overview
The MCP Hint System provides contextual reminders and guidance for AI agents after MCP operations complete. It tracks operation results, generates appropriate hints, and maintains comprehensive logs for debugging and monitoring.

## Architecture

### Components

#### 1. Post-Action Hint Generator (`mcp_post_action_hints.py`)
- Generates contextual hints based on tool, action, and result
- Only provides hints for successful operations
- Tracks task patterns and provides intelligent reminders

#### 2. Hint Bridge System (`hint_bridge.py`)
- Stores hints between operations
- Maintains a 5-minute relevance window
- Marks hints as displayed to avoid repetition

#### 3. Display Formatter (`post_action_display.py`)
- Formats hints for proper display in Claude's interface
- **RESOLVED**: Uses `<system-reminder>` format (Claude recognizes this)
- **FIXED**: Removed custom `<post-action-hook>` tags that caused display issues
- JSON and plain text fallbacks available but system-reminder is primary

#### 4. Hook Integration
- **post_tool_use.py**: Generates and stores hints after operations
- **pre_tool_use.py**: Retrieves and displays pending hints

## Logging System

### Files Generated

#### `mcp_post_hints_detailed.json`
Complete operation details including:
- Timestamp
- Tool name and action
- Input parameters summary
- Generated hint text
- Storage and display status

Example entry:
```json
{
  "timestamp": "2025-09-12T11:57:48.285737",
  "tool_name": "mcp__dhafnck_mcp_http__manage_task",
  "action": "update",
  "tool_input_summary": {
    "task_id": "52852bee-5c5a-4167-9a12-199080523caa",
    "status": "in_progress"
  },
  "hint_generated": "📊 TASK UPDATED - REMINDERS:\n⏰ REMINDER: Continue updating every 25% progress",
  "hint_stored": true,
  "hint_displayed": true
}
```

#### `mcp_post_hints.log`
Simple text log with timestamp and hint preview:
```
2025-09-12T11:57:48.286061 - mcp__dhafnck_mcp_http__manage_task:update - Hint: 📊 TASK UPDATED - REMINDERS...
```

#### `pending_hints.json`
Bridge storage for hints awaiting display:
```json
{
  "message": "<system-reminder>\n📊 TASK UPDATED...\n</system-reminder>",
  "from_tool": "mcp__dhafnck_mcp_http__manage_task",
  "from_action": "update",
  "created_at": "2025-09-12T11:57:48.285361",
  "displayed": false
}
```

**RESOLVED DISPLAY ISSUES**:
- Fixed unwanted `</post-action-hook>` closing tags appearing in interface
- Changed from custom `<post-action-hook>` to standard `<system-reminder>` format
- All hints now display properly in Claude's interface

## Hint Categories

### Task Management
- **Create**: Delegation reminders, subtask suggestions
- **Update**: Progress tracking, continue updating every 25%
- **Complete**: Context update reminders, next task selection
- **Get/List**: Review and planning suggestions

### Agent Operations
- **call_agent**: One-time load warning, workflow reminders
- **assign_agent**: Agent capability reminders

### Context Operations
- **Update**: Level-specific impact information
- **Add Insight**: Knowledge sharing encouragement

## Key Features

### Success/Failure Detection
```python
if result and isinstance(result, dict):
    is_success = result.get('success', True)
    if not is_success:
        # Don't provide hints for failed operations
        return None
```

### Pattern Detection
- Tracks tasks completed without updates
- Detects time since last update
- Identifies complex tasks needing decomposition

### Workflow State Tracking
- Maintains task lifecycle state
- Tracks delegation status
- Monitors update frequency

## Usage Patterns

### Successful Operation Flow
1. MCP operation completes successfully
2. post_tool_use hook generates contextual hints
3. Hints are stored in bridge and logs
4. Next tool use retrieves pending hints
5. Hints marked as displayed

### Failed Operation Flow
1. MCP operation fails
2. No hints generated (by design)
3. Error logged separately
4. User handles error without hint interference

## Configuration

### Environment Variables (.env.claude)
**RESOLVED**: System now respects `.env.claude` configuration:
- `AI_DATA`: Data directory path (default: `.claude/data`)
- `AI_DOCS`: Documentation directory (default: `ai_docs`) 
- `LOG_PATH`: Log directory path (default: `logs`)

**DATA CONSOLIDATION COMPLETED**:
- All data properly organized per .env.claude settings
- No more scattered data across multiple folders
- Migration script consolidated all existing data

### File Permissions
```bash
chmod +x .claude/hooks/post_tool_use.py
chmod +x .claude/hooks/pre_tool_use.py
```

## Best Practices

### For Developers
1. Always check operation success before hint generation
2. Keep hints concise and actionable
3. Log both summary and detailed information
4. Use emoji indicators for quick scanning

### For AI Agents
1. Hints appear after successful operations
2. Follow suggested next steps
3. Update tasks regularly (every 25% progress)
4. Complete tasks with summaries

## Troubleshooting

### Hints Not Appearing
1. Check `mcp_post_hints_detailed.json` for generation
2. Verify `pending_hints.json` for storage
3. Ensure hooks are executable
4. Check operation was successful

### Log Files Growing
- Logs auto-trim to last 100 entries
- Old hints cleared after 10 minutes
- Manual cleanup: Delete JSON files in logs/

## Future Enhancements

### Potential Improvements
1. Custom hint templates per project
2. ML-based hint relevance scoring
3. User preference learning
4. Cross-session hint persistence
5. Visual hint display in UI

### Integration Opportunities
1. VS Code extension integration
2. Web dashboard for hint analytics
3. Team hint sharing
4. Hint effectiveness metrics

## Testing

### Manual Test
```python
# Trigger a task creation
mcp__dhafnck_mcp_http__manage_task(
    action="create",
    title="Test task",
    git_branch_id="valid-uuid",
    assignees="@coding-agent"
)

# Check logs
cat logs/mcp_post_hints_detailed.json
cat .claude/hooks/data/pending_hints.json
```

### Verify Logging
```bash
# Check detailed log exists and is valid JSON
python -m json.tool logs/mcp_post_hints_detailed.json

# Check hints are being stored
ls -la .claude/hooks/data/pending_hints.json
```

## Recent Resolutions (2025-09-12)

### Issues Resolved
1. **Import Error Fixed**: 
   - Resolved "attempted relative import beyond top-level package"
   - Renamed conflicting modules with `_clean_arch` suffix
   
2. **Display Tag Issue Fixed**:
   - **Problem**: Custom `<post-action-hook>` tags showing unwanted closing tags
   - **Solution**: Changed to use `<system-reminder>` format that Claude recognizes
   - **Result**: Hints now display properly without unwanted tags

3. **Data Consolidation Completed**:
   - All scattered data consolidated per `.env.claude` configuration
   - Proper directory structure established
   - Migration script successfully moved all existing data

4. **SOLID Architecture Implemented**:
   - Hook system refactored following clean architecture principles
   - Modular components with single responsibilities
   - Easy to extend and maintain

### Claude Interface Tags
- `<session-start-hook>`: System-generated by Claude Code (don't modify)
- `<system-reminder>`: Standard format for hint display (working correctly)
- Custom tags: Avoided - use standard formats only

## Summary

The MCP Hint System successfully:
- ✅ Generates contextual hints after operations
- ✅ Detects success/failure and acts accordingly  
- ✅ Maintains comprehensive audit logs
- ✅ Provides bridge mechanism for hint display
- ✅ Tracks workflow patterns for intelligent guidance
- ✅ **DISPLAYS PROPERLY** in Claude's interface using `<system-reminder>` format
- ✅ **RESPECTS** .env.claude configuration for data organization
- ✅ **FOLLOWS** SOLID principles for maintainable architecture

The system is now fully functional with proper display integration and clean architecture.