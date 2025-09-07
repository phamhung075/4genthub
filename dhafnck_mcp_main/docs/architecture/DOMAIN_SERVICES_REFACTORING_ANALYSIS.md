# Domain Services Refactoring Analysis
**Moving Business Logic from Application Layer to Domain Services**

## Executive Summary

Based on the recent DDD compliance analysis showing 95/100 score with enhancement opportunities to "move more business logic to Domain Services", this analysis identifies specific business logic currently in Application Layer (facades) that should be moved to Domain Services following DDD best practices.

## Current Domain Services Architecture

### Existing Domain Services ✅
The project already has excellent domain services implementing core business rules:

1. **`TaskValidationService`** - Comprehensive validation business logic
   - Field validation, relationship validation, business constraints
   - Status transition validation, content appropriateness checks
   - Complex multi-entity validation rules

2. **`TaskPriorityService`** - Priority calculation and ordering business logic
   - Priority scoring based on multiple factors (due date, dependencies, age)
   - Task ordering for "next task" recommendations
   - Dynamic priority adjustments based on context

3. **`TaskStateTransitionService`** - State machine and transition business logic
   - Valid state transitions with prerequisites
   - Automatic state changes based on dependencies
   - State-specific business rules and side effects

4. **`TaskProgressService`** - Progress calculation business logic
   - Task completion percentages with subtask aggregation
   - Progress scoring for prioritization
   - Completion rules and blocking factor identification

## Business Logic Misplaced in Application Layer

### 1. Task Dependency Management Logic 🔄
**Current Location**: `TaskApplicationFacade` (lines 960-1057)
**Issue**: Complex dependency relationship business rules in application layer

```python
# Current: In TaskApplicationFacade.add_dependency()
task.add_dependency(dependency_task.id)
# Complex validation logic mixed with application concerns
```

**Recommendation**: Move to new `TaskDependencyService`

### 2. User Authentication and Context Resolution Logic 🔐
**Current Location**: 
- `TaskApplicationFacade` (lines 148-186, 103-135)
- `SubtaskApplicationFacade` (lines 58-164)

**Issue**: Authentication business rules scattered across facades

```python
# Current: Complex user context derivation in facades
derived_user_id = None
try:
    from fastmcp.auth.middleware.request_context_middleware import get_current_user_id
    context_user_obj = get_current_user_id()
    # Complex extraction logic...
```

**Recommendation**: Move to new `TaskAuthenticationService`

### 3. Task-Context Synchronization Logic 📋
**Current Location**: `TaskApplicationFacade` (lines 201-253)
**Issue**: Business rules for context creation and synchronization in application layer

```python
# Current: Context sync business logic in facade
updated_task_response = self._await_if_coroutine(
    self._task_context_sync_service.sync_context_and_get_task(...)
)
```

**Recommendation**: Move to new `TaskContextService`

### 4. Complex Task Filtering and Querying Logic 🔍
**Current Location**: `TaskApplicationFacade` (lines 829-957)
**Issue**: Business rules for task filtering, summarization mixed with application concerns

```python
# Current: Complex filtering logic in facade
if PerformanceConfig.is_performance_mode() and minimal:
    # Repository selection and filtering logic
```

**Recommendation**: Move to new `TaskFilteringService`

### 5. Task Summary and Aggregation Logic 📊
**Current Location**: `TaskApplicationFacade` (lines 856-957)
**Issue**: Business rules for task summaries, counts, and aggregations in application layer

**Recommendation**: Move to new `TaskSummaryService`

## Recommended New Domain Services

### 1. TaskDependencyService
**Purpose**: Centralize all dependency-related business logic
**Responsibilities**:
- Dependency relationship validation
- Circular dependency detection
- Dependency completion impact analysis
- Blocking task identification

```python
class TaskDependencyService:
    def add_dependency(self, task: Task, dependency_task: Task) -> DependencyResult
    def remove_dependency(self, task: Task, dependency_id: TaskId) -> DependencyResult
    def validate_dependency_chain(self, task: Task, all_tasks: List[Task]) -> ValidationResult
    def get_blocking_analysis(self, task: Task) -> BlockingAnalysis
    def handle_dependency_completion(self, completed_task: Task) -> List[TaskUpdate]
```

### 2. TaskAuthenticationService
**Purpose**: Centralize authentication and authorization business logic
**Responsibilities**:
- User context resolution and validation
- Permission checks for task operations
- Authentication state management

```python
class TaskAuthenticationService:
    def resolve_user_context(self, request_context: Any) -> UserContext
    def validate_task_access(self, user: User, task: Task, operation: str) -> AccessResult
    def derive_user_from_context(self, context: Dict[str, Any]) -> User
```

### 3. TaskContextService
**Purpose**: Centralize task-context synchronization business rules
**Responsibilities**:
- Context creation and linking rules
- Context synchronization validation
- Context hierarchy management

```python
class TaskContextService:
    def should_create_context(self, task: Task) -> bool
    def sync_task_context(self, task: Task, context_data: Dict) -> ContextSyncResult
    def validate_context_consistency(self, task: Task) -> ValidationResult
```

### 4. TaskFilteringService
**Purpose**: Centralize complex filtering and querying business logic
**Responsibilities**:
- Performance-based repository selection
- Complex filtering rule application
- Query optimization decisions

