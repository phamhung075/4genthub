# Toast Notification Architecture (Token-Optimized)

## System Overview

**Toast notifications in agenthub are triggered exclusively by WebSocket events**, with global deduplication to prevent spam. Components use only error toasts for client-side validation failures.

### Core Principle
> **WebSocket is the single source of truth for success notifications**. Components trigger error toasts only for client-side failures that don't reach the API.

---

## Architecture Layers

| Layer | Component | Purpose | Location |
|-------|-----------|---------|----------|
| **UI** | `ToastProvider` + `ToastContainer` | React Context, visual rendering | `toast.tsx` |
| **Integration** | `useRealtimeSync` | WebSocket handler, cache sync, toast triggering | `useRealtimeSync.ts` |
| **Data Source** | WebSocket v2.0 | Real-time entity updates from backend | `useWebSocketV2.ts` |

**Flow**: WebSocket message → `useRealtimeSync` → Global deduplication → Toast hook → Context → UI

---

## Key Files

### 1. `toast.tsx` (267 lines)

**Exports**:
- `ToastProvider` - React Context wrapping entire app
- `ToastContainer` - Visual toast rendering
- `useToast()` - Base hook (returns `showToast`, `dismissToast`, `dismissAll`)
- `useSuccessToast()` - Convenience hook for success messages
- `useErrorToast()` - Convenience hook for errors (8s duration)
- `useWarningToast()` - Convenience hook for warnings
- `useInfoToast()` - Convenience hook for info messages

**Toast Types**:
| Type | Icon | Duration | Use Case |
|------|------|----------|----------|
| `success` | CheckCircle | 5s | Operation completed (WebSocket only) |
| `error` | XCircle | 8s | Client validation failures |
| `warning` | AlertCircle | 5s | Deletions (WebSocket only) |
| `info` | Info | 5s | Updates (WebSocket only) |

**Features**:
- Auto-dismiss with pause on hover
- Stacking with animation delays (100ms per toast)
- Design system colors (success/error/warning/info variants)
- Action buttons (optional)

### 2. `useRealtimeSync.ts` (955 lines)

**Responsibility**: **Single source of truth for all toast notifications**

**Key Features**:
- Handles WebSocket v2.0 protocol messages
- Updates React Query cache with delays for animations
- **Global toast deduplication** (prevents duplicates from multiple hook instances)
- Triggers all success/info/warning toasts

**Deduplication Logic** (lines 17-65):
```typescript
// Global map shared across ALL hook instances
const globalRecentToastsMap = new Map<string, number>();

// Only show toast if not shown in last 2 seconds
const showToastOnce = (key: string, showFn: () => void) => {
  const now = Date.now();
  const lastShown = globalRecentToastsMap.get(key);

  if (!lastShown || now - lastShown > 2000) {
    showFn();
    globalRecentToastsMap.set(key, now);
  }
}
```

**Toast Triggers by Entity**:

| Entity | Actions | Toast Type | Key Format |
|--------|---------|-----------|-----------|
| **Task** | created | success | `task-created-${id}` |
| | updated | info (if not system) | `task-updated-${id}` |
| | completed | success | `task-completed-${id}` |
| | deleted | warning | `task-deleted-${id}` |
| **Subtask** | created | success | `subtask-created-${id}` |
| | updated | info | `subtask-updated-${id}` |
| | completed | success | `subtask-completed-${id}` |
| | deleted | warning | `subtask-deleted-${id}` |
| **Project** | created | success | `project-created-${id}` |
| | updated | info | `project-updated-${id}` |
| | deleted | warning | `project-deleted-${id}` |
| **Branch** | created | success | `branch-created-${id}` |
| | updated | info | `branch-updated-${id}` |
| | deleted | warning | `branch-deleted-${id}` |
| **Agent** | created | success | `agent-created-${id}` |
| | updated | info | `agent-updated-${id}` |
| | deleted | warning | `agent-deleted-${id}` |

**Critical Implementation Details**:

