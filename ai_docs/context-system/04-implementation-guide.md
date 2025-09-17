# Context System Implementation Guide

## Overview

This guide provides technical implementation details for integrating with the 4genthub context system, including code examples, integration patterns, and troubleshooting.

## System Requirements

- Python 3.8+
- SQLite/PostgreSQL database
- Network connectivity for cloud sync
- WebSocket support for real-time updates

## Core Implementation

### Service Layer Architecture

```python
# UnifiedContextService - Core service implementation
class UnifiedContextService:
    def __init__(self):
        # Repository for data access
        self.repository = UnifiedContextRepository()
        
        # Services for specific functionality
        self.inheritance_service = ContextInheritanceService()
        self.delegation_service = ContextDelegationService()
        self.cache_service = ContextCacheService()
        
        # Sync components
        self.sync_wrapper = MandatorySyncWrapper()
        self.local_journal = LocalChangeJournal()
        self.websocket_service = WebSocketNotificationService()
    
    async def create_context(self, level: str, context_id: str, data: Dict) -> Dict:
        """Create context with automatic sync"""
        # Pre-sync: Pull latest
        await self.sync_wrapper.pre_sync(level, context_id)
        
        # Validate hierarchy
        if not await self._validate_hierarchy(level, context_id):
            raise ValidationError("Parent context must exist")
        
        # Create context
        result = await self.repository.create_context(level, context_id, data)
        
        # Post-sync: Push changes
        await self.sync_wrapper.post_sync(level, context_id, result)
        
        # Notify other agents
        await self.websocket_service.broadcast_change({
            "level": level,
            "context_id": context_id,
            "type": "created"
        })
        
        return result
```

### Repository Pattern

```python
class UnifiedContextRepository:
    def __init__(self):
        self.model_map = {
            "global": GlobalContext,
            "project": ProjectContext,
            "branch": BranchContext,
            "task": TaskContext
        }
    
    async def create_context(self, level: str, context_id: str, data: Dict) -> Dict:
        """Create context in appropriate table"""
        model_class = self.model_map.get(level)
        if not model_class:
            raise ValueError(f"Invalid context level: {level}")
        
        # Create record
        context = model_class(
            id=context_id,
            **self._prepare_data(level, data)
        )
        
        # Save to database
        async with get_db_session() as session:
            session.add(context)
            await session.commit()
            
        return context.to_dict()
```

### Inheritance Resolution

```python
class ContextInheritanceService:
    async def resolve_context(self, level: str, context_id: str) -> Dict:
        """Resolve context with full inheritance chain"""
        
        # Build inheritance path
        path = await self._build_inheritance_path(level, context_id)
        
        # Fetch contexts in path
        contexts = []
        for level_name, ctx_id in path:
            ctx = await self.repository.get_context(level_name, ctx_id)
            if ctx:
                contexts.append(ctx)
        
        # Merge contexts (most specific wins)
        resolved = {}
        for ctx in reversed(contexts):  # Start with global
            resolved = self._deep_merge(resolved, ctx.get("data", {}))
        
        return {
            "context_id": context_id,
            "level": level,
            "data": resolved,
            "inheritance_chain": [c["id"] for c in contexts]
        }
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge dictionaries with override precedence"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
```

### Automatic Context Extraction

```python
class ContextExtractor:
    """Extract context from AI actions automatically"""
    
    def __init__(self):
        self.extractors = {
            "file_edit": self.extract_from_file_edit,
            "test_run": self.extract_from_test_run,
            "command": self.extract_from_command,
            "search": self.extract_from_search
        }
    
    async def extract_context(self, action_type: str, action_data: Dict) -> Dict:
        """Extract context based on action type"""
        extractor = self.extractors.get(action_type)
        if not extractor:
            return {}
        
        return await extractor(action_data)
    
    async def extract_from_file_edit(self, data: Dict) -> Dict:
        """Extract context from file modifications"""
        return {
            "files_modified": data.get("file_paths", []),
            "change_summary": self._summarize_changes(data.get("changes", "")),
            "patterns_used": self._detect_patterns(data.get("content", ""))
        }
    
    async def extract_from_test_run(self, data: Dict) -> Dict:
        """Extract context from test execution"""
        return {
            "test_results": {
                "passed": data.get("passed", 0),
                "failed": data.get("failed", 0),
                "coverage": data.get("coverage", 0)
            },
            "failures": data.get("failure_details", [])
        }
```

### Sync Wrapper Implementation

```python
class MandatorySyncWrapper:
    """Wrap all operations with mandatory sync"""
    
    def __init__(self):
        self.sync_client = CloudSyncClient()
        self.local_journal = LocalChangeJournal()
    
    async def pre_sync(self, level: str, context_id: str):
        """Pull latest before operation"""
        try:
            latest = await self.sync_client.pull(level, context_id)
            if latest:
                await self.apply_remote_changes(latest)
        except NetworkError:
            # Continue with local data
            logger.warning("Pre-sync failed, using local data")
    
    async def post_sync(self, level: str, context_id: str, data: Dict):
        """Push changes after operation"""
        try:
            await self.sync_client.push(level, context_id, data)
        except NetworkError as e:
            # Save to journal for retry
            await self.local_journal.append({
                "level": level,
                "context_id": context_id,
                "data": data,
                "error": str(e)
            })
```

### WebSocket Integration

