# Context Update Implementation Technical Specification

**Version**: 1.0  
**Date**: February 3, 2025  
**Status**: Technical Implementation Guide  
**Scope**: 4-Tier Context Update System (Global → Project → Branch → Task)

## Executive Summary

This document provides a comprehensive technical specification for implementing safe, atomic, and intelligent context update patterns across the agenthub 4-tier context hierarchy. The specification addresses data preservation, merge strategies, agent coordination, and concurrency challenges to ensure reliable multi-session and multi-agent collaboration.

## 1. Context Update API Design

### 1.1 Update Operation Types

The system supports five distinct update operation types, each with specific merge strategies:

```typescript
enum UpdateOperation {
  REPLACE = "replace",     // Complete field replacement
  MERGE = "merge",         // Deep merge for objects
  APPEND = "append",       // Add to arrays/lists
  PREPEND = "prepend",     // Add to beginning of arrays
  ATOMIC = "atomic"        // All-or-nothing update
}

interface UpdateRequest {
  level: "global" | "project" | "branch" | "task";
  context_id: string;
  operation: UpdateOperation;
  data: Record<string, any>;
  merge_strategy?: MergeStrategy;
  preserve_fields?: string[];
  atomic?: boolean;
  user_id?: string;
  agent_id?: string;
  timestamp?: string;
}
```

### 1.2 Merge Strategy Configuration

```typescript
interface MergeStrategy {
  // Field-specific strategies
  field_strategies: Record<string, FieldUpdateStrategy>;
  
  // Default behavior for unknown fields
  default_strategy: "merge" | "replace" | "preserve";
  
  // Array handling
  array_strategy: "append" | "replace" | "unique_append" | "merge_by_key";
  
  // Conflict resolution
  conflict_resolution: "latest_wins" | "agent_priority" | "manual" | "merge_intelligent";
  
  // Validation rules
  validation_rules: ValidationRule[];
}

interface FieldUpdateStrategy {
  operation: UpdateOperation;
  preserve_existing?: boolean;
  merge_key?: string; // For array merging by key
  validation?: string; // Validation function name
}
```

### 1.3 Level-Specific Field Configurations

```python
# Global Context Fields (User-Scoped)
GLOBAL_FIELD_STRATEGIES = {
    "organization_name": {"operation": "replace", "preserve_existing": True},
    "global_settings": {"operation": "merge"},
    "user_preferences": {"operation": "merge"},
    "agent_configurations": {"operation": "merge"},
    "metadata": {"operation": "merge"}
}

# Project Context Fields
PROJECT_FIELD_STRATEGIES = {
    "project_name": {"operation": "replace", "preserve_existing": True},
    "team_preferences": {"operation": "merge"},
    "technology_stack": {"operation": "merge"},
    "project_workflow": {"operation": "merge"},
    "local_standards": {"operation": "merge"},
    "metadata": {"operation": "merge"}
}

# Branch Context Fields
BRANCH_FIELD_STRATEGIES = {
    "git_branch_name": {"operation": "replace", "preserve_existing": True},
    "branch_settings": {"operation": "merge"},
    "branch_progress": {"operation": "append", "merge_key": "timestamp"},
    "agent_assignments": {"operation": "unique_append", "merge_key": "agent_id"},
    "metadata": {"operation": "merge"}
}

# Task Context Fields
TASK_FIELD_STRATEGIES = {
    "task_data": {"operation": "merge"},
    "progress": {"operation": "replace"},
    "insights": {"operation": "unique_append", "merge_key": "id"},
    "next_steps": {"operation": "replace"},  # Always replace with latest
    "work_history": {"operation": "append", "merge_key": "timestamp"},
    "blockers": {"operation": "unique_append", "merge_key": "issue_id"},
    "metadata": {"operation": "merge"}
}
```

## 2. Agent Context Update Workflow

### 2.1 Safe Update Process (Step-by-Step)

```python
class SafeContextUpdateWorkflow:
    """Step-by-step process for agents to safely update context."""
    
    async def execute_safe_update(
        self,
        level: str,
        context_id: str,
        update_data: Dict[str, Any],
        agent_id: str,
        user_id: str
    ) -> UpdateResult:
        """
        Execute a safe context update following the 7-step process:
        1. Validate input and permissions
        2. Read existing context with optimistic locking
        3. Apply merge strategies 
        4. Validate merged result
        5. Atomic commit with conflict detection
        6. Propagate changes to child contexts
        7. Invalidate caches and notify agents
        """
        
        # Step 1: Validate Input and Permissions
        validation_result = await self._validate_update_request(
            level, context_id, update_data, agent_id, user_id
        )
        if not validation_result.valid:
            return UpdateResult.error(validation_result.errors)
        
        # Step 2: Read with Optimistic Locking
        lock_token = str(uuid.uuid4())
        existing_context = await self._read_with_lock(
            level, context_id, lock_token, user_id
        )
        if not existing_context:
            return UpdateResult.error("Context not found or locked by another agent")
        
        try:
            # Step 3: Apply Merge Strategies
            merged_data = await self._apply_merge_strategies(
                level=level,
                existing_data=existing_context.data,
                update_data=update_data,
                agent_id=agent_id
            )
            
            # Step 4: Validate Merged Result  
            validation_result = await self._validate_merged_data(
                level, merged_data, existing_context
            )
            if not validation_result.valid:
                return UpdateResult.error(validation_result.errors)
            
            # Step 5: Atomic Commit with Conflict Detection
            commit_result = await self._atomic_commit(
                level=level,
                context_id=context_id, 
                merged_data=merged_data,
                lock_token=lock_token,
                expected_version=existing_context.version,
                agent_id=agent_id,
                user_id=user_id
            )
            
            if not commit_result.success:
                if commit_result.conflict:
                    # Retry with exponential backoff
                    return await self._retry_with_backoff(
                        level, context_id, update_data, agent_id, user_id
                    )
                return UpdateResult.error(commit_result.error)
            
            # Step 6: Propagate Changes to Child Contexts
            await self._propagate_changes(
                level=level,
                context_id=context_id,
                changes=update_data,
                agent_id=agent_id,
                user_id=user_id
            )
            
            # Step 7: Cache Invalidation and Notifications
            await self._invalidate_and_notify(
                level=level,
                context_id=context_id,
                changes=update_data,
                agent_id=agent_id,
                user_id=user_id
            )
            
            return UpdateResult.success(commit_result.updated_context)
            
        finally:
            # Always release lock
            await self._release_lock(level, context_id, lock_token)
    
    async def _validate_update_request(
        self, 
        level: str, 
        context_id: str, 
        data: Dict[str, Any],
        agent_id: str,
        user_id: str
    ) -> ValidationResult:
        """Validate update request before processing."""
        errors = []
        
        # Validate level
        if level not in ["global", "project", "branch", "task"]:
            errors.append(f"Invalid level: {level}")
        
        # Validate context_id format
        if not self._is_valid_uuid(context_id) and not (level == "global" and context_id == "global"):
            errors.append(f"Invalid context_id format: {context_id}")
        
        # Check user permissions
        if not await self._check_user_permissions(user_id, level, context_id):
            errors.append("User does not have permission to update this context")
        
        # Check agent permissions  
        if not await self._check_agent_permissions(agent_id, level, context_id):
            errors.append("Agent does not have permission to update this context")
        
        # Validate data structure
        schema_errors = await self._validate_data_schema(level, data)
        errors.extend(schema_errors)
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
```

### 2.2 Merge Strategy Implementation