```typescript
// Suppress automatic task updates (subtask count changes)
const isAutomaticUpdate = message.metadata?.source === 'system' ||
                          message.metadata?.event_type === 'subtask_count_update';
if (!isAutomaticUpdate) {
  showToastOnce(`task-updated-${taskId}`, () => {
    showInfo(`Task "${taskTitle}" updated`);
  });
}
```

**Animation Coordination**:
- **DELETE**: Toast shown FIRST, cache update delayed 600ms (allows delete animation)
- **UPDATE**: Toast shown immediately, cache update delayed 150ms (allows update animation)
- **COMPLETE**: Toast shown FIRST, cache update delayed 150ms (allows completion animation)
- **CREATE**: Toast + cache update immediate (no animation delay needed)

### 3. Component Usage

**LazyTaskListRefactored.tsx** (line 27):
```typescript
const showError = useErrorToast();
// ONLY error toasts - success handled by WebSocket
```

**LazySubtaskListRefactored.tsx** (line 58):
```typescript
const showErrorToast = useErrorToast();
// ONLY error toasts - success handled by WebSocket
```

**Why components don't use success toasts**:
- **Problem**: Duplicate toasts (component + WebSocket both triggering)
- **Solution**: Components handle ONLY client-side validation errors
- **API operations**: WebSocket broadcasts success → `useRealtimeSync` shows toast

---

## Data Flow (Actual Implementation)

### Success Flow (API Operation)
```
User clicks "Create Task"
↓
Component calls API mutation
↓
API creates task
↓
WebSocket broadcasts "task created" message
↓
useRealtimeSync receives message
↓
Global deduplication check (2s window)
↓
showToastOnce(`task-created-${id}`, () => showSuccess(...))
↓
ToastProvider adds toast to context
↓
ToastContainer renders toast
↓
Auto-dismiss after 5s (pauses on hover)
```

### Error Flow (Client Validation)
```
User enters invalid data
↓
Component validation fails
↓
Component calls showErrorToast("Invalid data")
↓
ToastProvider adds toast to context
↓
ToastContainer renders toast (8s duration)
```

---

## Best Practices

### ✅ DO

| Practice | Reason |
|----------|--------|
| **Use `useErrorToast` in components** | Client-side validation failures |
| **Let WebSocket handle success** | Prevents duplicates, consistent UX |
| **Trust global deduplication** | Handles multiple hook instances |
| **Keep messages concise** | Toast titles <50 chars |

### ❌ DON'T

| Practice | Why Not |
|----------|---------|
| **Call success toast in components** | WebSocket already shows it → duplicates |
| **Show toasts for every update** | Spam users (automatic updates suppressed) |
| **Override deduplication** | Breaks spam prevention |
| **Use toasts for long messages** | Max 2 lines description |

---

## Configuration

### Toast Durations

| Type | Default | Override | Use Case |
|------|---------|----------|----------|
| success | 5000ms | `duration: 3000` | Quick confirmations |
| error | 8000ms | `duration: 10000` | Critical errors needing attention |
| warning | 5000ms | `duration: 6000` | Deletions, important warnings |
| info | 5000ms | `duration: 4000` | Informational updates |

### Deduplication Window

**Global**: 2000ms (2 seconds) in `useRealtimeSync.ts:46`

**Cleanup**: Toast keys removed after 5s (line 51-56)

---

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| **No toast appears** | WebSocket disconnected | Check `useWebSocket` connection status |
| **Duplicate toasts** | Component calling success toast | Remove component toast, rely on WebSocket |
| **Toast shows but no cache update** | Animation timing mismatch | Check setTimeout delays (150ms/600ms) |
| **Automatic update toasts spamming** | Missing system source check | Verify `isAutomaticUpdate` logic (line 163-171) |

---

## WebSocket v2.0 Integration

**Setup** (in `App.tsx` or layout component):
```typescript
const { user, tokens } = useAuth();
const webSocketClient = useWebSocket(user?.id || '', tokens?.access_token || '');
useRealtimeSync(webSocketClient.client, true);
```