```python
class TaskFilteringService:
    def select_optimal_repository(self, filters: FilterCriteria) -> Repository
    def apply_business_filters(self, tasks: List[Task], criteria: FilterCriteria) -> List[Task]
    def optimize_query_strategy(self, request: ListTasksRequest) -> QueryStrategy
```

### 5. TaskSummaryService
**Purpose**: Centralize task summarization and aggregation business logic
**Responsibilities**:
- Summary data calculation rules
- Aggregation algorithms
- Performance optimization for summaries

```python
class TaskSummaryService:
    def create_task_summary(self, task: Task, options: SummaryOptions) -> TaskSummary
    def calculate_aggregated_metrics(self, tasks: List[Task]) -> AggregatedMetrics
    def generate_lightweight_summary(self, tasks: List[Task]) -> List[LightweightSummary]
```

## Enhanced Integration Between Services

### Service Collaboration Patterns
The domain services should collaborate using well-defined interfaces:

```python
# Example: TaskStateTransitionService using other domain services
class TaskStateTransitionService:
    def __init__(
        self,
        dependency_service: TaskDependencyService,
        progress_service: TaskProgressService,
        validation_service: TaskValidationService
    ):
        # Compose services for complex business operations
```

### Protocol-Based Dependencies
Continue using Protocol pattern to avoid infrastructure dependencies:

```python
class TaskRepositoryProtocol(Protocol):
    def find_by_id(self, task_id: TaskId) -> Optional[Task]: ...
    def find_all(self) -> List[Task]: ...
```

## Implementation Strategy

### Phase 1: Create New Domain Services
1. **TaskDependencyService** - High impact, complex business logic
2. **TaskAuthenticationService** - Security critical, widely used
3. **TaskContextService** - Context management is core business logic

### Phase 2: Enhance Existing Services
1. Add integration points between services
2. Refactor validation service to work with new services
3. Enhance progress service with dependency information

### Phase 3: Refactor Application Facades
1. Remove business logic from facades
2. Delegate to appropriate domain services
3. Keep only orchestration and response formatting

### Phase 4: Integration Testing
1. Comprehensive testing of service interactions
2. Performance impact assessment
3. Validation of DDD compliance improvements

## Specific Refactoring Examples

### Before: Dependency Logic in Facade
```python
# TaskApplicationFacade.add_dependency()
task = self._task_repository.find_by_id(TaskId(task_id))
dependency_task = self._task_repository.find_by_id(TaskId(dependency_id))

# Business logic mixed with application concerns
if not dependency_task:
    raise TaskNotFoundError(f"Dependency task with ID {dependency_id} not found")

task.add_dependency(dependency_task.id)
self._task_repository.save(task)
```

### After: Business Logic in Domain Service
```python
# TaskApplicationFacade.add_dependency()
result = self._dependency_service.add_dependency(task_id, dependency_id)
return result.to_response()

# TaskDependencyService.add_dependency()
def add_dependency(self, task_id: str, dependency_id: str) -> DependencyResult:
    # All business logic centralized in domain service
    task = self._find_task_with_validation(task_id)
    dependency = self._find_dependency_with_validation(dependency_id)
    
    # Business rules
    if self._creates_circular_dependency(task, dependency):
        return DependencyResult.failure("Circular dependency detected")
    
    if self._exceeds_dependency_limit(task):
        return DependencyResult.failure("Maximum dependencies exceeded")
    
    # Execute business operation
    task.add_dependency(dependency.id)
    self._task_repository.save(task)
    
    return DependencyResult.success(task)
```

## Expected Benefits

### 1. Enhanced DDD Compliance
- Clear separation between Application and Domain layers
- Business logic centralized in appropriate domain services
- Better adherence to DDD principles

### 2. Improved Maintainability
- Single responsibility for each domain service
- Easier to test business logic in isolation
- Reduced coupling between application and domain logic

### 3. Better Reusability
- Domain services can be reused across multiple use cases
- Business logic not tied to specific application facades
- Easier to extend with new functionality

### 4. Enhanced Performance
- Business logic optimization in domain services
- Better caching strategies at domain level
- Reduced duplication of business rule execution

## Implementation Checklist

- [ ] Create `TaskDependencyService` with full dependency management logic
- [ ] Create `TaskAuthenticationService` for user context management
- [ ] Create `TaskContextService` for context synchronization rules
- [ ] Create `TaskFilteringService` for complex querying logic
- [ ] Create `TaskSummaryService` for aggregation business rules
- [ ] Refactor `TaskApplicationFacade` to delegate to domain services
- [ ] Refactor `SubtaskApplicationFacade` to use domain services
- [ ] Add comprehensive integration tests
- [ ] Update documentation and architectural diagrams
- [ ] Performance testing and optimization

## Conclusion

This refactoring will move the project from an already excellent 95/100 DDD compliance score to near-perfect compliance by properly separating business logic into domain services. The current architecture provides an excellent foundation, and these enhancements will further improve maintainability, testability, and adherence to DDD principles.

---
**Status**: Analysis Complete  
**Next Steps**: Begin implementation of new domain services  
**Priority**: High - Foundational architecture improvement  