```python
class IntelligentMergeEngine:
    """Intelligent context data merging with conflict resolution."""
    
    def __init__(self):
        self.field_strategies = self._load_field_strategies()
        self.conflict_resolver = ConflictResolver()
    
    async def apply_merge_strategies(
        self,
        level: str,
        existing_data: Dict[str, Any],
        update_data: Dict[str, Any],
        agent_id: str
    ) -> MergeResult:
        """Apply intelligent merge strategies based on field types and level."""
        
        merged_data = existing_data.copy()
        conflicts = []
        changes = []
        
        level_strategies = self.field_strategies.get(level, {})
        
        for field_name, new_value in update_data.items():
            try:
                merge_result = await self._merge_field(
                    field_name=field_name,
                    existing_value=existing_data.get(field_name),
                    new_value=new_value,
                    strategy=level_strategies.get(field_name, DEFAULT_STRATEGY),
                    agent_id=agent_id
                )
                
                if merge_result.conflict:
                    conflicts.append(merge_result.conflict)
                    # Apply conflict resolution strategy
                    resolved_value = await self.conflict_resolver.resolve(
                        merge_result.conflict
                    )
                    merged_data[field_name] = resolved_value
                else:
                    merged_data[field_name] = merge_result.value
                
                changes.append({
                    "field": field_name,
                    "old_value": existing_data.get(field_name),
                    "new_value": merged_data[field_name],
                    "merge_strategy": merge_result.strategy_used
                })
                
            except Exception as e:
                logger.error(f"Failed to merge field {field_name}: {e}")
                conflicts.append(FieldConflict(
                    field=field_name,
                    error=str(e),
                    requires_manual_resolution=True
                ))
        
        return MergeResult(
            merged_data=merged_data,
            conflicts=conflicts,
            changes=changes
        )
    
    async def _merge_field(
        self,
        field_name: str,
        existing_value: Any,
        new_value: Any,
        strategy: FieldUpdateStrategy,
        agent_id: str
    ) -> FieldMergeResult:
        """Merge a single field based on its strategy."""
        
        if strategy.operation == UpdateOperation.REPLACE:
            return FieldMergeResult(
                value=new_value,
                strategy_used="replace",
                conflict=None
            )
        
        elif strategy.operation == UpdateOperation.MERGE:
            if isinstance(existing_value, dict) and isinstance(new_value, dict):
                merged = await self._deep_merge_dicts(existing_value, new_value)
                return FieldMergeResult(
                    value=merged,
                    strategy_used="deep_merge",
                    conflict=None
                )
            else:
                # Type mismatch - create conflict
                return FieldMergeResult(
                    value=new_value,  # Default to new value
                    strategy_used="replace_on_conflict",
                    conflict=FieldConflict(
                        field=field_name,
                        existing_type=type(existing_value).__name__,
                        new_type=type(new_value).__name__,
                        message="Type mismatch during merge operation"
                    )
                )
        
        elif strategy.operation == UpdateOperation.APPEND:
            if isinstance(existing_value, list):
                if isinstance(new_value, list):
                    merged = existing_value + new_value
                else:
                    merged = existing_value + [new_value]
                return FieldMergeResult(
                    value=merged,
                    strategy_used="append",
                    conflict=None
                )
            else:
                # Convert to list and append
                return FieldMergeResult(
                    value=[existing_value, new_value] if existing_value is not None else [new_value],
                    strategy_used="convert_and_append",
                    conflict=None
                )
        
        elif strategy.operation == UpdateOperation.UNIQUE_APPEND:
            return await self._unique_append(
                existing_value, new_value, strategy.merge_key
            )
        
        else:
            raise ValueError(f"Unknown merge strategy: {strategy.operation}")
    
    async def _deep_merge_dicts(
        self, 
        existing: Dict[str, Any], 
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recursively merge nested dictionaries."""
        result = existing.copy()
        
        for key, value in new.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = await self._deep_merge_dicts(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def _unique_append(
        self,
        existing_value: Any,
        new_value: Any,
        merge_key: Optional[str]
    ) -> FieldMergeResult:
        """Append to array only if unique based on merge key."""
        if not isinstance(existing_value, list):
            existing_value = []
        
        if isinstance(new_value, list):
            items_to_add = new_value
        else:
            items_to_add = [new_value]
        
        result = existing_value.copy()
        
        for item in items_to_add:
            if merge_key and isinstance(item, dict):
                # Check uniqueness by merge key
                item_key = item.get(merge_key)
                if not any(existing.get(merge_key) == item_key for existing in result if isinstance(existing, dict)):
                    result.append(item)
            else:
                # Simple uniqueness check
                if item not in result:
                    result.append(item)
        
        return FieldMergeResult(
            value=result,
            strategy_used="unique_append",
            conflict=None
        )
```

## 3. Data Structure Evolution

### 3.1 Schema Versioning and Migration

```python
class ContextSchemaManager:
    """Manages context schema versions and automatic migrations."""
    
    CURRENT_SCHEMA_VERSION = "2.1.0"
    
    SCHEMA_MIGRATIONS = {
        "1.0.0": {
            "2.0.0": migration_1_to_2,
            "2.1.0": migration_1_to_2_1
        },
        "2.0.0": {
            "2.1.0": migration_2_to_2_1
        }
    }
    
    async def ensure_schema_compatibility(
        self, 
        context_data: Dict[str, Any], 
        level: str
    ) -> Dict[str, Any]:
        """Ensure context data matches current schema version."""
        
        current_version = context_data.get("_schema_version", "1.0.0")
        
        if current_version == self.CURRENT_SCHEMA_VERSION:
            return context_data
        
        # Apply migrations
        migrated_data = context_data.copy()
        migration_path = self._find_migration_path(current_version, self.CURRENT_SCHEMA_VERSION)
        
        for from_version, to_version, migration_func in migration_path:
            migrated_data = await migration_func(migrated_data, level)
            migrated_data["_schema_version"] = to_version
        
        return migrated_data
    
    def _find_migration_path(self, from_version: str, to_version: str) -> List[Migration]:
        """Find the shortest migration path between schema versions."""
        # Implementation of graph-based migration path finding
        # Returns list of (from_version, to_version, migration_function) tuples
        pass

class ContextEvolutionPatterns:
    """Patterns for handling context structure evolution."""
    
    # Fields that should always be preserved during updates
    PRESERVED_FIELDS = {
        "global": ["organization_name", "_schema_version", "created_at"],
        "project": ["project_name", "project_id", "_schema_version", "created_at"],
        "branch": ["git_branch_name", "project_id", "_schema_version", "created_at"],
        "task": ["task_id", "branch_id", "_schema_version", "created_at"]
    }
    
    # Fields that should be appended to, never replaced
    APPEND_ONLY_FIELDS = {
        "global": ["user_activity_log", "system_events"],
        "project": ["team_member_history", "milestone_history"],
        "branch": ["commit_history", "merge_events", "agent_activity"],
        "task": ["work_history", "insights", "progress_snapshots"]
    }
    
    # Fields that should be merged intelligently
    MERGE_FIELDS = {
        "global": ["global_settings", "user_preferences"],
        "project": ["team_preferences", "technology_stack", "project_workflow", "local_standards"],
        "branch": ["branch_settings", "feature_flags"],
        "task": ["task_data", "metadata", "configurations"]
    }
    
    # Fields that can be replaced completely
    REPLACEABLE_FIELDS = {
        "global": ["current_focus", "active_notifications"],
        "project": ["current_sprint", "active_features"],
        "branch": ["current_status", "latest_build_info"],
        "task": ["progress", "current_assignee", "next_steps", "priority"]
    }
```

### 3.2 Nested Object Update Patterns

```python
class NestedUpdateEngine:
    """Handle complex nested object updates with path-based targeting."""
    
    async def update_nested_field(
        self,
        context_data: Dict[str, Any],
        field_path: str,
        new_value: Any,
        operation: UpdateOperation = UpdateOperation.REPLACE
    ) -> Dict[str, Any]:
        """
        Update a nested field using dot notation path.
        
        Examples:
        - "team_preferences.code_review.required" -> Sets nested boolean
        - "technology_stack.frontend.frameworks[]" -> Appends to array
        - "insights[0].confidence_score" -> Updates specific array item
        """
        
        result = context_data.copy()
        path_parts = self._parse_field_path(field_path)
        
        current_obj = result
        
        # Navigate to parent object
        for part in path_parts[:-1]:
            if part.is_array_index:
                if not isinstance(current_obj, list):
                    raise ValueError(f"Expected list at {part.path}, got {type(current_obj)}")
                current_obj = current_obj[part.index]
            elif part.is_array_append:
                if not isinstance(current_obj, list):
                    raise ValueError(f"Expected list for append at {part.path}")
                # Handle array append operations
                current_obj.append({})
                current_obj = current_obj[-1]
            else:
                if part.key not in current_obj:
                    current_obj[part.key] = {}
                current_obj = current_obj[part.key]
        
        # Apply final update
        final_part = path_parts[-1]
        if final_part.is_array_append:
            if not isinstance(current_obj, list):
                current_obj = []
            if operation == UpdateOperation.APPEND:
                current_obj.append(new_value)
            elif operation == UpdateOperation.PREPEND:
                current_obj.insert(0, new_value)
            elif operation == UpdateOperation.UNIQUE_APPEND:
                if new_value not in current_obj:
                    current_obj.append(new_value)
        else:
            current_obj[final_part.key] = new_value
        
        return result
    
    def _parse_field_path(self, path: str) -> List[PathPart]:
        """Parse dot notation path into structured parts."""
        parts = []
        segments = path.split('.')
        
        for segment in segments:
            if '[' in segment and ']' in segment:
                key = segment[:segment.index('[')]
                bracket_content = segment[segment.index('[') + 1:segment.index(']')]
                
                if bracket_content == '':
                    # Array append operation: field[]
                    parts.append(PathPart(key=key, is_array_append=True))
                else:
                    # Array index operation: field[0]
                    index = int(bracket_content)
                    parts.append(PathPart(key=key, is_array_index=True, index=index))
            else:
                parts.append(PathPart(key=segment))
        
        return parts

@dataclass
class PathPart:
    key: str
    is_array_index: bool = False
    is_array_append: bool = False
    index: Optional[int] = None
    path: str = ""
```

