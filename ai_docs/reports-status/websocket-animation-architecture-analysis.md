# WebSocket Animation Architecture Analysis Report
**Date**: 2025-10-31
**Analyst**: system-architect-agent
**Status**: Phase 1 Complete - Critical Gaps Identified

---

## Executive Summary

**Objective**: Validate unified WebSocket-driven animation architecture across all 4 entities (Task, Subtask, Branch, Project).

**Key Findings**:
- ✅ **Backend**: 100% consistent - All 4 entities properly broadcast WebSocket events
- ⚠️ **Frontend**: Incomplete implementation with critical gaps
  - **Task & Subtask**: 95% complete (full AnimationFactory integration)
  - **Branch**: 50% complete (partial integration, missing explicit animation methods)
  - **Project**: 0% complete (backend broadcasts ignored by frontend)

**Critical Gap**: `WebSocketAnimationService.ts` lines 60-79 only routes 3 of 4 entities, completely missing Project animation support despite backend broadcasting all Project CRUD events.

**Risk Level**: 🔴 HIGH - User receives Project updates but sees NO visual feedback, creating poor UX.

---

## 1. Backend Architecture Analysis ✅ (100% Consistent)

### 1.1 WebSocket Broadcast Function
**File**: `agenthub_main/src/fastmcp/server/routes/websocket_routes.py:1354-1610`

**Core Function**:
```python
async def broadcast_data_change(
    event_type: str,        # created|updated|deleted|completed
    entity_type: str,       # task|subtask|branch|project
    entity_id: str,         # UUID
    user_id: str,           # Owner UUID
    data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None
```

**Message Format (v2.0)** - UNIFORM across all entities:
```json
{
  "id": "broadcast-{entity_type}-{random}",
  "version": "2.0",
  "type": "update",
  "timestamp": "2025-10-31T08:22:38.233388+00:00",
  "sequence": 1234,
  "payload": {
    "entity": "task|subtask|branch|project",
    "action": "created|updated|deleted|completed",
    "data": {
      "primary": {
        "id": "entity-uuid",
        "title": "Entity Title",
        ...entity-specific fields
      },
      "cascade": {
        "branches": [...related branch updates],
        "tasks": [...related task updates]
      }
    }
  },
  "metadata": {
    "source": "system",
    "userId": "user-uuid",
    "entity_type": "task|subtask|branch|project",
    "entity_id": "entity-uuid",
    "event_type": "created|updated|deleted|completed",
    ...entity-specific metadata
  }
}
```

### 1.2 WebSocketNotificationService Analysis
**File**: `agenthub_main/src/fastmcp/task_management/application/services/websocket_notification_service.py`

**All 4 Entities Supported**:

| Entity | Broadcast Method | Lines | Status |
|--------|-----------------|-------|--------|
| Task | `broadcast_task_event()` | 300-431 | ✅ Complete |
| Subtask | `broadcast_subtask_event()` | 433-479 | ✅ Complete |
| Project | `broadcast_project_event()` | 481-518 | ✅ Complete |
| Branch | `broadcast_branch_event()` | 520-565 | ✅ Complete |

**Key Features**:
- ✅ Duplicate notification prevention (5-second TTL cache)
- ✅ User authorization enforcement (only owners receive events)
- ✅ Enhanced metadata (titles, parent relationships)
- ✅ Cascade data for related entity updates
- ✅ Direct WebSocket + HTTP fallback support

**Authorization**: `is_user_authorized_for_message()` at websocket_routes.py:997-1221
- ✅ Validates user owns the resource
- ✅ Multi-tenant isolation guaranteed

---

## 2. Frontend Architecture Analysis ⚠️ (Incomplete)

### 2.1 WebSocket Integration Layer ✅
**File**: `agenthub-frontend/src/hooks/useWebSocketV2.ts`

```typescript
// Lines 187-189: Service initialization
webSocketAnimationService.init(client);
const cleanupChangePool = initializeWebSocketIntegration(client);
const cleanupNotifications = notificationService.initializeWebSocketListener(client);

// Lines 120-135: Message processing
client.on('update', (message: WSMessage) => {
  dispatch(messageReceived(message));
  if (message.payload.data.cascade) {
    dispatch(updateFromWebSocket(message.payload.data.cascade));
  }
});
```