**Message Format** (WebSocket v2.0 Protocol):
```typescript
{
  version: "2.0",
  type: "update",
  payload: {
    entity: "task" | "subtask" | "project" | "branch" | "agent",
    action: "created" | "updated" | "completed" | "deleted",
    data: {
      primary: { ...entityData },
      cascade: { ...relatedEntities }
    }
  },
  metadata: {
    source: "user" | "system",
    event_type?: "subtask_count_update"
  }
}
```

---

## Implementation Examples

### Component Error Toast
```typescript
// ✅ CORRECT: Component validates, shows error
const handleSubmit = async () => {
  if (!title.trim()) {
    showErrorToast("Title is required");
    return;
  }

  // API handles success toast via WebSocket
  await createTask({ title });
};
```

### WebSocket Success Toast
```typescript
// ✅ CORRECT: useRealtimeSync handles WebSocket messages
switch (action) {
  case 'created':
    showToastOnce(`task-created-${taskId}`, () => {
      showSuccess(`Task "${taskTitle}" created successfully`);
    });
    break;
}
```

### ❌ WRONG: Component Success Toast
```typescript
// ❌ WRONG: Creates duplicate (component + WebSocket)
const handleSubmit = async () => {
  await createTask({ title });
  showSuccessToast("Task created"); // DON'T DO THIS
};
```

---

## Memory Management

**Automatic Cleanup**:
1. **Toast auto-dismiss**: Timers cleaned up on unmount (toast.tsx:77-82)
2. **Deduplication map**: Keys removed after 5s (useRealtimeSync.ts:51-56)
3. **WebSocket listeners**: Unsubscribed on hook cleanup (useRealtimeSync.ts:943-947)

**Performance**:
- Global deduplication prevents O(n²) duplicate checks
- Toast keys are UUIDs + entity IDs (unique, collision-free)
- Map cleanup prevents memory leaks

---

## Testing Toast System

### Manual Testing
```typescript
// 1. Test WebSocket toast (use browser console)
// Trigger task creation → verify single success toast

// 2. Test deduplication
// Rapid task updates → verify single info toast

// 3. Test component error
// Submit invalid form → verify error toast (8s duration)

// 4. Test animation coordination
// Delete task → verify toast shows, then item disappears (600ms delay)
```

### Verification Checklist
- [ ] WebSocket connected (`useWebSocket.isConnected`)
- [ ] `useRealtimeSync` hook active
- [ ] No component-level success toasts (only errors)
- [ ] Toasts auto-dismiss after duration
- [ ] Pause-on-hover works
- [ ] No duplicate toasts (global deduplication working)

---

## Migration from Legacy System

**Before (DEPRECATED - does not exist in codebase)**:
- `toastEventBus` service
- `NotificationService` with 5s deduplication
- `WebSocketToastBridge` component
- Dual deduplication (1s + 5s)

**After (CURRENT - as of WebSocket v2.0 refactor 2025-11-07)**:
- Direct toast hooks in `toast.tsx`
- Single deduplication in `useRealtimeSync` (2s global)
- No bridge component needed
- Simplified architecture (70% fewer LOC)

**Key Changes**:
| Aspect | Old | New |
|--------|-----|-----|
| **Deduplication** | 2-tier (1s + 5s) | Single global (2s) |
| **Integration** | Bridge component | Direct hooks |
| **Location** | Separate services | `useRealtimeSync` |
| **Complexity** | 3 files, 500+ LOC | 1 file, 65 LOC |

---

## Summary

**Architecture**: WebSocket → `useRealtimeSync` (global dedup) → Toast hooks → Context → UI

**Key Files**:
- `toast.tsx` - React Context, hooks, UI components
- `useRealtimeSync.ts` - WebSocket handler, toast triggering, deduplication

**Deduplication**: Global `Map<string, number>` with 2s window, shared across all hook instances

**Component Usage**: **Error toasts only** - WebSocket handles all success notifications

**Animation Coordination**: Toast timing synced with cache updates (150ms/600ms delays)

**Result**: Zero duplicate toasts, consistent UX, minimal code (simplified in WebSocket v2.0 refactor)