## 4. Implementation Examples

### 4.1 Python Backend Context Update Service

```python
class ContextUpdateService:
    """Production-ready context update service implementation."""
    
    def __init__(
        self,
        context_repository: ContextRepository,
        merge_engine: IntelligentMergeEngine,
        schema_manager: ContextSchemaManager,
        cache_service: ContextCacheService,
        notification_service: NotificationService
    ):
        self.repository = context_repository
        self.merge_engine = merge_engine
        self.schema_manager = schema_manager
        self.cache = cache_service
        self.notifications = notification_service
        self.update_lock = asyncio.Lock()
    
    async def update_context(
        self,
        request: ContextUpdateRequest,
        user_id: str,
        agent_id: Optional[str] = None
    ) -> ContextUpdateResponse:
        """Main entry point for context updates."""
        
        async with self.update_lock:
            try:
                # Step 1: Validate request
                validation = await self._validate_request(request, user_id)
                if not validation.valid:
                    return ContextUpdateResponse.error(validation.errors)
                
                # Step 2: Read current context with version check
                current_context = await self.repository.get_with_version(
                    level=request.level,
                    context_id=request.context_id,
                    user_id=user_id
                )
                
                if not current_context:
                    return ContextUpdateResponse.error("Context not found")
                
                # Step 3: Schema compatibility check
                compatible_data = await self.schema_manager.ensure_schema_compatibility(
                    current_context.data, request.level
                )
                
                # Step 4: Apply merge strategies
                merge_result = await self.merge_engine.apply_merge_strategies(
                    level=request.level,
                    existing_data=compatible_data,
                    update_data=request.data,
                    agent_id=agent_id or "system"
                )
                
                if merge_result.conflicts:
                    # Handle conflicts based on resolution strategy
                    if request.conflict_resolution == "fail_on_conflict":
                        return ContextUpdateResponse.conflict(merge_result.conflicts)
                
                # Step 5: Create updated context entity
                updated_context = current_context.copy()
                updated_context.data = merge_result.merged_data
                updated_context.version += 1
                updated_context.updated_at = datetime.utcnow()
                updated_context.updated_by = user_id
                updated_context.update_agent = agent_id
                
                # Step 6: Atomic commit with optimistic locking
                commit_result = await self.repository.update_with_version_check(
                    updated_context, expected_version=current_context.version
                )
                
                if not commit_result.success:
                    if commit_result.version_conflict:
                        # Retry with exponential backoff
                        return await self._retry_update(request, user_id, agent_id)
                    return ContextUpdateResponse.error(commit_result.error)
                
                # Step 7: Post-update operations
                await self._post_update_operations(
                    level=request.level,
                    context_id=request.context_id,
                    changes=merge_result.changes,
                    user_id=user_id,
                    agent_id=agent_id
                )
                
                return ContextUpdateResponse.success(
                    context=commit_result.context,
                    changes=merge_result.changes,
                    conflicts_resolved=len(merge_result.conflicts)
                )
                
            except Exception as e:
                logger.error(f"Context update failed: {e}", exc_info=True)
                return ContextUpdateResponse.error(f"Update failed: {str(e)}")
    
    async def _post_update_operations(
        self,
        level: str,
        context_id: str,
        changes: List[FieldChange],
        user_id: str,
        agent_id: Optional[str]
    ):
        """Execute post-update operations: caching, notifications, propagation."""
        
        # Invalidate related caches
        await self.cache.invalidate_context(level, context_id, user_id)
        await self.cache.invalidate_inheritance_chain(level, context_id, user_id)
        
        # Send notifications to active agents
        await self.notifications.notify_context_update(
            level=level,
            context_id=context_id,
            changes=changes,
            updated_by=user_id,
            agent_id=agent_id
        )
        
        # Propagate changes to child contexts if needed
        if level in ["global", "project", "branch"]:
            await self._propagate_to_children(level, context_id, changes, user_id)
```

### 4.2 TypeScript/React Frontend Implementation

```typescript
class ContextUpdateManager {
  private apiClient: ApiClient;
  private cache: ContextCache;
  private eventEmitter: EventEmitter;
  
  constructor(apiClient: ApiClient) {
    this.apiClient = apiClient;
    this.cache = new ContextCache();
    this.eventEmitter = new EventEmitter();
  }
  
  /**
   * Update context with optimistic updates and rollback on failure
   */
  async updateContext(
    level: ContextLevel,
    contextId: string,
    updates: Record<string, any>,
    options: UpdateOptions = {}
  ): Promise<UpdateResult> {
    
    // Optimistic update for immediate UI feedback
    const optimisticUpdate = {
      id: contextId,
      level,
      data: updates,
      timestamp: new Date(),
      status: 'pending'
    };
    
    if (options.optimistic !== false) {
      this.cache.applyOptimisticUpdate(optimisticUpdate);
      this.eventEmitter.emit('context:optimistic-update', optimisticUpdate);
    }
    
    try {
      // Prepare update request with conflict resolution
      const request: ContextUpdateRequest = {
        level,
        context_id: contextId,
        data: updates,
        operation: options.operation || 'merge',
        conflict_resolution: options.conflictResolution || 'latest_wins',
        merge_strategy: {
          field_strategies: this.getFieldStrategiesForLevel(level),
          default_strategy: 'merge',
          array_strategy: options.arrayStrategy || 'unique_append',
          validation_rules: this.getValidationRulesForLevel(level)
        }
      };
      
      // Execute update with retry logic
      const result = await this.executeWithRetry(
        () => this.apiClient.updateContext(request),
        options.retries || 3
      );
      
      if (result.success) {
        // Update cache with server response
        this.cache.updateContext(level, contextId, result.context);
        
        // Emit success event
        this.eventEmitter.emit('context:updated', {
          level,
          contextId,
          changes: result.changes,
          conflicts: result.conflicts_resolved
        });
        
        return {
          success: true,
          context: result.context,
          changes: result.changes
        };
      } else {
        // Rollback optimistic update
        this.cache.rollbackOptimisticUpdate(optimisticUpdate.id);
        
        // Handle specific error types
        if (result.error_type === 'conflict') {
          return this.handleUpdateConflict(level, contextId, updates, result.conflicts);
        }
        
        throw new Error(result.error);
      }
      
    } catch (error) {
      // Rollback optimistic update on error
      if (options.optimistic !== false) {
        this.cache.rollbackOptimisticUpdate(optimisticUpdate.id);
        this.eventEmitter.emit('context:update-failed', {
          level,
          contextId,
          error: error.message
        });
      }
      
      throw error;
    }
  }
  
  /**
   * Handle update conflicts with user interaction
   */
  private async handleUpdateConflict(
    level: ContextLevel,
    contextId: string,
    updates: Record<string, any>,
    conflicts: FieldConflict[]
  ): Promise<UpdateResult> {
    
    // Show conflict resolution UI
    const resolution = await this.showConflictResolutionDialog(conflicts);
    
    if (resolution.action === 'retry') {
      // Retry with conflict resolution strategy
      return this.updateContext(level, contextId, resolution.resolvedUpdates, {
        conflictResolution: resolution.strategy,
        optimistic: false // Don't apply optimistically again
      });
    } else if (resolution.action === 'merge') {
      // Apply intelligent merge resolution
      const mergedUpdates = this.mergeConflictResolution(updates, resolution.resolutions);
      return this.updateContext(level, contextId, mergedUpdates, {
        conflictResolution: 'manual',
        optimistic: false
      });
    }
    
    return {
      success: false,
      error: 'Update cancelled by user',
      conflicts
    };
  }
  
  /**
   * Batch update multiple contexts atomically
   */
  async batchUpdate(
    updates: BatchUpdateRequest[]
  ): Promise<BatchUpdateResult> {
    
    // Apply optimistic updates
    const optimisticUpdates = updates.map(update => ({
      id: `batch-${Date.now()}-${Math.random()}`,
      ...update,
      status: 'pending'
    }));
    
    optimisticUpdates.forEach(update => {
      this.cache.applyOptimisticUpdate(update);
    });
    
    try {
      const result = await this.apiClient.batchUpdateContexts({
        updates,
        atomic: true // All-or-nothing execution
      });
      
      if (result.success) {
        // Update cache with all successful updates
        result.results.forEach((updateResult, index) => {
          if (updateResult.success) {
            const update = updates[index];
            this.cache.updateContext(
              update.level, 
              update.context_id, 
              updateResult.context
            );
          }
        });
        
        return {
          success: true,
          results: result.results,
          total_updated: result.total_updated
        };
      } else {
        // Rollback all optimistic updates
        optimisticUpdates.forEach(update => {
          this.cache.rollbackOptimisticUpdate(update.id);
        });
        
        throw new Error(result.error);
      }
      
    } catch (error) {
      // Rollback all optimistic updates
      optimisticUpdates.forEach(update => {
        this.cache.rollbackOptimisticUpdate(update.id);
      });
      
      throw error;
    }
  }
  
  private getFieldStrategiesForLevel(level: ContextLevel): Record<string, FieldStrategy> {
    const strategies = {
      global: {
        'global_settings': { operation: 'merge' },
        'user_preferences': { operation: 'merge' },
        'organization_name': { operation: 'replace', preserve_existing: true }
      },
      project: {
        'team_preferences': { operation: 'merge' },
        'technology_stack': { operation: 'merge' },
        'project_workflow': { operation: 'merge' },
        'local_standards': { operation: 'merge' },
        'project_name': { operation: 'replace', preserve_existing: true }
      },
      branch: {
        'branch_settings': { operation: 'merge' },
        'agent_assignments': { operation: 'unique_append', merge_key: 'agent_id' },
        'branch_progress': { operation: 'append', merge_key: 'timestamp' }
      },
      task: {
        'task_data': { operation: 'merge' },
        'insights': { operation: 'unique_append', merge_key: 'id' },
        'work_history': { operation: 'append', merge_key: 'timestamp' },
        'next_steps': { operation: 'replace' },
        'progress': { operation: 'replace' }
      }
    };
    
    return strategies[level] || {};
  }
}
```