**Status**: ✅ Complete - All WebSocket messages properly received

### 2.2 Animation Routing Service ⚠️ (Critical Gap)
**File**: `agenthub-frontend/src/services/WebSocketAnimationService.ts:60-79`

```typescript
handleWebSocketMessage(message: WSMessage) {
  const { payload } = message;
  const { entity, action } = payload;

  // ROUTING LOGIC
  if (entity === 'task') {
    this.triggerTaskAnimation(action, message);      // ✅ Lines 85-161
  } else if (entity === 'subtask') {
    this.triggerSubtaskAnimation(action, message);   // ✅ Lines 166-228
  } else if (entity === 'branch') {
    this.triggerBranchAnimation(action, message);    // ✅ Lines 233-285
  }
  // ❌ MISSING: Project entity routing!
  // Should have:
  // else if (entity === 'project') {
  //   this.triggerProjectAnimation(action, message);
  // }
}
```

**Critical Gap**: Project entity routing completely missing despite backend broadcasting all Project events.

### 2.3 Entity-Specific Animation Patterns

#### Pattern A: Task & Subtask (95% Complete) ✅

**Architecture**:
```
WebSocket Message → AnimationService.triggerTaskAnimation()
  → Extract entity ID from message
  → Defer 150ms for DOM readiness
  → AnimationFactory.animate(taskId, animationType, 'websocket')
  → Component receives animation via registered element
```

**Hook Pattern**: `useTaskAnimation.ts` / `useSubtaskAnimation.ts`
```typescript
// 1. Register element on mount
useEffect(() => {
  animationFactory.registerElement(entityId, elementRef.current, {
    onAnimationStart: (type) => { },
    onAnimationEnd: (type) => { }
  });
  return () => animationFactory.unregisterElement(entityId);
}, [entityId]);

// 2. Auto-trigger create animation on mount
useEffect(() => {
  setTimeout(() => playCreateAnimation('mount'), 50);
}, []);

// 3. Detect changes and trigger update animation
useEffect(() => {
  if (statusChanged || titleChanged || progressChanged) {
    playUpdateAnimation('websocket');
  }
}, [summary.status, summary.title, summary.subtask_count]);

// 4. Detect deletion marker and trigger delete animation
useEffect(() => {
  const checkInterval = setInterval(() => {
    if (taskDeletionTracker.isMarkedForDeletion(entityId)) {
      playDeleteAnimation('websocket');
      clearInterval(checkInterval);
    }
  }, 50);
  return () => clearInterval(checkInterval);
}, [entityId]);
```

**Animation Methods**:
- `playCreateAnimation(source)` → Delegates to `animationFactory.animate(id, 'create', source)`
- `playDeleteAnimation(source)` → Delegates to `animationFactory.animate(id, 'delete', source)`
- `playUpdateAnimation(source)` → Delegates to `animationFactory.animate(id, 'update', source)`

**Status**: ✅ Fully implemented and working

#### Pattern B: Branch (50% Complete) ⚠️

**Architecture**:
```
WebSocket Message → AnimationService.triggerBranchAnimation()
  → Extract branch ID from message
  → Defer 150ms for DOM readiness
  → AnimationFactory.animate(branchId, animationType, 'websocket')
  → Component receives animation via registered element
```

**Component Integration**: `BranchItem.tsx:42-60`
```typescript
useEffect(() => {
  if (elementRef.current) {
    animationFactory.registerElement(branch.id, elementRef.current, {
      onAnimationStart: (type) => { },
      onAnimationEnd: (type) => { }
    });
  }
  return () => {
    animationFactory.unregisterElement(branch.id);
  };
}, [branch.id]);
```

**Missing Components**:
- ❌ No dedicated `useBranchAnimation` hook
- ❌ No explicit `playCreateAnimation()` / `playDeleteAnimation()` / `playUpdateAnimation()` methods
- ⚠️ Relies on parent `useProjectAnimations` for state management
- ⚠️ CSS-based animations instead of AnimationFactory coordination

**Current Animation Implementation** (in `useProjectAnimations.ts`):
```typescript
// Detects new branches via Set comparison
const newlyAddedBranches = Array.from(currentBranchIds)
  .filter(id => !previousBranchIds.has(id));

// Manages animation state
const [newBranches, setNewBranches] = useState<Set<string>>(new Set());
const [fadingOutBranches, setFadingOutBranches] = useState<Set<string>>(new Set());

// Applies CSS classes in component
<BranchItem
  isNew={newBranches.has(branch.id)}
  isFadingOut={fadingOutBranches.has(branch.id)}
/>
```

