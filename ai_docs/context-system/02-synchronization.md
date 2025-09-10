# Context Synchronization System

## Core Reality
**"AI must manually write to the notebook, but the notebook syncs to cloud automatically"**

## What's Actually Automatic vs Manual

### Manual (AI Must Do)
- Check notebook before starting work
- Write updates to notebook after work
- Track what files were modified
- Record decisions and discoveries

### Automatic (System Does)
- Sync notebook entries to cloud
- Notify other agents of changes
- Handle network failures with retry
- Resolve conflicts between agents

## Synchronization Architecture

### Overview
When AI manually writes to the context notebook (via manage_context), those writes are automatically synchronized to the cloud MCP server.

### Sync Flow
```
AI manually calls manage_context(action="update", data={...})
    ↓
System pulls latest from cloud (automatic)
    ↓
System updates local notebook (automatic)
    ↓
System pushes to cloud (automatic)
    ↓ (on network failure)
System saves to local journal (automatic)
    ↓
Background retry service (automatic)
    ↓
Eventually syncs to cloud (automatic)
```

## Synchronization Components

### 1. Mandatory Sync Wrapper
Wraps every MCP tool execution with automatic synchronization:

```python
class MandatorySyncWrapper:
    async def wrap_tool(self, tool_func):
        async def synced_execution(**params):
            # Pre-sync: Pull latest context
            await self.pre_sync(params)
            
            # Execute tool
            result = await tool_func(**params)
            
            # Post-sync: Push changes (MANDATORY)
            await self.post_sync(params, result)
            
            return result
        return synced_execution
```

### 2. Local Change Journal
Persists changes locally when sync fails:

```python
class LocalChangeJournal:
    def __init__(self, journal_dir=".context_journal"):
        self.journal_dir = Path(journal_dir)
        self.journal_dir.mkdir(exist_ok=True)
        
    async def append(self, changes: Dict[str, Any]):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "changes": changes,
            "retry_count": 0,
            "status": "pending"
        }
        
        # Append to journal file
        journal_file = self.journal_dir / f"journal_{date.today()}.jsonl"
        with open(journal_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
```

### 3. Background Retry Service
Continuously retries failed syncs with exponential backoff:

```python
class BackgroundRetryService:
    def __init__(self):
        self.retry_intervals = [1, 2, 4, 8, 16, 32, 64]  # seconds
        
    async def retry_failed_syncs(self):
        while True:
            pending = await self.journal.get_pending_entries()
            
            for entry in pending:
                retry_count = entry['retry_count']
                if retry_count < len(self.retry_intervals):
                    interval = self.retry_intervals[retry_count]
                    
                    if time_since_last_attempt(entry) > interval:
                        success = await self.attempt_sync(entry)
                        if success:
                            await self.journal.mark_synced(entry)
                        else:
                            await self.journal.increment_retry(entry)
```

### 4. Real-time WebSocket Notifications
Broadcasts changes to all connected agents:

```python
class WebSocketNotificationService:
    async def broadcast_change(self, change_event):
        notification = {
            "event": "context_changed",
            "level": change_event.level,
            "context_id": change_event.context_id,
            "changed_by": change_event.agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "change_type": change_event.type
        }
        
        for client in self.connected_clients:
            await client.send_json(notification)
```

## Fail-Safe Mechanisms

### Layer 1: Real-time Sync
- Primary synchronization path
- WebSocket connection for instant updates
- Sub-second latency

### Layer 2: Local Journal
- Activated on network failure
- Persistent local storage
- Survives process restarts

### Layer 3: Retry Queue
- Exponential backoff strategy
- Intelligent retry scheduling
- Prevents server overload

### Layer 4: Shutdown Hooks
- Last-chance sync on process exit
- Flushes pending changes
- Graceful shutdown

### Layer 5: Startup Recovery
- Checks journal on startup
- Resumes failed syncs
- Ensures continuity

## Manual Context Updates by AI

Since we cannot modify AI's built-in tools, the AI must manually track and update context:

### What AI Should Track Manually
```python
# After reading files
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "files_read": [
            "auth/config.py",
            "utils/jwt.py"
        ],
        "understanding": "Current auth uses basic JWT without refresh"
    }
)

# After modifying files  
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "files_modified": [
            "auth/jwt.py",
            "auth/refresh.py"
        ],
        "changes_made": "Added refresh token generation and validation"
    }
)

# After running tests
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "tests_run": "pytest auth/test_jwt.py",
        "test_results": "15 passed, 2 failed",
        "failures": ["test_refresh_token_expiry", "test_token_revocation"]
    }
)
```

### Helper Pattern for AI Memory
```python
# AI can maintain a local tracking dict during work
work_tracker = {
    "files_read": [],
    "files_modified": [],
    "decisions": [],
    "discoveries": [],
    "test_results": []
}

# Then update context at end
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data=work_tracker
)
```

## Sync Status Indicators

### Visual Status
```yaml
sync_status_display:
  states:
    synced:
      icon: "✅"
      threshold: "< 60 seconds"
      color: "green"
    recent:
      icon: "🟡"
      threshold: "60-300 seconds"
      color: "yellow"
    stale:
      icon: "🔴"
      threshold: "> 300 seconds"
      color: "red"
```

### Status Calculation
```python
def calculate_sync_status(last_sync_time: datetime) -> SyncStatus:
    age = (datetime.utcnow() - last_sync_time).total_seconds()
    
    if age < 60:
        return SyncStatus.SYNCED
    elif age < 300:
        return SyncStatus.RECENT
    else:
        return SyncStatus.STALE
```

## Conflict Resolution

### Strategies
1. **Merge**: Combine non-conflicting changes
2. **Version**: Keep both versions with timestamps
3. **Last-Write-Wins**: Use most recent change
4. **Manual**: Queue for human review

### Implementation
```python
class ConflictResolver:
    async def resolve(self, local: Dict, remote: Dict) -> Dict:
        strategy = self.determine_strategy(local, remote)
        
        if strategy == "merge":
            return self.deep_merge(local, remote)
        elif strategy == "version":
            return self.create_versions(local, remote)
        elif strategy == "last_write_wins":
            return self.select_newest(local, remote)
        else:
            return await self.queue_for_review(local, remote)
```

## Performance Metrics

### Target Metrics
- **Sync Latency**: <100ms for normal operations
- **Sync Success Rate**: >99.9%
- **Data Loss**: 0% with fail-safe mechanisms
- **Cache Hit Rate**: >85%
- **Conflict Rate**: <0.1%

### Monitoring
```python
class SyncMetricsCollector:
    def record_sync(self, duration: float, success: bool):
        self.metrics.append({
            "timestamp": datetime.utcnow(),
            "duration_ms": duration * 1000,
            "success": success,
            "retry_count": 0
        })
        
    def get_stats(self) -> Dict:
        return {
            "avg_latency_ms": self.calculate_avg_latency(),
            "success_rate": self.calculate_success_rate(),
            "total_syncs": len(self.metrics)
        }
```

## Best Practices

1. **Let Sync Happen Automatically**: Don't manually trigger syncs
2. **Trust the Journal**: Failed syncs will retry automatically
3. **Monitor Status Indicators**: Watch for persistent red status
4. **Handle Conflicts Gracefully**: Choose appropriate resolution strategy
5. **Keep Context Granular**: Smaller updates sync faster