### 4.3 MCP Tool Usage Examples for Agents

```python
# Example 1: Safe Task Context Update
async def update_task_context_safely(task_id: str, work_summary: str, agent_id: str):
    """Example of how an agent should update task context."""
    
    # Step 1: Read existing context first
    current_context = await mcp_tools.manage_context(
        action="get",
        level="task",
        context_id=task_id,
        include_inherited=True,
        force_refresh=False
    )
    
    if not current_context["success"]:
        logger.error(f"Failed to read task context: {current_context['error']}")
        return False
    
    # Step 2: Prepare update data based on existing structure
    existing_insights = current_context["context"].get("insights", [])
    existing_work_history = current_context["context"].get("work_history", [])
    
    new_insight = {
        "id": str(uuid.uuid4()),
        "content": work_summary,
        "agent_id": agent_id,
        "timestamp": datetime.utcnow().isoformat(),
        "category": "work_progress"
    }
    
    new_work_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": agent_id,
        "summary": work_summary,
        "type": "progress_update"
    }
    
    # Step 3: Update with proper merge strategy
    update_result = await mcp_tools.manage_context(
        action="update",
        level="task",
        context_id=task_id,
        data={
            "insights": [new_insight],  # Will be unique_appended
            "work_history": [new_work_entry],  # Will be appended
            "last_updated_by": agent_id,
            "last_activity": datetime.utcnow().isoformat()
        },
        propagate_changes=True
    )
    
    if update_result["success"]:
        logger.info(f"Successfully updated task context for {task_id}")
        return True
    else:
        logger.error(f"Failed to update task context: {update_result['error']}")
        return False

# Example 2: Branch Context Update with Agent Assignment
async def assign_agent_to_branch(branch_id: str, agent_id: str, agent_role: str):
    """Example of updating branch context to assign an agent."""
    
    update_result = await mcp_tools.manage_context(
        action="update",
        level="branch",
        context_id=branch_id,
        data={
            "agent_assignments": [{
                "agent_id": agent_id,
                "role": agent_role,
                "assigned_at": datetime.utcnow().isoformat(),
                "status": "active"
            }],
            "last_agent_change": {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "agent_assigned",
                "agent_id": agent_id,
                "role": agent_role
            }
        },
        propagate_changes=False  # Don't propagate agent assignments to tasks
    )
    
    return update_result["success"]

# Example 3: Project Technology Stack Update
async def update_project_tech_stack(project_id: str, new_technology: dict):
    """Example of updating project technology stack."""
    
    # Read current tech stack first
    current_project = await mcp_tools.manage_context(
        action="get",
        level="project",
        context_id=project_id,
        include_inherited=False
    )
    
    if not current_project["success"]:
        return False
    
    # Update technology stack with merge strategy
    update_result = await mcp_tools.manage_context(
        action="update",
        level="project",
        context_id=project_id,
        data={
            "technology_stack": new_technology,  # Will be deep merged
            "tech_stack_history": [{
                "timestamp": datetime.utcnow().isoformat(),
                "change": new_technology,
                "updated_by": "system"
            }]
        },
        propagate_changes=True  # Propagate to child branches and tasks
    )
    
    return update_result["success"]

# Example 4: Global User Preferences Update
async def update_user_preferences(user_id: str, preferences: dict):
    """Example of updating global user preferences."""
    
    update_result = await mcp_tools.manage_context(
        action="update",
        level="global",
        context_id="global",  # Will be normalized to user-specific UUID
        data={
            "user_preferences": preferences,  # Will be deep merged
            "preferences_history": [{
                "timestamp": datetime.utcnow().isoformat(),
                "changes": list(preferences.keys()),
                "updated_by": user_id
            }]
        },
        user_id=user_id,
        propagate_changes=True  # Propagate to all user's contexts
    )
    
    return update_result["success"]
```

## 5. Context Update Rules

### 5.1 Field Update Rules by Level

```python
CONTEXT_UPDATE_RULES = {
    "global": {
        "immutable_fields": ["organization_name", "created_at", "user_id"],
        "append_only_fields": ["user_activity_log", "system_events", "preferences_history"],
        "merge_fields": ["user_preferences", "global_settings", "agent_configurations"],
        "replace_fields": ["current_focus", "active_notifications"],
        "required_fields": ["organization_name"],
        "max_field_size": {
            "user_activity_log": 1000,  # Max 1000 entries
            "system_events": 500
        }
    },
    
    "project": {
        "immutable_fields": ["project_name", "project_id", "created_at"],
        "append_only_fields": ["team_member_history", "milestone_history", "tech_stack_history"],
        "merge_fields": ["team_preferences", "technology_stack", "project_workflow", "local_standards"],
        "replace_fields": ["current_sprint", "active_features", "project_status"],
        "required_fields": ["project_name", "technology_stack"],
        "validation_rules": {
            "team_preferences.code_review.required": {"type": "boolean"},
            "technology_stack.frontend": {"type": "array", "min_length": 1}
        }
    },
    
    "branch": {
        "immutable_fields": ["git_branch_name", "project_id", "created_at"],
        "append_only_fields": ["commit_history", "merge_events", "agent_activity"],
        "merge_fields": ["branch_settings", "feature_flags"],
        "replace_fields": ["current_status", "latest_build_info", "active_agents"],
        "required_fields": ["git_branch_name", "project_id"],
        "agent_assignment_rules": {
            "max_agents_per_branch": 5,
            "required_roles": ["primary_developer"],
            "role_restrictions": {
                "security_auditor": ["security", "audit", "compliance"],
                "ui_designer": ["frontend", "design", "ux"]
            }
        }
    },
    
    "task": {
        "immutable_fields": ["task_id", "branch_id", "created_at"],
        "append_only_fields": ["work_history", "insights", "progress_snapshots"],
        "merge_fields": ["task_data", "metadata", "configurations"],
        "replace_fields": ["progress", "current_assignee", "next_steps", "priority", "status"],
        "required_fields": ["task_id", "branch_id"],
        "progress_rules": {
            "progress_range": [0, 100],
            "progress_snapshots_max": 50,
            "auto_complete_at": 100
        },
        "insight_rules": {
            "max_insights": 100,
            "required_fields": ["id", "content", "timestamp"],
            "categories": ["discovery", "blocker", "decision", "progress", "note"]
        }
    }
}
```

### 5.2 Conflict Resolution Strategies