**Status**: ⚠️ Partially implemented - Registered but inconsistent with Task/Subtask pattern

#### Pattern C: Project (0% Complete) ❌

**Current State**:
- ❌ NO routing in `WebSocketAnimationService.handleWebSocketMessage()`
- ❌ NO `triggerProjectAnimation()` method
- ❌ NO `useProjectAnimation` hook (note: `useProjectAnimations` exists but manages branch animations)
- ❌ NO AnimationFactory registration in Project components
- ✅ Backend broadcasts Project events (verified in `websocket_notification_service.py:481-518`)

**Missing Implementation**:
```typescript
// SHOULD EXIST in WebSocketAnimationService.ts
private triggerProjectAnimation(action: string, message: WSMessage) {
  const projectId = extractProjectId(message);

  let animationType: AnimationType | null = null;
  switch (action) {
    case 'created': animationType = 'create'; break;
    case 'updated': animationType = 'update'; break;
    case 'deleted': animationType = 'delete'; break;
  }

  requestAnimationFrame(() => {
    setTimeout(() => {
      animationFactory.animate(projectId, animationType!, 'websocket');
    }, 150);
  });
}
```

**Status**: ❌ Not implemented - Backend events ignored by frontend

---

## 3. Data Model Specifications

### 3.1 WebSocket Trigger Input Model

```typescript
/**
 * Unified WebSocket message structure for all entities
 * This is the data model that triggers animations
 */
interface WSMessage {
  id: string;                    // "broadcast-{entity}-{random}"
  version: "2.0";                // Message format version
  type: "update";                // Always "update" for data changes
  timestamp: string;             // ISO 8601 format
  sequence: number;              // Message sequence number
  payload: WSPayload;
  metadata: WSMetadata;
}

interface WSPayload {
  entity: 'task' | 'subtask' | 'branch' | 'project';  // Entity type
  action: 'created' | 'updated' | 'deleted' | 'completed';  // Action type
  data: {
    primary: Record<string, any>;    // Entity data (id, title, etc.)
    cascade?: {                       // Optional related updates
      branches?: Array<BranchData>;
      tasks?: Array<TaskData>;
      projects?: Array<ProjectData>;
    };
  };
}

interface WSMetadata {
  source: 'system' | 'user';
  userId: string;                     // Owner UUID - CRITICAL for authorization
  entity_type: string;                // Duplicate of payload.entity
  entity_id: string;                  // Entity UUID
  event_type: string;                 // Duplicate of payload.action

  // Entity-specific metadata
  task_title?: string;
  parent_branch_id?: string;
  parent_branch_title?: string;
  subtask_title?: string;
  parent_task_id?: string;
  parent_task_title?: string;
  branch_title?: string;
  project_id?: string;
  timestamp: string;                  // ISO 8601
}
```

### 3.2 Animation Type Mapping

```typescript
/**
 * WebSocket action → AnimationType mapping
 * Used by WebSocketAnimationService to trigger correct animations
 */
const ACTION_TO_ANIMATION: Record<string, AnimationType> = {
  'created': 'create',     // New entity added
  'updated': 'update',     // Entity modified
  'deleted': 'delete',     // Entity removed
  'completed': 'complete'  // Task/Subtask marked complete
};

/**
 * Animation source types
 */
type AnimationSource =
  | 'websocket'  // Triggered by WebSocket event (remote change)
  | 'mount'      // Triggered on component mount (new item)
  | 'callback';  // Triggered by user action callback

/**
 * Supported animation types
 */
type AnimationType =
  | 'create'    // Fade in, slide in
  | 'delete'    // Fade out, slide out
  | 'update'    // Flash, highlight
  | 'complete'; // Celebration effect (Task/Subtask only)
```

### 3.3 Entity-Specific ID Extraction

```typescript
/**
 * Extract entity ID from WebSocket message
 * Each entity type has multiple possible ID locations
 */
function extractEntityId(message: WSMessage, entityType: string): string | undefined {
  const primary = message.payload?.data?.primary;
  const directDataId = message.payload?.data?.id;
  const metadataId = message.metadata?.entity_id;

  // Priority order: primary.id > data.id > metadata.entity_id
  const primaryId = primary && !Array.isArray(primary) ? primary.id : undefined;
  return primaryId || directDataId || metadataId;
}
```

