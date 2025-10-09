# DDD Refactoring Task Roadmap - Complete Implementation Plan

**Generated**: 2025-10-09
**Total Phases**: 8
**Total Duration**: ~18 weeks
**Total Tasks Created**: 8 parent tasks + subtasks

---

## 📋 Executive Summary

This roadmap provides a complete task breakdown for the DDD compliance refactoring project. All tasks have been created in the MCP system with:
- Clear acceptance criteria
- Assigned specialized agents
- Dependency tracking
- Feature flag strategies for zero-downtime migration

---

## 🎯 Phase 1: Rich Domain Models (2 weeks)

**Task ID**: `3fc56e2b-f42b-47bf-bd09-5adc359a51c9`
**Priority**: Critical
**Assignees**: coding-agent, system-architect-agent
**Dependencies**: None (starting phase)

### Objective
Transform anemic domain entities into rich domain models by adding business logic methods.

### Target Files
- `domain/entities/context.py:220-313` (TaskContextUnified)
- `domain/entities/project.py`
- `domain/entities/agent.py`
- `domain/entities/git_branch.py`

### Subtasks
1. **1.1**: Add Feature Flag and Business Methods to TaskContextUnified
   - Agent: coding-agent
   - Add `FEATURE_RICH_DOMAIN_MODEL` flag
   - Implement: `validate_context_data()`, `merge_context_updates()`, `add_insight()`, `update_progress()`

2. **1.2**: Create Unit Tests for Rich Domain Methods
   - Agent: test-orchestrator-agent
   - Target 100% coverage
   - File: `tests/unit/domain/entities/test_context_rich_domain.py`

3. **1.3**: Add Business Logic to Project Entity
   - Agent: coding-agent
   - Implement: `validate_agent_assignment()`, `calculate_project_health()`, `check_deadline_risk()`

4. **1.4**: Add Business Logic to Agent Entity
   - Agent: coding-agent
   - Implement: `validate_capability_match()`, `calculate_workload_score()`, `check_availability()`

5. **1.5**: Integration Testing with Feature Flag
   - Agent: test-orchestrator-agent
   - Test flag on/off scenarios
   - File: `tests/integration/test_rich_domain_migration.py`

### Success Criteria
✅ Feature flag controls new behavior
✅ Legacy behavior preserved when flag=false
✅ Business logic in domain entities, not services
✅ Unit tests with 100% coverage
✅ No breaking changes

---

## 🎯 Phase 2: Clean Repository Pattern (1 week)

**Task ID**: `dce163fb-3318-4fd9-a85e-33b00c458d10`
**Priority**: High
**Assignees**: coding-agent, system-architect-agent
**Dependencies**: Phase 1 complete

### Objective
Remove concrete implementation helpers from repository interfaces.

### Target Files
- `domain/repositories/base_repository.py:115-144` (pagination helper)
- `infrastructure/repositories/base_orm_repository.py:119-124` (validation logic)

### Subtasks
1. **2.1**: Create PaginationService in Domain Layer
   - Agent: coding-agent
   - Extract logic from `base_repository.py:115-144`
   - New file: `domain/services/pagination_service.py`

2. **2.2**: Remove Validation Logic from Infrastructure Layer
   - Agent: coding-agent
   - Move from `base_orm_repository.py:119-124` to domain

3. **2.3**: Clean BaseRepository Interface
   - Agent: coding-agent
   - Remove concrete `create_pagination_result()` method

4. **2.4**: Update Repository Implementations to Use PaginationService
   - Agent: coding-agent
   - Refactor all repository implementations

### Success Criteria
✅ Repository interfaces contain only abstract methods
✅ Pagination logic moved to appropriate layer
✅ Validation logic moved to domain
✅ Adapter maintains backward compatibility
✅ All tests pass

---

## 🎯 Phase 3: Move Orchestrator to Application Layer (1 week)

**Task ID**: `f80cdc25-522c-49b3-8c14-9a87ceacbbac`
**Priority**: Critical
**Assignees**: system-architect-agent, coding-agent
**Dependencies**: Phase 1, Phase 2 complete