```python
class ConflictResolver:
    """Handles conflicts during context updates."""
    
    RESOLUTION_STRATEGIES = {
        "latest_wins": "Always use the newest value",
        "agent_priority": "Use value from higher priority agent",
        "merge_intelligent": "Apply field-specific intelligent merging", 
        "manual": "Require manual resolution",
        "preserve_existing": "Keep existing value, ignore new",
        "fail_on_conflict": "Fail the update operation"
    }
    
    async def resolve_conflict(
        self,
        conflict: FieldConflict,
        strategy: str = "latest_wins"
    ) -> ResolutionResult:
        """Resolve a field conflict using the specified strategy."""
        
        if strategy == "latest_wins":
            return ResolutionResult(
                resolved_value=conflict.new_value,
                strategy_used="latest_wins",
                confidence=1.0
            )
        
        elif strategy == "agent_priority":
            agent_priorities = await self._get_agent_priorities(
                conflict.existing_agent_id, 
                conflict.new_agent_id
            )
            
            if agent_priorities["new"] > agent_priorities["existing"]:
                return ResolutionResult(
                    resolved_value=conflict.new_value,
                    strategy_used="agent_priority",
                    confidence=0.9
                )
            else:
                return ResolutionResult(
                    resolved_value=conflict.existing_value,
                    strategy_used="agent_priority",
                    confidence=0.9
                )
        
        elif strategy == "merge_intelligent":
            return await self._intelligent_merge_resolution(conflict)
        
        elif strategy == "preserve_existing":
            return ResolutionResult(
                resolved_value=conflict.existing_value,
                strategy_used="preserve_existing",
                confidence=1.0
            )
        
        elif strategy == "manual":
            return ResolutionResult(
                resolved_value=None,
                strategy_used="manual",
                confidence=0.0,
                requires_manual_resolution=True
            )
        
        else:
            raise ValueError(f"Unknown conflict resolution strategy: {strategy}")
    
    async def _intelligent_merge_resolution(self, conflict: FieldConflict) -> ResolutionResult:
        """Apply intelligent merging based on field type and content."""
        
        # For lists: merge and deduplicate
        if isinstance(conflict.existing_value, list) and isinstance(conflict.new_value, list):
            merged = list(set(conflict.existing_value + conflict.new_value))
            return ResolutionResult(
                resolved_value=merged,
                strategy_used="intelligent_list_merge",
                confidence=0.8
            )
        
        # For dictionaries: deep merge
        elif isinstance(conflict.existing_value, dict) and isinstance(conflict.new_value, dict):
            merged = self._deep_merge_dicts(conflict.existing_value, conflict.new_value)
            return ResolutionResult(
                resolved_value=merged,
                strategy_used="intelligent_dict_merge",
                confidence=0.8
            )
        
        # For strings: attempt semantic merge
        elif isinstance(conflict.existing_value, str) and isinstance(conflict.new_value, str):
            merged = await self._semantic_string_merge(
                conflict.existing_value, 
                conflict.new_value
            )
            if merged:
                return ResolutionResult(
                    resolved_value=merged,
                    strategy_used="intelligent_string_merge",
                    confidence=0.6
                )
        
        # Default to latest wins if no intelligent merge possible
        return ResolutionResult(
            resolved_value=conflict.new_value,
            strategy_used="fallback_latest_wins",
            confidence=0.5
        )
```

## 6. Concurrency Considerations

### 6.1 Optimistic Locking Implementation

```python
class OptimisticLockingManager:
    """Manages optimistic locking for concurrent context updates."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.lock_timeout = 300  # 5 minutes
    
    async def acquire_update_lock(
        self,
        level: str,
        context_id: str,
        agent_id: str,
        expected_version: int
    ) -> Optional[UpdateLock]:
        """Acquire an optimistic lock for context update."""
        
        lock_key = f"context_lock:{level}:{context_id}"
        lock_value = {
            "agent_id": agent_id,
            "expected_version": expected_version,
            "timestamp": time.time(),
            "lock_id": str(uuid.uuid4())
        }
        
        # Try to set lock with expiration
        success = await self.redis.set(
            lock_key, 
            json.dumps(lock_value),
            nx=True,  # Only if key doesn't exist
            ex=self.lock_timeout
        )
        
        if success:
            return UpdateLock(
                lock_id=lock_value["lock_id"],
                level=level,
                context_id=context_id,
                agent_id=agent_id,
                expected_version=expected_version
            )
        
        # Check if we can extend existing lock (same agent)
        existing_lock_data = await self.redis.get(lock_key)
        if existing_lock_data:
            existing_lock = json.loads(existing_lock_data)
            if existing_lock["agent_id"] == agent_id:
                # Extend our own lock
                extended_lock = existing_lock.copy()
                extended_lock["timestamp"] = time.time()
                await self.redis.set(lock_key, json.dumps(extended_lock), ex=self.lock_timeout)
                return UpdateLock(**extended_lock)
        
        return None  # Failed to acquire lock
    
    async def release_update_lock(self, lock: UpdateLock) -> bool:
        """Release an optimistic lock."""
        
        lock_key = f"context_lock:{lock.level}:{lock.context_id}"
        
        # Use Lua script for atomic release
        lua_script = """
        local lock_data = redis.call('GET', KEYS[1])
        if lock_data then
            local lock = cjson.decode(lock_data)
            if lock.lock_id == ARGV[1] then
                return redis.call('DEL', KEYS[1])
            end
        end
        return 0
        """
        
        result = await self.redis.eval(lua_script, 1, lock_key, lock.lock_id)
        return result == 1
    
    async def check_version_conflict(
        self,
        level: str,
        context_id: str,
        expected_version: int
    ) -> bool:
        """Check if there's a version conflict."""
        
        current_version = await self._get_current_version(level, context_id)
        return current_version != expected_version
    
    async def _get_current_version(self, level: str, context_id: str) -> int:
        """Get current version of context."""
        # Implementation depends on your database structure
        # This should query the actual context version from database
        pass

@dataclass
class UpdateLock:
    lock_id: str
    level: str
    context_id: str
    agent_id: str
    expected_version: int
```

### 6.2 Retry Strategy with Exponential Backoff

```python
class RetryManager:
    """Manages retry logic for failed context updates."""
    
    def __init__(self):
        self.max_retries = 5
        self.base_delay = 1.0  # seconds
        self.max_delay = 30.0  # seconds
        self.jitter_factor = 0.1
    
    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        retry_condition: Callable[[Exception], bool] = None,
        max_retries: Optional[int] = None
    ) -> T:
        """Execute operation with exponential backoff retry."""
        
        max_attempts = (max_retries or self.max_retries) + 1
        
        for attempt in range(max_attempts):
            try:
                result = await operation()
                return result
                
            except Exception as e:
                # Check if we should retry
                if attempt == max_attempts - 1:  # Last attempt
                    raise e
                
                if retry_condition and not retry_condition(e):
                    raise e
                
                # Calculate delay with exponential backoff and jitter
                delay = min(
                    self.base_delay * (2 ** attempt),
                    self.max_delay
                )
                
                # Add jitter to prevent thundering herd
                jitter = delay * self.jitter_factor * random.random()
                total_delay = delay + jitter
                
                logger.warning(
                    f"Context update attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {total_delay:.2f}s"
                )
                
                await asyncio.sleep(total_delay)
        
        raise RuntimeError("Max retries exceeded")
    
    def is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        
        retryable_errors = [
            "version_conflict",
            "lock_timeout",
            "database_connection_error",
            "temporary_unavailable"
        ]
        
        error_msg = str(error).lower()
        return any(retryable in error_msg for retryable in retryable_errors)
```

## 7. Error Handling Strategies

### 7.1 Context Update Error Types

```python
class ContextUpdateError(Exception):
    """Base exception for context update operations."""
    pass

class ValidationError(ContextUpdateError):
    """Data validation failed."""
    def __init__(self, field: str, message: str, invalid_value: Any):
        self.field = field
        self.message = message
        self.invalid_value = invalid_value
        super().__init__(f"Validation error in field '{field}': {message}")

class ConflictError(ContextUpdateError):
    """Version or data conflict detected."""
    def __init__(self, context_id: str, expected_version: int, actual_version: int):
        self.context_id = context_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Version conflict for context {context_id}: "
            f"expected {expected_version}, got {actual_version}"
        )

class PermissionError(ContextUpdateError):
    """Insufficient permissions for update operation."""
    def __init__(self, user_id: str, context_id: str, operation: str):
        self.user_id = user_id
        self.context_id = context_id
        self.operation = operation
        super().__init__(
            f"User {user_id} lacks permission for {operation} on context {context_id}"
        )

class SchemaError(ContextUpdateError):
    """Schema compatibility or migration error."""
    def __init__(self, from_version: str, to_version: str, error_details: str):
        self.from_version = from_version
        self.to_version = to_version
        self.error_details = error_details
        super().__init__(
            f"Schema migration failed: {from_version} -> {to_version}: {error_details}"
        )

class LockTimeoutError(ContextUpdateError):
    """Failed to acquire update lock within timeout."""
    def __init__(self, context_id: str, timeout: int, locked_by: str):
        self.context_id = context_id
        self.timeout = timeout
        self.locked_by = locked_by
        super().__init__(
            f"Failed to acquire lock for context {context_id} within {timeout}s. "
            f"Currently locked by {locked_by}"
        )
```