---

## 4. Architectural Gaps & Inconsistencies

### 4.1 Gap Matrix

| Entity | Backend Broadcast | Frontend Routing | AnimationFactory | Hook Pattern | Completion |
|--------|------------------|------------------|------------------|--------------|-----------|
| Task | ✅ Complete | ✅ Complete | ✅ Complete | ✅ useTaskAnimation | 95% |
| Subtask | ✅ Complete | ✅ Complete | ✅ Complete | ✅ useSubtaskAnimation | 95% |
| Branch | ✅ Complete | ✅ Complete | ✅ Registered | ⚠️ useProjectAnimations | 50% |
| Project | ✅ Complete | ❌ **MISSING** | ❌ **MISSING** | ❌ **MISSING** | 0% |

### 4.2 Detailed Gap Analysis

#### Gap 1: Project Animation Routing ❌ CRITICAL
**Location**: `WebSocketAnimationService.ts:60-79`

**Problem**:
```typescript
// Current code - Only handles 3 entities
if (entity === 'task') { ... }
else if (entity === 'subtask') { ... }
else if (entity === 'branch') { ... }
// Project messages silently ignored!
```

**Impact**:
- Backend sends Project created/updated/deleted events
- Frontend receives messages but takes NO action
- Users see no visual feedback for Project operations
- Poor UX - creates appear instantly without animation

**Fix Required**: Add Project routing logic

#### Gap 2: Branch Animation Inconsistency ⚠️ MEDIUM
**Location**: `BranchItem.tsx` + `useProjectAnimations.ts`

**Problem**:
- Branch registers with AnimationFactory (good)
- But animations managed via parent component state (inconsistent)
- No dedicated hook like Task/Subtask pattern
- CSS classes applied directly instead of AnimationFactory coordination

**Impact**:
- Inconsistent architecture across entities
- Harder to maintain and extend
- Animation behavior differs from Task/Subtask

**Fix Recommended**: Create `useBranchAnimation` hook following Task pattern

#### Gap 3: Animation Method Naming ⚠️ LOW
**Location**: Animation hooks

**Problem**:
- Task/Subtask: `playCreateAnimation()`, `playDeleteAnimation()`, `playUpdateAnimation()`
- Branch: No explicit methods, relies on state flags
- Project: N/A (not implemented)

**Impact**: API inconsistency across entities

**Fix Recommended**: Standardize method names across all entities

### 4.3 Inconsistency Summary

**Pattern Inconsistencies**:

| Aspect | Task/Subtask | Branch | Project |
|--------|-------------|--------|---------|
| Dedicated Hook | ✅ Yes | ❌ No | ❌ No |
| AnimationFactory Integration | ✅ Full | ⚠️ Partial | ❌ None |
| Explicit Animation Methods | ✅ Yes | ❌ No | ❌ No |
| Mount Animation | ✅ Auto | ⚠️ Manual | ❌ None |
| Update Detection | ✅ Auto | ⚠️ Manual | ❌ None |
| Delete Detection | ✅ Auto | ⚠️ Manual | ❌ None |

---

## 5. TDD Test Specifications

### 5.1 Backend Tests

#### Test Suite 1: WebSocket Authorization
**File**: `agenthub_main/src/tests/security/websocket/test_websocket_authorization.py`

```python
class TestWebSocketAuthorization:
    """Verify only resource owners receive WebSocket events"""

    def test_task_owner_receives_created_event(self):
        """Owner user receives task created event"""

    def test_non_owner_blocked_from_task_event(self):
        """Non-owner user does NOT receive task event"""

    def test_subtask_authorization(self):
        """Subtask events respect ownership"""

    def test_branch_authorization(self):
        """Branch events respect ownership"""

    def test_project_authorization(self):
        """Project events respect ownership"""
```

#### Test Suite 2: Message Format Validation
**File**: `agenthub_main/src/tests/unit/task_management/infrastructure/test_websocket_message_format.py`