### Objective
Move orchestrator from domain to application layer (multi-entity coordination is application concern).

### Target Files
- **Current**: `domain/services/orchestrator.py:1-362`
- **New**: `application/orchestration/project_orchestrator.py`

### Strategy
Create new application service, gradually migrate calls using `FEATURE_APPLICATION_ORCHESTRATOR` flag.

### Success Criteria
✅ Orchestrator moved to application layer
✅ Domain layer no longer has orchestration logic
✅ Feature flag controls which orchestrator is used
✅ All existing functionality preserved

---

## 🎯 Phase 4: Introduce Value Objects for Type Safety (2 weeks)

**Task ID**: `9b9a1ef0-39c2-4098-a93e-d0e5dfe0d16e`
**Priority**: Medium
**Assignees**: coding-agent, system-architect-agent
**Dependencies**: Phase 3 complete

### Objective
Create immutable value objects for domain concepts to enforce type safety.

### New Value Objects
- `domain/value_objects/task_id.py` - TaskId
- `domain/value_objects/project_id.py` - ProjectId
- `domain/value_objects/agent_id.py` - AgentId
- `domain/value_objects/priority.py` - Enhanced Priority
- `domain/value_objects/status.py` - Status

### Benefits
- Type safety (can't pass TaskId where ProjectId expected)
- Validation centralized in one place
- Immutability enforced by design

### Success Criteria
✅ All value objects created with validation
✅ Entities use value objects instead of strings
✅ Type hints updated throughout codebase

---

## 🎯 Phase 5: Implement Domain Events Pattern (2 weeks)

**Task ID**: `6e777f80-c7d1-4694-b867-4173ca6787cf`
**Priority**: Medium
**Assignees**: system-architect-agent, coding-agent
**Dependencies**: Phase 4 complete

### Objective
Add domain events for key state changes to enable loose coupling between aggregates.

### New Structure
- `domain/events/base_event.py` - Event base class
- `domain/events/task_events.py` - Task-related events
- `domain/events/agent_events.py` - Agent-related events
- `application/event_handlers/` - Event handler directory

### Key Events
- **Task Events**: TaskCreated, TaskUpdated, TaskCompleted
- **Agent Events**: AgentAssigned, AgentUnassigned
- **Project Events**: ProjectCreated, ProjectArchived

### Success Criteria
✅ Event infrastructure in place
✅ Key domain events implemented
✅ Event handlers process events asynchronously
✅ No breaking changes to existing flows

---

## 🎯 Phase 6: Thin Application Services (2 weeks)

**Task ID**: `bc8927c0-91dd-4e9c-b65a-781ea408f150`
**Priority**: High
**Assignees**: coding-agent, system-architect-agent
**Dependencies**: Phase 5 complete

### Objective
Refactor application facades to delegate business logic to domain. Application layer should coordinate, not decide.

### Target Files
- `application/facades/unified_context_facade.py:110,146,195` (generic exception handling)
- `application/facades/task_facade.py`
- `application/facades/project_facade.py`

### Changes
- Move business decisions to domain entities
- Application facades only coordinate workflow
- Use specific domain exceptions
- Delegate validation to domain

### Success Criteria
✅ No business logic in application layer
✅ Application services coordinate only
✅ Domain exceptions used throughout

---

## 🎯 Phase 7: Clean MCP Controllers (2 weeks)

**Task ID**: `fa180dc8-8a5d-496d-a1a5-fd8163e8d99f`
**Priority**: Critical
**Assignees**: coding-agent, system-architect-agent
**Dependencies**: Phase 6 complete

### Objective
Remove business logic from MCP controllers - controllers should only handle HTTP/MCP concerns.

### Target Files
- `interface/mcp_controllers/task_mcp_controller/task_mcp_controller.py:420-446`

### Extract To
- **Parameter transformation** → Application DTOs
- **Validation** → Domain entities
- **Permission checking** → Application authorization service

### Success Criteria
✅ Controllers only handle HTTP/MCP concerns
✅ No business logic in interface layer
✅ Clean separation of concerns
✅ All functionality preserved

---

## 🎯 Phase 8: Legacy Code Cleanup (1 week)

**Task ID**: `aaffe1c8-714e-4128-804f-4938cee06f00`
**Priority**: Low
**Assignees**: test-orchestrator-agent, coding-agent
**Dependencies**: All phases 1-7 complete

### Objective
Remove all feature flags and legacy code paths after successful migration.

### Cleanup Tasks
- Remove `FEATURE_RICH_DOMAIN_MODEL` flag
- Remove `FEATURE_CLEAN_REPOSITORIES` flag
- Remove `FEATURE_APPLICATION_ORCHESTRATOR` flag
- Delete legacy code paths
- Remove adapter classes
- Update documentation

### Success Criteria
✅ All feature flags removed
✅ Single code path (new DDD-compliant)
✅ No legacy code remaining
✅ Performance benchmarks confirm no regression
✅ Full test suite passes

---

## 📊 Task Dependency Graph

```
Phase 1: Rich Domain Models (2w)
    ↓
Phase 2: Clean Repository Pattern (1w)
    ↓
Phase 3: Move Orchestrator to Application (1w)
    ↓
Phase 4: Value Objects for Type Safety (2w)
    ↓
Phase 5: Domain Events Pattern (2w)
    ↓
Phase 6: Thin Application Services (2w)
    ↓
Phase 7: Clean MCP Controllers (2w)
    ↓
Phase 8: Legacy Code Cleanup (1w)
```

**Total Timeline**: 13 weeks (sequential) or ~18 weeks (with testing and reviews)

---

## 🚀 Getting Started

### 1. View All Tasks
```bash
# List all DDD refactoring tasks
mcp__agenthub_http__manage_task(action="list", git_branch_id="9e94fa57-e01a-4f8b-ab54-e9cb6fac3bab")
```

### 2. Start Phase 1
```bash
# Mark Phase 1 task as in progress
mcp__agenthub_http__manage_task(
    action="update",
    task_id="3fc56e2b-f42b-47bf-bd09-5adc359a51c9",
    status="in_progress"
)
```

### 3. Delegate First Subtask
```bash
# Delegate subtask 1.1 to coding-agent
Task(
    subagent_type="coding-agent",
    prompt="task_id: 3fc56e2b-f42b-47bf-bd09-5adc359a51c9, subtask_id: df75e69f-bac9-4555-a831-5bf3e3e83e8c"
)
```

---

## 📝 Agent Assignment Summary

| Agent Type | Primary Phases | Total Assignments |
|------------|---------------|-------------------|
| coding-agent | All phases | 8 parent + multiple subtasks |
| system-architect-agent | All phases | 8 parent tasks |
| test-orchestrator-agent | Phases 1, 2, 8 | Testing tasks |

---

## ⚠️ Critical Success Factors

1. **Feature Flags**: Every phase uses feature flags for zero-downtime migration
2. **Testing**: Comprehensive testing at each phase before proceeding
3. **Backward Compatibility**: Maintain legacy behavior until final cleanup (Phase 8)
4. **Documentation**: Update technical docs as changes are implemented
5. **Code Review**: System-architect-agent reviews all architectural changes

---

## 📚 Related Documentation

- **DDD Compliance Review**: `ai_docs/reports-status/ddd-compliance-review-2025-10-09.md`
- **Implementation Plan**: `ai_docs/development-guides/ddd-refactoring-implementation-plan.md`
- **This Roadmap**: `ai_docs/development-guides/ddd-refactoring-task-roadmap.md`

---

## 🎯 Next Actions

1. Review this roadmap with team
2. Begin Phase 1 implementation
3. Monitor progress via MCP task updates
4. Conduct code reviews after each phase
5. Update documentation as changes are deployed

---

**Generated by**: Master Orchestrator Agent
**Date**: 2025-10-09
**Project**: 4genthub DDD Refactoring Initiative