### 7.2 Comprehensive Error Handling

```python
class ErrorHandler:
    """Centralized error handling for context updates."""
    
    def __init__(self, logger: Logger, metrics: MetricsCollector):
        self.logger = logger
        self.metrics = metrics
        self.error_recovery_strategies = {
            ConflictError: self._handle_conflict_error,
            ValidationError: self._handle_validation_error,
            PermissionError: self._handle_permission_error,
            LockTimeoutError: self._handle_lock_timeout_error,
            SchemaError: self._handle_schema_error
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        recovery_options: Dict[str, Any] = None
    ) -> ErrorHandlingResult:
        """Handle context update errors with appropriate recovery strategies."""
        
        # Log error with context
        self.logger.error(
            f"Context update error: {type(error).__name__}: {error}",
            extra={
                "error_type": type(error).__name__,
                "context_level": context.get("level"),
                "context_id": context.get("context_id"),
                "user_id": context.get("user_id"),
                "agent_id": context.get("agent_id")
            }
        )
        
        # Record metrics
        self.metrics.increment_counter(
            "context_update_errors",
            tags={
                "error_type": type(error).__name__,
                "level": context.get("level", "unknown")
            }
        )
        
        # Try error-specific recovery
        error_type = type(error)
        if error_type in self.error_recovery_strategies:
            recovery_strategy = self.error_recovery_strategies[error_type]
            return await recovery_strategy(error, context, recovery_options or {})
        
        # Generic error handling
        return await self._handle_generic_error(error, context)
    
    async def _handle_conflict_error(
        self,
        error: ConflictError,
        context: Dict[str, Any],
        recovery_options: Dict[str, Any]
    ) -> ErrorHandlingResult:
        """Handle version conflicts with automatic retry or manual resolution."""
        
        retry_strategy = recovery_options.get("retry_strategy", "exponential_backoff")
        max_retries = recovery_options.get("max_retries", 3)
        
        if retry_strategy == "exponential_backoff":
            return ErrorHandlingResult(
                recovery_action="retry_with_backoff",
                retry_count=max_retries,
                retry_delay=1.0,
                message="Version conflict detected. Will retry with latest version.",
                user_message="Another agent updated this context. Retrying with latest changes."
            )
        elif retry_strategy == "manual_merge":
            return ErrorHandlingResult(
                recovery_action="require_manual_merge",
                user_interaction_required=True,
                message="Manual conflict resolution required",
                user_message="Conflicting changes detected. Please review and resolve conflicts."
            )
        
        return ErrorHandlingResult(
            recovery_action="fail",
            message=f"Unresolvable version conflict: {error}"
        )
    
    async def _handle_validation_error(
        self,
        error: ValidationError,
        context: Dict[str, Any],
        recovery_options: Dict[str, Any]
    ) -> ErrorHandlingResult:
        """Handle data validation errors."""
        
        # Check if we can auto-correct the validation error
        if error.field in ["timestamp", "created_at", "updated_at"]:
            return ErrorHandlingResult(
                recovery_action="auto_correct",
                corrected_data={error.field: datetime.utcnow().isoformat()},
                message=f"Auto-corrected invalid {error.field} field",
                user_message="Timestamp was invalid and has been corrected."
            )
        
        # For other validation errors, require user intervention
        return ErrorHandlingResult(
            recovery_action="require_correction",
            user_interaction_required=True,
            invalid_field=error.field,
            validation_message=error.message,
            invalid_value=error.invalid_value,
            message="Data validation failed",
            user_message=f"Invalid value for {error.field}: {error.message}"
        )
    
    async def _handle_permission_error(
        self,
        error: PermissionError,
        context: Dict[str, Any],
        recovery_options: Dict[str, Any]
    ) -> ErrorHandlingResult:
        """Handle permission errors."""
        
        # Check if we can escalate permissions
        if recovery_options.get("allow_permission_escalation"):
            return ErrorHandlingResult(
                recovery_action="request_permission_escalation",
                user_interaction_required=True,
                message="Requesting elevated permissions",
                user_message=f"Additional permissions required for this operation. Request access?"
            )
        
        return ErrorHandlingResult(
            recovery_action="fail",
            message=f"Insufficient permissions: {error}",
            user_message="You don't have permission to perform this operation."
        )
    
    async def _handle_lock_timeout_error(
        self,
        error: LockTimeoutError,
        context: Dict[str, Any],
        recovery_options: Dict[str, Any]
    ) -> ErrorHandlingResult:
        """Handle lock timeout errors."""
        
        wait_for_lock = recovery_options.get("wait_for_lock", True)
        
        if wait_for_lock:
            return ErrorHandlingResult(
                recovery_action="wait_and_retry",
                retry_delay=30.0,  # Wait 30 seconds
                max_wait_time=300.0,  # Max wait 5 minutes
                message=f"Context locked by {error.locked_by}. Waiting for lock release.",
                user_message="Another agent is currently updating this context. Please wait..."
            )
        
        return ErrorHandlingResult(
            recovery_action="fail",
            message=f"Context update locked: {error}",
            user_message="Context is currently being updated by another agent. Please try again later."
        )

@dataclass
class ErrorHandlingResult:
    recovery_action: str  # "retry", "fail", "auto_correct", "require_manual", etc.
    retry_count: int = 0
    retry_delay: float = 0.0
    max_wait_time: float = 0.0
    user_interaction_required: bool = False
    corrected_data: Optional[Dict[str, Any]] = None
    invalid_field: Optional[str] = None
    validation_message: Optional[str] = None
    invalid_value: Optional[Any] = None
    message: str = ""
    user_message: str = ""
```

## 8. Performance Optimization

### 8.1 Batch Update Operations

```python
class BatchUpdateProcessor:
    """Optimized batch processing for multiple context updates."""
    
    def __init__(self, max_batch_size: int = 50):
        self.max_batch_size = max_batch_size
        self.update_queue = asyncio.Queue()
        self.processing = False
    
    async def add_update(self, update_request: ContextUpdateRequest) -> str:
        """Add an update to the batch processing queue."""
        
        batch_id = str(uuid.uuid4())
        await self.update_queue.put({
            "batch_id": batch_id,
            "request": update_request,
            "timestamp": datetime.utcnow()
        })
        
        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self._process_batch_updates())
        
        return batch_id
    
    async def _process_batch_updates(self):
        """Process queued updates in optimized batches."""
        
        self.processing = True
        
        try:
            while not self.update_queue.empty():
                batch = []
                
                # Collect batch of updates
                for _ in range(min(self.max_batch_size, self.update_queue.qsize())):
                    if self.update_queue.empty():
                        break
                    batch.append(await self.update_queue.get())
                
                if batch:
                    await self._execute_batch(batch)
                
        finally:
            self.processing = False
    
    async def _execute_batch(self, batch: List[Dict]):
        """Execute a batch of updates with optimizations."""
        
        # Group by level and context for optimizations
        grouped_updates = defaultdict(list)
        for item in batch:
            request = item["request"]
            key = (request.level, request.context_id)
            grouped_updates[key].append(item)
        
        # Process each group
        for (level, context_id), updates in grouped_updates.items():
            if len(updates) == 1:
                # Single update - process normally
                await self._process_single_update(updates[0])
            else:
                # Multiple updates to same context - merge them
                await self._process_merged_updates(level, context_id, updates)
    
    async def _process_merged_updates(
        self,
        level: str,
        context_id: str,
        updates: List[Dict]
    ):
        """Merge multiple updates to the same context into a single operation."""
        
        # Sort updates by timestamp
        updates.sort(key=lambda x: x["timestamp"])
        
        # Merge all update data
        merged_data = {}
        for update_item in updates:
            request = update_item["request"]
            merged_data = self._merge_update_data(merged_data, request.data)
        
        # Create single merged update request
        merged_request = ContextUpdateRequest(
            level=level,
            context_id=context_id,
            data=merged_data,
            operation=UpdateOperation.MERGE,
            batch_ids=[item["batch_id"] for item in updates]
        )
        
        # Execute merged update
        await self._execute_single_update(merged_request)
```