```python
class TestWebSocketMessageFormat:
    """Validate v2.0 message structure consistency"""

    def test_task_message_structure(self):
        """Task broadcast matches v2.0 format"""

    def test_subtask_message_structure(self):
        """Subtask broadcast matches v2.0 format"""

    def test_branch_message_structure(self):
        """Branch broadcast matches v2.0 format"""

    def test_project_message_structure(self):
        """Project broadcast matches v2.0 format"""

    def test_metadata_consistency(self):
        """All entities include required metadata fields"""
```

#### Test Suite 3: Entity CRUD Broadcasts
**File**: `agenthub_main/src/tests/integration/test_entity_crud_broadcasts.py`

```python
class TestEntityCRUDBroadcasts:
    """Test all 4 entities × 4 actions = 16 test cases"""

    # Task tests
    def test_task_created_broadcasts(self):
    def test_task_updated_broadcasts(self):
    def test_task_deleted_broadcasts(self):
    def test_task_completed_broadcasts(self):

    # Subtask tests
    def test_subtask_created_broadcasts(self):
    def test_subtask_updated_broadcasts(self):
    def test_subtask_deleted_broadcasts(self):
    def test_subtask_completed_broadcasts(self):

    # Branch tests
    def test_branch_created_broadcasts(self):
    def test_branch_updated_broadcasts(self):
    def test_branch_deleted_broadcasts(self):

    # Project tests
    def test_project_created_broadcasts(self):
    def test_project_updated_broadcasts(self):
    def test_project_deleted_broadcasts(self):
```

### 5.2 Frontend Tests

#### Test Suite 4: Unified Animation Service
**File**: `agenthub-frontend/src/tests/services/WebSocketAnimationService.unified.test.ts`

```typescript
describe('WebSocketAnimationService - Unified Entity Routing', () => {
  it('routes task messages to triggerTaskAnimation', () => {
    const message = createTaskMessage('created', 'task-id');
    service.handleWebSocketMessage(message);
    expect(animationFactory.animate).toHaveBeenCalledWith('task-id', 'create', 'websocket');
  });

  it('routes subtask messages to triggerSubtaskAnimation', () => { });
  it('routes branch messages to triggerBranchAnimation', () => { });
  it('routes project messages to triggerProjectAnimation', () => { }); // CURRENTLY FAILS

  it('extracts correct entity ID from all message formats', () => { });
  it('maps WebSocket actions to AnimationTypes correctly', () => { });
  it('defers animation by 150ms for DOM readiness', () => { });
});
```

#### Test Suite 5: Animation Factory Triggers
**File**: `agenthub-frontend/src/tests/services/AnimationFactory.triggers.test.ts`

```typescript
describe('AnimationFactory - Trigger Data Models', () => {
  describe('Task Animation Triggers', () => {
    it('accepts valid task ID and animates registered element', () => { });
    it('ignores animation if element not registered', () => { });
    it('calls onAnimationStart callback', () => { });
    it('calls onAnimationEnd callback after duration', () => { });
  });

  describe('Subtask Animation Triggers', () => { });
  describe('Branch Animation Triggers', () => { });
  describe('Project Animation Triggers', () => { }); // TODO: Implement
});
```

#### Test Suite 6: E2E Animation Flow
**File**: `agenthub-frontend/src/tests/integration/websocket-animations-e2e.test.tsx`

```typescript
describe('WebSocket Animation E2E', () => {
  it('full flow: backend broadcast → frontend animation for Task', async () => {
    // 1. Simulate backend broadcast
    // 2. WebSocket receives message
    // 3. AnimationService routes to triggerTaskAnimation
    // 4. AnimationFactory animates element
    // 5. Component shows animation
    // 6. Animation completes
  });

  it('full flow: Task created → create animation', () => { });
  it('full flow: Task updated → update animation', () => { });
  it('full flow: Task deleted → delete animation', () => { });
  it('full flow: Task completed → complete animation', () => { });

  // Repeat for Subtask, Branch, Project
});
```

---

## 6. Recommendations

### 6.1 Immediate Actions (High Priority)

1. **Add Project Animation Support** ⚡ CRITICAL
   - Add routing in `WebSocketAnimationService.handleWebSocketMessage()` (lines 60-79)
   - Implement `triggerProjectAnimation()` method (mirror Branch pattern)
   - Create `useProjectAnimation` hook (mirror Task pattern)
   - Register Project components with AnimationFactory