```python
class ContextWebSocketHandler:
    """Handle real-time context updates"""
    
    async def connect(self, websocket):
        """Handle new WebSocket connection"""
        self.clients.add(websocket)
        
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "agent_id": websocket.agent_id
        })
    
    async def handle_message(self, websocket, message):
        """Process incoming WebSocket messages"""
        msg_type = message.get("type")
        
        if msg_type == "subscribe":
            await self.subscribe_to_context(
                websocket,
                message.get("level"),
                message.get("context_id")
            )
        elif msg_type == "update":
            await self.handle_context_update(websocket, message)
    
    async def broadcast_change(self, change_event: Dict):
        """Broadcast context change to all clients"""
        for client in self.clients:
            if self.should_notify(client, change_event):
                await client.send_json({
                    "type": "context_changed",
                    **change_event
                })
```

## Integration Patterns

### Task Management Integration

```python
class TaskCompletionService:
    def __init__(self, context_service: UnifiedContextService):
        self.context_service = context_service
    
    async def complete_task(self, task_id: str, completion_summary: str):
        """Complete task with context update"""
        
        # Update task context
        await self.context_service.update_context(
            level="task",
            context_id=task_id,
            data={
                "status": "completed",
                "completion_summary": completion_summary,
                "completed_at": datetime.utcnow().isoformat()
            }
        )
        
        # Extract patterns for delegation
        patterns = await self.extract_reusable_patterns(task_id)
        if patterns:
            await self.context_service.delegate_context(
                level="task",
                context_id=task_id,
                delegate_to="project",
                delegate_data=patterns,
                delegation_reason="Reusable patterns discovered"
            )
```

### Agent Integration

```python
class AgentContextManager:
    """Manage context for AI agents"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.context_service = UnifiedContextService()
        self.extractor = ContextExtractor()
    
    async def track_action(self, action_type: str, action_data: Dict):
        """Track agent action and update context"""
        
        # Extract context from action
        context_update = await self.extractor.extract_context(
            action_type, action_data
        )
        
        # Add agent metadata
        context_update["agent_id"] = self.agent_id
        context_update["timestamp"] = datetime.utcnow().isoformat()
        
        # Update task context
        if task_id := action_data.get("task_id"):
            await self.context_service.add_progress(
                level="task",
                context_id=task_id,
                content=json.dumps(context_update),
                agent=self.agent_id
            )
```

## Database Setup

### Schema Migration

```sql
-- Run these migrations in order

-- 1. Create context tables
CREATE TABLE IF NOT EXISTS global_contexts (
    id VARCHAR(50) PRIMARY KEY,
    organization_name VARCHAR(255),
    global_settings JSON NOT NULL DEFAULT '{}',
    metadata JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_contexts (
    id VARCHAR(36) PRIMARY KEY,
    project_name VARCHAR(255),
    project_settings JSON NOT NULL DEFAULT '{}',
    metadata JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Continue for branch_contexts and task_contexts...

-- 2. Create indexes for performance
CREATE INDEX idx_branch_contexts_project ON branch_contexts(project_id);
CREATE INDEX idx_task_contexts_branch ON task_contexts(branch_id);
CREATE INDEX idx_task_contexts_updated ON task_contexts(updated_at);
```

## Error Handling

### Common Errors and Solutions

```python
class ContextErrorHandler:
    """Handle context system errors gracefully"""
    
    async def handle_error(self, error: Exception, context: Dict) -> Dict:
        """Process errors and return appropriate response"""
        
        if isinstance(error, NetworkError):
            # Network failures - use journal
            await self.local_journal.append(context)
            return {
                "success": False,
                "error": "Network error - changes saved locally",
                "will_retry": True
            }
        
        elif isinstance(error, ValidationError):
            # Validation failures - return details
            return {
                "success": False,
                "error": str(error),
                "validation_errors": error.details
            }
        
        elif isinstance(error, ConflictError):
            # Conflict - attempt resolution
            resolved = await self.conflict_resolver.resolve(
                error.local_data,
                error.remote_data
            )
            return {
                "success": True,
                "warning": "Conflict resolved",
                "resolution": resolved
            }
        
        else:
            # Unknown error - log and return generic
            logger.error(f"Unexpected error: {error}")
            return {
                "success": False,
                "error": "Internal error occurred"
            }
```

## Performance Optimization

### Caching Strategy

```python
class ContextCache:
    """High-performance context caching"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = LRUCache(maxsize=max_size)
        self.dependency_tracker = {}
    
    async def get_or_fetch(self, key: str, fetcher: Callable) -> Any:
        """Get from cache or fetch if missing"""
        
        # Check cache first
        if cached := self.cache.get(key):
            if not self._is_stale(cached):
                return cached["data"]
        
        # Fetch and cache
        data = await fetcher()
        self.cache[key] = {
            "data": data,
            "timestamp": time.time(),
            "dependencies": self._extract_dependencies(data)
        }
        
        return data
    
    def invalidate_dependents(self, changed_key: str):
        """Invalidate all contexts that depend on changed context"""
        for key, deps in self.dependency_tracker.items():
            if changed_key in deps:
                self.cache.pop(key, None)
```

## Monitoring and Debugging

### Debug Logging

```python
import logging

# Configure context system logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable debug logging for troubleshooting
logging.getLogger('context_system').setLevel(logging.DEBUG)
```

### Health Checks

```python
class ContextSystemHealth:
    """Monitor context system health"""
    
    async def check_health(self) -> Dict:
        """Comprehensive health check"""
        return {
            "database": await self._check_database(),
            "sync": await self._check_sync_status(),
            "cache": await self._check_cache_performance(),
            "journal": await self._check_journal_size()
        }
    
    async def _check_sync_status(self) -> Dict:
        """Check sync system status"""
        pending = await self.journal.count_pending()
        return {
            "status": "healthy" if pending < 100 else "degraded",
            "pending_syncs": pending,
            "last_sync": await self.get_last_sync_time()
        }
```