### 8.2 Caching Strategy for Context Updates

```python
class ContextUpdateCache:
    """Smart caching for context update operations."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.local_cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute local cache
    
    async def get_cached_context(
        self,
        level: str,
        context_id: str,
        user_id: str,
        include_version: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get context from cache with version information."""
        
        cache_key = f"context:{user_id}:{level}:{context_id}"
        
        # Try local cache first
        if cache_key in self.local_cache:
            return self.local_cache[cache_key]
        
        # Try Redis cache
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            context_data = json.loads(cached_data)
            
            # Update local cache
            self.local_cache[cache_key] = context_data
            
            return context_data
        
        return None
    
    async def cache_context(
        self,
        level: str,
        context_id: str,
        user_id: str,
        context_data: Dict[str, Any],
        ttl: int = 3600  # 1 hour
    ):
        """Cache context data with TTL."""
        
        cache_key = f"context:{user_id}:{level}:{context_id}"
        
        # Add caching metadata
        cached_data = {
            **context_data,
            "_cache_timestamp": time.time(),
            "_cache_ttl": ttl
        }
        
        # Cache in Redis
        await self.redis.set(
            cache_key,
            json.dumps(cached_data, default=str),
            ex=ttl
        )
        
        # Cache locally
        self.local_cache[cache_key] = cached_data
    
    async def invalidate_context(
        self,
        level: str,
        context_id: str,
        user_id: str
    ):
        """Invalidate cached context data."""
        
        cache_key = f"context:{user_id}:{level}:{context_id}"
        
        # Remove from local cache
        self.local_cache.pop(cache_key, None)
        
        # Remove from Redis
        await self.redis.delete(cache_key)
        
        # Invalidate related inheritance caches
        await self._invalidate_inheritance_cache(level, context_id, user_id)
    
    async def _invalidate_inheritance_cache(
        self,
        level: str,
        context_id: str,
        user_id: str
    ):
        """Invalidate inheritance chain caches."""
        
        # Invalidate child context caches (they inherit from this context)
        child_patterns = {
            "global": [f"context:{user_id}:project:*", f"context:{user_id}:branch:*", f"context:{user_id}:task:*"],
            "project": [f"context:{user_id}:branch:*", f"context:{user_id}:task:*"],
            "branch": [f"context:{user_id}:task:*"]
        }
        
        if level in child_patterns:
            for pattern in child_patterns[level]:
                keys = await self.redis.keys(pattern)
                if keys:
                    await self.redis.delete(*keys)
```

## 9. Monitoring and Observability

### 9.1 Metrics Collection

```python
class ContextUpdateMetrics:
    """Comprehensive metrics collection for context updates."""
    
    def __init__(self, metrics_client: MetricsClient):
        self.metrics = metrics_client
        
        # Define metrics
        self.update_counter = self.metrics.counter(
            "context_updates_total",
            description="Total number of context updates",
            labels=["level", "operation", "result", "agent_type"]
        )
        
        self.update_duration = self.metrics.histogram(
            "context_update_duration_seconds",
            description="Time taken for context updates",
            labels=["level", "operation"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        self.conflict_counter = self.metrics.counter(
            "context_update_conflicts_total",
            description="Number of update conflicts",
            labels=["level", "resolution_strategy", "resolved"]
        )
        
        self.batch_size_histogram = self.metrics.histogram(
            "context_batch_update_size",
            description="Number of updates in batch operations",
            buckets=[1, 5, 10, 20, 50, 100]
        )
        
        self.cache_hit_counter = self.metrics.counter(
            "context_cache_hits_total",
            description="Context cache hit/miss statistics",
            labels=["cache_type", "result", "level"]
        )
    
    def record_update_start(self, level: str, operation: str, agent_id: str) -> str:
        """Record the start of a context update operation."""
        trace_id = str(uuid.uuid4())
        
        # Start timing
        self.update_start_times[trace_id] = time.time()
        
        return trace_id
    
    def record_update_complete(
        self,
        trace_id: str,
        level: str,
        operation: str,
        result: str,
        agent_type: str,
        conflicts_count: int = 0
    ):
        """Record the completion of a context update operation."""
        
        # Calculate duration
        start_time = self.update_start_times.pop(trace_id, time.time())
        duration = time.time() - start_time
        
        # Record metrics
        self.update_counter.increment(
            labels={
                "level": level,
                "operation": operation,
                "result": result,
                "agent_type": agent_type
            }
        )
        
        self.update_duration.observe(
            duration,
            labels={
                "level": level,
                "operation": operation
            }
        )
        
        # Record conflicts if any
        if conflicts_count > 0:
            self.conflict_counter.increment(
                conflicts_count,
                labels={
                    "level": level,
                    "resolution_strategy": "auto",
                    "resolved": "true"
                }
            )
    
    def record_batch_update(self, batch_size: int):
        """Record batch update metrics."""
        self.batch_size_histogram.observe(batch_size)
    
    def record_cache_hit(self, cache_type: str, hit: bool, level: str):
        """Record cache hit/miss."""
        self.cache_hit_counter.increment(
            labels={
                "cache_type": cache_type,
                "result": "hit" if hit else "miss",
                "level": level
            }
        )
```

### 9.2 Audit Trail Implementation

```python
class ContextUpdateAuditLogger:
    """Comprehensive audit logging for context updates."""
    
    def __init__(self, logger: Logger, audit_storage: AuditStorage):
        self.logger = logger
        self.audit_storage = audit_storage
    
    async def log_update_attempt(
        self,
        level: str,
        context_id: str,
        update_data: Dict[str, Any],
        user_id: str,
        agent_id: Optional[str],
        trace_id: str
    ) -> str:
        """Log a context update attempt."""
        
        audit_entry = {
            "audit_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "context_update_attempt",
            "level": level,
            "context_id": context_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "update_data_summary": self._summarize_update_data(update_data),
            "update_data_hash": self._hash_data(update_data),
            "ip_address": self._get_client_ip(),
            "user_agent": self._get_user_agent()
        }
        
        # Log to application logger
        self.logger.info(
            f"Context update attempt: {level}:{context_id}",
            extra=audit_entry
        )
        
        # Store in audit database
        await self.audit_storage.store_entry(audit_entry)
        
        return audit_entry["audit_id"]
    
    async def log_update_result(
        self,
        audit_id: str,
        trace_id: str,
        success: bool,
        error_message: Optional[str] = None,
        conflicts_resolved: int = 0,
        changes_applied: List[str] = None
    ):
        """Log the result of a context update."""
        
        result_entry = {
            "audit_id": audit_id,
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "context_update_result",
            "success": success,
            "error_message": error_message,
            "conflicts_resolved": conflicts_resolved,
            "changes_applied": changes_applied or [],
            "processing_duration_ms": self._get_processing_duration(trace_id)
        }
        
        # Log result
        if success:
            self.logger.info(
                f"Context update successful: {audit_id}",
                extra=result_entry
            )
        else:
            self.logger.error(
                f"Context update failed: {audit_id} - {error_message}",
                extra=result_entry
            )
        
        # Update audit record
        await self.audit_storage.update_entry(audit_id, result_entry)
    
    async def log_conflict_resolution(
        self,
        trace_id: str,
        level: str,
        context_id: str,
        conflicts: List[FieldConflict],
        resolution_strategy: str,
        resolved_values: Dict[str, Any]
    ):
        """Log conflict resolution details."""
        
        conflict_entry = {
            "audit_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "conflict_resolution",
            "level": level,
            "context_id": context_id,
            "conflict_count": len(conflicts),
            "conflicts": [
                {
                    "field": c.field,
                    "existing_value_hash": self._hash_data(c.existing_value),
                    "new_value_hash": self._hash_data(c.new_value),
                    "conflict_type": c.conflict_type
                } for c in conflicts
            ],
            "resolution_strategy": resolution_strategy,
            "resolved_values_hash": self._hash_data(resolved_values)
        }
        
        self.logger.warning(
            f"Context update conflicts resolved: {len(conflicts)} conflicts",
            extra=conflict_entry
        )
        
        await self.audit_storage.store_entry(conflict_entry)
    
    def _summarize_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of update data for audit logs."""
        return {
            "field_count": len(data),
            "fields_updated": list(data.keys()),
            "has_nested_objects": any(isinstance(v, dict) for v in data.values()),
            "has_arrays": any(isinstance(v, list) for v in data.values()),
            "data_size_bytes": len(json.dumps(data, default=str))
        }
    
    def _hash_data(self, data: Any) -> str:
        """Create a hash of data for audit purposes."""
        import hashlib
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
```