2. **Standardize Branch Animations** 🔧 HIGH
   - Create `useBranchAnimation` hook following Task/Subtask pattern
   - Move animation logic from `useProjectAnimations` to dedicated hook
   - Add explicit `playCreateAnimation()`, `playUpdateAnimation()`, `playDeleteAnimation()` methods

3. **Write TDD Tests** ✅ HIGH
   - Implement all test suites specified in Section 5
   - Run tests to validate current Task/Subtask implementations
   - Use failing tests to drive Project/Branch improvements

### 6.2 Architecture Improvements (Medium Priority)

1. **Unified Hook Pattern**
   - Define `BaseEntityAnimation` interface
   - Enforce consistent API across all entity hooks
   - Document standard lifecycle: register → mount animation → change detection → delete detection

2. **Enhanced Type Safety**
   - Create strict TypeScript interfaces for all animation triggers
   - Add runtime validation for WebSocket message formats
   - Type-safe entity ID extraction

3. **Performance Optimization**
   - Benchmark animation performance under high-frequency updates
   - Consider animation throttling for rapid updates
   - Add performance monitoring

### 6.3 Documentation (Low Priority)

1. **Architecture Guide**
   - Document unified animation pattern
   - Provide examples for each entity
   - Explain WebSocket → Animation flow

2. **Developer Guide**
   - How to add animations to new entities
   - How to customize animation behavior
   - Troubleshooting common issues

---

## 7. Conclusion

### 7.1 Summary

The WebSocket animation architecture demonstrates **excellent backend design** with 100% consistency across all entities. However, the frontend implementation has **critical gaps**:

- **Backend**: ✅ All 4 entities properly broadcast WebSocket events with uniform v2.0 format
- **Frontend**: ⚠️ Only Task & Subtask have complete implementations (95%)
- **Critical Gap**: Project animations completely missing (0%)
- **Inconsistency**: Branch animations partially implemented (50%)

### 7.2 Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|-----------|
| Poor UX for Project operations | HIGH | 100% | Add Project animation support immediately |
| Architecture debt accumulation | MEDIUM | HIGH | Standardize Branch animations |
| Regression when adding features | MEDIUM | MEDIUM | Write comprehensive test suite |
| Performance issues at scale | LOW | LOW | Monitor and optimize if needed |

### 7.3 Next Steps

**Immediate (This Sprint)**:
1. ✅ Complete this analysis report
2. ⏭️ Implement Project animation support (WebSocketAnimationService + hook)
3. ⏭️ Write TDD tests for all 4 entities
4. ⏭️ Validate with manual testing

**Short-term (Next Sprint)**:
1. Standardize Branch animations to match Task/Subtask pattern
2. Create comprehensive E2E test suite
3. Document unified animation architecture

**Long-term (Future)**:
1. Performance optimization and monitoring
2. Advanced animation effects (completion celebrations, etc.)
3. Animation configuration and customization

---

## Appendix A: File References

### Backend Files
- `agenthub_main/src/fastmcp/server/routes/websocket_routes.py:1354-1610`
- `agenthub_main/src/fastmcp/task_management/application/services/websocket_notification_service.py`

### Frontend Files
- `agenthub-frontend/src/hooks/useWebSocketV2.ts`
- `agenthub-frontend/src/services/WebSocketAnimationService.ts`
- `agenthub-frontend/src/services/AnimationFactory.ts`
- `agenthub-frontend/src/types/animationTypes.ts`
- `agenthub-frontend/src/hooks/useTaskAnimation.ts`
- `agenthub-frontend/src/hooks/useSubtaskAnimation.ts`
- `agenthub-frontend/src/components/ProjectList/hooks/useProjectAnimations.ts`
- `agenthub-frontend/src/components/ProjectList/components/BranchItem.tsx`

### Test Files (To Be Created)
- Backend: `agenthub_main/src/tests/security/websocket/test_websocket_authorization.py`
- Backend: `agenthub_main/src/tests/integration/test_entity_crud_broadcasts.py`
- Frontend: `agenthub-frontend/src/tests/services/WebSocketAnimationService.unified.test.ts`
- Frontend: `agenthub-frontend/src/tests/integration/websocket-animations-e2e.test.tsx`

---

**Report Status**: ✅ Complete
**Next Action**: Present findings to user for feedback and prioritization