## 10. Testing Strategy

### 10.1 Unit Tests for Update Logic

```python
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

class TestContextUpdateService:
    """Comprehensive unit tests for context update service."""
    
    @pytest.fixture
    def mock_dependencies(self):
        return {
            "repository": Mock(),
            "merge_engine": AsyncMock(),
            "schema_manager": AsyncMock(),
            "cache_service": AsyncMock(),
            "notification_service": AsyncMock()
        }
    
    @pytest.fixture
    def update_service(self, mock_dependencies):
        return ContextUpdateService(**mock_dependencies)
    
    @pytest.mark.asyncio
    async def test_simple_update_success(self, update_service, mock_dependencies):
        """Test successful simple context update."""
        
        # Arrange
        request = ContextUpdateRequest(
            level="task",
            context_id="task-123",
            data={"progress": 75, "status": "in_progress"},
            operation=UpdateOperation.MERGE
        )
        
        current_context = Mock()
        current_context.data = {"progress": 50, "task_data": {"title": "Test"}}
        current_context.version = 1
        
        mock_dependencies["repository"].get_with_version.return_value = current_context
        mock_dependencies["merge_engine"].apply_merge_strategies.return_value = MergeResult(
            merged_data={"progress": 75, "status": "in_progress", "task_data": {"title": "Test"}},
            conflicts=[],
            changes=[{"field": "progress", "old_value": 50, "new_value": 75}]
        )
        
        commit_result = Mock()
        commit_result.success = True
        commit_result.context = current_context
        mock_dependencies["repository"].update_with_version_check.return_value = commit_result
        
        # Act
        result = await update_service.update_context(request, user_id="user-123")
        
        # Assert
        assert result.success is True
        assert result.changes is not None
        mock_dependencies["repository"].get_with_version.assert_called_once()
        mock_dependencies["merge_engine"].apply_merge_strategies.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_version_conflict_retry(self, update_service, mock_dependencies):
        """Test version conflict handling with retry."""
        
        # Arrange
        request = ContextUpdateRequest(
            level="project",
            context_id="project-456",
            data={"team_preferences": {"code_review": True}},
            operation=UpdateOperation.MERGE
        )
        
        current_context = Mock()
        current_context.version = 2
        mock_dependencies["repository"].get_with_version.return_value = current_context
        
        # First attempt fails with version conflict
        first_commit_result = Mock()
        first_commit_result.success = False
        first_commit_result.version_conflict = True
        
        # Second attempt succeeds
        second_commit_result = Mock()
        second_commit_result.success = True
        second_commit_result.context = current_context
        
        mock_dependencies["repository"].update_with_version_check.side_effect = [
            first_commit_result,
            second_commit_result
        ]
        
        # Act
        result = await update_service.update_context(request, user_id="user-123")
        
        # Assert
        assert result.success is True
        assert mock_dependencies["repository"].update_with_version_check.call_count == 2
    
    @pytest.mark.asyncio
    async def test_merge_conflicts_resolution(self, update_service, mock_dependencies):
        """Test merge conflict resolution."""
        
        # Arrange
        request = ContextUpdateRequest(
            level="branch",
            context_id="branch-789",
            data={"branch_settings": {"auto_merge": False}},
            operation=UpdateOperation.MERGE,
            conflict_resolution="intelligent_merge"
        )
        
        current_context = Mock()
        current_context.data = {"branch_settings": {"auto_merge": True, "require_review": True}}
        mock_dependencies["repository"].get_with_version.return_value = current_context
        
        # Simulate merge conflict
        conflict = FieldConflict(
            field="branch_settings.auto_merge",
            existing_value=True,
            new_value=False,
            conflict_type="value_mismatch"
        )
        
        mock_dependencies["merge_engine"].apply_merge_strategies.return_value = MergeResult(
            merged_data={"branch_settings": {"auto_merge": False, "require_review": True}},
            conflicts=[conflict],
            changes=[]
        )
        
        # Act
        result = await update_service.update_context(request, user_id="user-123")
        
        # Assert
        assert result.success is True
        assert result.conflicts_resolved == 1
```

### 10.2 Integration Tests

```python
class TestContextUpdateIntegration:
    """Integration tests for complete update workflow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_task_update(self):
        """Test complete task context update workflow."""
        
        # Setup: Create project, branch, and task contexts
        project_id = await self.create_test_project()
        branch_id = await self.create_test_branch(project_id)
        task_id = await self.create_test_task(branch_id)
        
        # Test: Update task context with work progress
        update_data = {
            "insights": [{
                "id": "insight-001",
                "content": "Discovered optimization opportunity",
                "category": "discovery",
                "timestamp": datetime.utcnow().isoformat()
            }],
            "work_history": [{
                "timestamp": datetime.utcnow().isoformat(),
                "summary": "Implemented caching layer",
                "agent_id": "test-agent"
            }],
            "progress": 85
        }
        
        result = await self.context_service.update_context(
            ContextUpdateRequest(
                level="task",
                context_id=task_id,
                data=update_data,
                operation=UpdateOperation.MERGE
            ),
            user_id="test-user"
        )
        
        # Verify: Update succeeded
        assert result.success is True
        
        # Verify: Data was properly merged
        updated_context = await self.context_service.get_context(
            level="task",
            context_id=task_id,
            user_id="test-user"
        )
        
        assert updated_context["context"]["progress"] == 85
        assert len(updated_context["context"]["insights"]) == 1
        assert len(updated_context["context"]["work_history"]) == 1
        
        # Verify: Inheritance still works
        inherited_context = await self.context_service.get_context(
            level="task",
            context_id=task_id,
            include_inherited=True,
            user_id="test-user"
        )
        
        # Should include project and branch settings
        assert "team_preferences" in inherited_context["context"]  # From project
        assert "branch_settings" in inherited_context["context"]    # From branch
    
    @pytest.mark.asyncio
    async def test_concurrent_updates_same_context(self):
        """Test concurrent updates to the same context."""
        
        task_id = await self.create_test_task_with_context()
        
        # Create multiple concurrent update tasks
        async def update_task(agent_id: str, progress_value: int):
            return await self.context_service.update_context(
                ContextUpdateRequest(
                    level="task",
                    context_id=task_id,
                    data={
                        "progress": progress_value,
                        "work_history": [{
                            "agent_id": agent_id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "summary": f"Agent {agent_id} progress update"
                        }]
                    }
                ),
                user_id="test-user",
                agent_id=agent_id
            )
        
        # Execute concurrent updates
        results = await asyncio.gather(
            update_task("agent-1", 30),
            update_task("agent-2", 60),
            update_task("agent-3", 90),
            return_exceptions=True
        )
        
        # Verify: All updates succeeded (with possible retries)
        successful_updates = [r for r in results if isinstance(r, ContextUpdateResponse) and r.success]
        assert len(successful_updates) == 3
        
        # Verify: Final context contains all work history entries
        final_context = await self.context_service.get_context(
            level="task",
            context_id=task_id,
            user_id="test-user"
        )
        
        work_history = final_context["context"]["work_history"]
        assert len(work_history) >= 3  # At least one entry per agent
        
        # Verify: Progress has the final value (one of the updates won)
        assert final_context["context"]["progress"] in [30, 60, 90]
```

## Conclusion

This technical specification provides a comprehensive implementation guide for safe, atomic, and intelligent context updates across the agenthub 4-tier context hierarchy. The specification addresses all major concerns including data preservation, merge strategies, agent coordination, concurrency handling, and error recovery.

### Key Implementation Points:

1. **Merge Strategy Engine**: Field-level merge strategies ensure data is combined intelligently based on field types and business rules.

2. **Optimistic Locking**: Version-based conflict detection with automatic retry mechanisms prevent data loss in concurrent scenarios.

3. **Error Recovery**: Comprehensive error handling with multiple recovery strategies ensures system resilience.

4. **Performance Optimization**: Batch processing, intelligent caching, and retry strategies optimize system performance.

5. **Audit Trail**: Complete audit logging ensures all context changes are tracked for compliance and debugging.

6. **Testing Strategy**: Comprehensive unit and integration tests validate the implementation under various scenarios.

This implementation will enable reliable multi-session and multi-agent collaboration while maintaining data integrity across the entire context hierarchy.

---

*Context Update Implementation Technical Specification v1.0 - February 2025*