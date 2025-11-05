# State Management Implementation Patterns
## Refactoring Guide with Real agenthub Examples

**Date**: 2025-11-05
**Audience**: Developers
**Purpose**: Practical code examples for migrating to modern state management

---

## 🎯 Overview

This guide shows **real before/after examples** from the agenthub codebase, demonstrating how to refactor from current patterns to recommended modern patterns.

### What You'll Learn

1. Migrating data-fetching hooks to React Query
2. Simplifying Redux usage
3. Implementing proper Context patterns
4. Testing strategies for each pattern

---

## 📦 Pattern 1: API Data Fetching with React Query

### Current Pattern (Manual State Management)

**File**: `src/hooks/useBranchSummaries.ts` (80+ lines)

```typescript
/**
 * ❌ BEFORE: Manual state management with useState + useEffect
 * Problems:
 * - 80+ lines for basic data fetching
 * - No caching (refetch on every mount)
 * - Manual loading states
 * - Manual error handling
 * - Manual refresh logic
 * - Auto-refresh with setInterval (memory leaks possible)
 */

import { useEffect, useState, useCallback } from 'react';
import { branchService } from '../services/branchService';
import type { BranchSummary, ProjectSummary } from '../types/api.types';

export function useBranchSummaries(options = {}) {
  const { projectIds, autoRefresh = false, refreshInterval = 30000 } = options;

  // Manual state management
  const [summaries, setSummaries] = useState<BranchSummary[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSummaries = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      let result;

      if (projectIds?.length) {
        const branches = await branchService.loadProjectSummaries(projectIds);
        result = { branches, projects: [] };
      } else {
        result = await branchService.loadUserSummaries();
      }

      setSummaries(result.branches);
      setProjects(result.projects);

    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to load summaries';
      setError(errorMessage);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectIds]);

  const refresh = useCallback(async () => {
    await loadSummaries(true);
  }, [loadSummaries]);

  // Auto-refresh with setInterval
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        loadSummaries(true);
      }, refreshInterval);

      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, loadSummaries]);

  // Initial load
  useEffect(() => {
    loadSummaries();
  }, [loadSummaries]);

  return {
    summaries,
    projects,
    loading,
    refreshing,
    error,
    refresh
  };
}
```

---

### Recommended Pattern (React Query)

**File**: `src/hooks/useBranchSummaries.ts` (15 lines - 81% reduction!)

```typescript
/**
 * ✅ AFTER: React Query handles everything automatically
 * Benefits:
 * - 15 lines instead of 80+ (81% reduction!)
 * - Automatic caching (instant on cache hit)
 * - Automatic background revalidation
 * - Automatic retry on error
 * - Automatic request deduplication
 * - No memory leaks
 * - Built-in loading/error states
 * - DevTools integration
 */

import { useQuery } from '@tanstack/react-query';
import { branchService } from '../services/branchService';

export function useBranchSummaries(options = {}) {
  const { projectIds, autoRefresh = false, refreshInterval = 30000 } = options;

  return useQuery({
    queryKey: ['branchSummaries', projectIds],
    queryFn: async () => {
      if (projectIds?.length) {
        const branches = await branchService.loadProjectSummaries(projectIds);
        return { branches, projects: [] };
      }
      return branchService.loadUserSummaries();
    },
    staleTime: autoRefresh ? 0 : 5 * 60 * 1000, // 5 min cache if no auto-refresh
    refetchInterval: autoRefresh ? refreshInterval : false,
    refetchOnWindowFocus: true, // Auto-refresh when user returns to tab
  });
}

// Usage in component:
function ProjectList() {
  const { data, isLoading, error, refetch } = useBranchSummaries({
    autoRefresh: true,
    refreshInterval: 30000
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {data.branches.map(branch => <BranchCard key={branch.id} branch={branch} />)}
      <button onClick={() => refetch()}>Refresh</button>
    </div>
  );
}
```

**Key Improvements**:
- ✅ 81% less code (15 lines vs 80+)
- ✅ Instant UI on cache hit (better UX)
- ✅ Background revalidation (always fresh data)
- ✅ No memory leaks (auto cleanup)
- ✅ Request deduplication (multiple components = 1 request)
- ✅ Simpler testing (covered later)

---

## 📦 Pattern 2: Mutations (Create/Update/Delete)

### Current Pattern

```typescript
/**
 * ❌ BEFORE: Manual mutation handling
 * Problems:
 * - Manual refetch after mutation
 * - No optimistic updates
 * - Error handling verbose
 * - Loading state manual
 */

function CreateProjectForm() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: ProjectData) => {
    try {
      setLoading(true);
      setError(null);

      await createProject(data);

      // Manual refetch
      await refetchProjects();

      // Close form
      onSuccess();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && <div>Error: {error}</div>}
      {/* form fields */}
      <button disabled={loading}>
        {loading ? 'Creating...' : 'Create'}
      </button>
    </form>
  );
}
```

---

### Recommended Pattern (React Query Mutation)

```typescript
/**
 * ✅ AFTER: React Query mutation with optimistic updates
 * Benefits:
 * - Automatic cache invalidation
 * - Optimistic updates (instant UI)
 * - Automatic rollback on error
 * - Built-in loading/error states
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

function CreateProjectForm() {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: createProject,

    // Optimistic update: Update UI before server responds
    onMutate: async (newProject) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries(['projects']);

      // Snapshot previous value
      const previousProjects = queryClient.getQueryData(['projects']);

      // Optimistically update cache
      queryClient.setQueryData(['projects'], (old) => [...old, newProject]);

      // Return context for rollback
      return { previousProjects };
    },

    // Rollback on error
    onError: (err, newProject, context) => {
      queryClient.setQueryData(['projects'], context.previousProjects);
    },

    // Refetch after success
    onSuccess: () => {
      queryClient.invalidateQueries(['projects']);
    },
  });

  const handleSubmit = (data: ProjectData) => {
    createMutation.mutate(data, {
      onSuccess: () => onClose(),
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      {createMutation.error && (
        <div>Error: {createMutation.error.message}</div>
      )}
      {/* form fields */}
      <button disabled={createMutation.isLoading}>
        {createMutation.isLoading ? 'Creating...' : 'Create'}
      </button>
    </form>
  );
}
```

**Key Improvements**:
- ✅ Instant UI update (optimistic)
- ✅ Automatic rollback on error
- ✅ Automatic cache invalidation
- ✅ Single source of truth

---

## 📦 Pattern 3: WebSocket State (Keep Redux or Migrate to Zustand)

### Current Pattern (Redux)

**File**: `src/store/slices/webSocketSlice.ts`

```typescript
/**
 * ✅ CURRENT: Redux for WebSocket state (this is fine!)
 * Justification:
 * - Multiple components need connection state
 * - Connection state changes frequently
 * - Good for coordination
 *
 * Keep as-is unless test issues persist
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface WebSocketState {
  isConnected: boolean;
  isReconnecting: boolean;
  error: string | null;
}

const webSocketSlice = createSlice({
  name: 'websocket',
  initialState: {
    isConnected: false,
    isReconnecting: false,
    error: null,
  },
  reducers: {
    connected: (state) => {
      state.isConnected = true;
      state.isReconnecting = false;
    },
    disconnected: (state) => {
      state.isConnected = false;
      state.isReconnecting = true;
    },
    error: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
    },
  },
});

// Usage in component:
import { useAppSelector } from '../store/hooks';

function WebSocketStatus() {
  const isConnected = useAppSelector(state => state.websocket.isConnected);
  return <div>{isConnected ? '🟢 Connected' : '🔴 Disconnected'}</div>;
}
```

---

### Alternative Pattern (Zustand - if migrating from Redux)

**File**: `src/store/websocket.ts`

```typescript
/**
 * ⚠️ ALTERNATIVE: Zustand (if Redux causes test issues)
 * Benefits vs Redux:
 * - 94% smaller (3 KB vs 52 KB)
 * - No Provider needed
 * - Simpler API
 * - Better testing (no Provider hanging)
 */

import create from 'zustand';

interface WebSocketStore {
  isConnected: boolean;
  isReconnecting: boolean;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
  setError: (error: string) => void;
}

export const useWebSocketStore = create<WebSocketStore>((set) => ({
  isConnected: false,
  isReconnecting: false,
  error: null,

  connect: () => set({ isConnected: true, isReconnecting: false, error: null }),

  disconnect: () => set({ isConnected: false, isReconnecting: true }),

  setError: (error) => set({ error }),
}));

// Usage in component (no hooks import needed!):
function WebSocketStatus() {
  const isConnected = useWebSocketStore((state) => state.isConnected);
  return <div>{isConnected ? '🟢 Connected' : '🔴 Disconnected'}</div>;
}
```

**Migration Checklist**:
```typescript
// 1. Install Zustand
npm install zustand

// 2. Create Zustand store (above)

// 3. Replace Redux hooks gradually:
// ❌ Before
import { useAppSelector, useAppDispatch } from '../store/hooks';
const isConnected = useAppSelector(state => state.websocket.isConnected);
const dispatch = useAppDispatch();
dispatch(connected());

// ✅ After
import { useWebSocketStore } from '../store/websocket';
const isConnected = useWebSocketStore(state => state.isConnected);
const connect = useWebSocketStore(state => state.connect);
connect();

// 4. Remove Redux when all components migrated
```

---

## 📦 Pattern 4: Real-time Updates (WebSocket + React Query)

### Problem: Cascade Slice Underutilization

**Current**: Cascade slice stores WebSocket updates but UI rarely reads it

**Solution**: Update React Query cache directly from WebSocket

```typescript
/**
 * ✅ RECOMMENDED: WebSocket updates React Query cache
 * Benefits:
 * - Single source of truth (React Query)
 * - No need for cascade Redux slice
 * - Automatic UI updates
 * - Works with React Query DevTools
 */

// src/hooks/useTasksWithRealtime.ts
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { webSocketClient } from '../services/WebSocketClient';

export function useTasksWithRealtime(branchId: string) {
  const queryClient = useQueryClient();

  // 1. Fetch tasks via React Query
  const query = useQuery({
    queryKey: ['tasks', branchId],
    queryFn: () => listTasks({ git_branch_id: branchId }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // 2. Subscribe to WebSocket updates
  useEffect(() => {
    const handleTaskUpdate = (updatedTask: Task) => {
      // Update React Query cache directly!
      queryClient.setQueryData(['tasks', branchId], (oldTasks: Task[] = []) =>
        oldTasks.map(task => task.id === updatedTask.id ? updatedTask : task)
      );
    };

    const handleTaskCreate = (newTask: Task) => {
      queryClient.setQueryData(['tasks', branchId], (oldTasks: Task[] = []) =>
        [...oldTasks, newTask]
      );
    };

    const handleTaskDelete = (taskId: string) => {
      queryClient.setQueryData(['tasks', branchId], (oldTasks: Task[] = []) =>
        oldTasks.filter(task => task.id !== taskId)
      );
    };

    // Subscribe to WebSocket events
    webSocketClient.on('task_updated', handleTaskUpdate);
    webSocketClient.on('task_created', handleTaskCreate);
    webSocketClient.on('task_deleted', handleTaskDelete);

    // Cleanup subscriptions
    return () => {
      webSocketClient.off('task_updated', handleTaskUpdate);
      webSocketClient.off('task_created', handleTaskCreate);
      webSocketClient.off('task_deleted', handleTaskDelete);
    };
  }, [branchId, queryClient]);

  return query;
}

// Usage in component:
function TaskList({ branchId }) {
  const { data: tasks, isLoading } = useTasksWithRealtime(branchId);

  // UI automatically updates on WebSocket events!
  return (
    <div>
      {tasks?.map(task => <TaskCard key={task.id} task={task} />)}
    </div>
  );
}
```

**Result**: Can remove cascade Redux slice entirely!

---

## 📦 Pattern 5: Global UI State with Context

### Current Pattern (Likely Context-based)

**File**: `src/hooks/useTheme.ts`

```typescript
/**
 * ✅ CURRENT: Likely using Context (correct pattern!)
 * Keep as-is - Context is perfect for theme
 */

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

---

### Recommended Pattern (Split Context for Performance)

**File**: `src/contexts/ThemeContext.tsx`

```typescript
/**
 * ✅ RECOMMENDED: Split context to optimize re-renders
 * Benefit: Components that only toggle theme won't re-render on theme change
 */

import { createContext, useContext, useState, useCallback } from 'react';

// Split contexts for optimal performance
const ThemeStateContext = createContext<'light' | 'dark' | undefined>(undefined);
const ThemeDispatchContext = createContext<(() => void) | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    // Initialize from localStorage
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'light';
  });

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const newTheme = prev === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', newTheme);
      return newTheme;
    });
  }, []);

  return (
    <ThemeStateContext.Provider value={theme}>
      <ThemeDispatchContext.Provider value={toggleTheme}>
        {children}
      </ThemeDispatchContext.Provider>
    </ThemeStateContext.Provider>
  );
}

// Hook for reading theme (will re-render on theme change)
export function useThemeState() {
  const context = useContext(ThemeStateContext);
  if (context === undefined) {
    throw new Error('useThemeState must be used within ThemeProvider');
  }
  return context;
}

// Hook for toggling theme (will NOT re-render on theme change!)
export function useThemeToggle() {
  const context = useContext(ThemeDispatchContext);
  if (context === undefined) {
    throw new Error('useThemeToggle must be used within ThemeProvider');
  }
  return context;
}

// Combined hook (for components that need both)
export function useTheme() {
  return {
    theme: useThemeState(),
    toggleTheme: useThemeToggle(),
  };
}
```

**Usage**:
```typescript
// Component that only reads theme (re-renders on change)
function ThemedButton() {
  const theme = useThemeState(); // Only subscribes to state
  return <button className={theme}>Click me</button>;
}

// Component that only toggles theme (does NOT re-render!)
function ThemeToggleButton() {
  const toggleTheme = useThemeToggle(); // Only subscribes to dispatch
  return <button onClick={toggleTheme}>Toggle Theme</button>;
}
```

---

## 🧪 Testing Patterns

### Pattern 1: Testing React Query

```typescript
/**
 * ✅ React Query Testing (Simple!)
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { ProjectList } from './ProjectList';

// Helper to create test query client
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false }, // Disable retry in tests
      mutations: { retry: false },
    },
  });
}

test('shows projects from cache', () => {
  const queryClient = createTestQueryClient();

  // Pre-populate cache (instant render!)
  queryClient.setQueryData(['projects'], [
    { id: '1', name: 'Project Alpha' },
    { id: '2', name: 'Project Beta' },
  ]);

  render(
    <QueryClientProvider client={queryClient}>
      <ProjectList />
    </QueryClientProvider>
  );

  // No loading state, instant render from cache
  expect(screen.getByText('Project Alpha')).toBeInTheDocument();
  expect(screen.getByText('Project Beta')).toBeInTheDocument();
});

test('handles loading state', () => {
  const queryClient = createTestQueryClient();

  render(
    <QueryClientProvider client={queryClient}>
      <ProjectList />
    </QueryClientProvider>
  );

  // Shows loading initially
  expect(screen.getByText('Loading...')).toBeInTheDocument();
});

test('handles error state', async () => {
  const queryClient = createTestQueryClient();

  // Mock API to reject
  vi.spyOn(api, 'listProjects').mockRejectedValue(new Error('Network error'));

  render(
    <QueryClientProvider client={queryClient}>
      <ProjectList />
    </QueryClientProvider>
  );

  await waitFor(() => {
    expect(screen.getByText(/Network error/)).toBeInTheDocument();
  });
});
```

---

### Pattern 2: Testing Redux (Current - Complex)

```typescript
/**
 * ⚠️ Redux Testing (Complex, prone to hanging)
 */

import { renderWithProviders } from '../test-utils';

test('shows connection status', () => {
  // Complex setup with Redux store
  const { store } = renderWithProviders(<WebSocketStatus />, {
    preloadedState: {
      websocket: {
        isConnected: true,
        isReconnecting: false,
        error: null,
        // ... many more fields
      },
      cascade: {} // Need to mock even if not used!
    }
  });

  expect(screen.getByText('🟢 Connected')).toBeInTheDocument();
  // Tests can hang here due to Redux Provider side effects
});
```

---

### Pattern 3: Testing Zustand (Simple!)

```typescript
/**
 * ✅ Zustand Testing (Simple, no hanging)
 */

import { useWebSocketStore } from '../store/websocket';

// No Provider needed! Just mock the store
vi.mock('../store/websocket', () => ({
  useWebSocketStore: vi.fn((selector) =>
    selector({ isConnected: true, error: null })
  ),
}));

test('shows connection status', () => {
  render(<WebSocketStatus />);

  expect(screen.getByText('🟢 Connected')).toBeInTheDocument();
  // No hanging, no Provider setup!
});
```

---

### Pattern 4: Testing Context

```typescript
/**
 * ✅ Context Testing (Simple)
 */

import { ThemeProvider } from '../contexts/ThemeContext';

test('renders with dark theme', () => {
  // Mock localStorage
  vi.spyOn(Storage.prototype, 'getItem').mockReturnValue('dark');

  render(
    <ThemeProvider>
      <App />
    </ThemeProvider>
  );

  expect(document.documentElement).toHaveClass('dark');
});

// Or provide mock value directly:
test('toggles theme', () => {
  const mockToggle = vi.fn();

  render(
    <ThemeDispatchContext.Provider value={mockToggle}>
      <ThemeToggleButton />
    </ThemeDispatchContext.Provider>
  );

  fireEvent.click(screen.getByText('Toggle Theme'));
  expect(mockToggle).toHaveBeenCalled();
});
```

---

## 📋 Migration Checklist

### Phase 1: Add React Query (2-3 days)

- [ ] Install dependencies
  ```bash
  npm install @tanstack/react-query
  ```

- [ ] Setup QueryClient in `main.tsx`
  ```typescript
  const queryClient = new QueryClient();
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
  ```

- [ ] Migrate 1-2 hooks as pilot
  - [ ] `useBranchSummaries` → React Query
  - [ ] `useTaskData` → React Query
  - [ ] Test and measure impact

- [ ] Create test utilities
  ```typescript
  // src/tests/query-utils.tsx
  export function createTestQueryClient() { ... }
  export function renderWithQuery(ui, options) { ... }
  ```

- [ ] Update team documentation

### Phase 2: Audit Redux (1 week)

- [ ] Measure cascade slice usage
  ```bash
  grep -r "cascade\." src/components --include="*.tsx"
  ```

- [ ] Decision: Keep Redux minimal OR migrate to Zustand
  - [ ] If keeping: Remove cascade slice if not needed
  - [ ] If migrating: Follow Zustand migration guide

- [ ] Fix test infrastructure issues
  - [ ] Investigate Redux Provider hanging
  - [ ] Update test-utils if keeping Redux
  - [ ] Simplify mocking strategies

### Phase 3: Standardize Patterns (Ongoing)

- [ ] Document team guidelines (✅ This document!)
- [ ] Code review checklist for state management
- [ ] Automated linting rules
- [ ] Onboarding materials
- [ ] Knowledge sharing sessions

---

## 🚨 Common Pitfalls & Solutions

### Pitfall 1: Using Redux for API Calls

❌ **Don't**:
```typescript
// Bad: Redux action for API call
const fetchProjects = createAsyncThunk('projects/fetch', async () => {
  return await listProjects();
});

// Component uses Redux
dispatch(fetchProjects());
const projects = useAppSelector(state => state.projects.data);
```

✅ **Do**:
```typescript
// Good: React Query for API calls
const { data: projects } = useQuery({
  queryKey: ['projects'],
  queryFn: listProjects
});
```

---

### Pitfall 2: Putting Everything in Context

❌ **Don't**:
```typescript
// Bad: Frequent changes in Context (performance issue)
const AppContext = createContext({ theme, user, tasks, projects, selectedItems });
// All consumers re-render on ANY change!
```

✅ **Do**:
```typescript
// Good: Split contexts or use appropriate tool
const ThemeContext = createContext(theme);      // Context ✅
const UserContext = createContext(user);        // Context ✅
const { data: tasks } = useQuery(['tasks']);    // React Query ✅
const [selected] = useState([]);                 // useState ✅
```

---

### Pitfall 3: No Caching Strategy

❌ **Don't**:
```typescript
// Bad: Refetch on every render
useEffect(() => {
  fetchProjects().then(setProjects);
}, []); // Only on mount, but still no cache between mounts
```

✅ **Do**:
```typescript
// Good: React Query caches automatically
const { data: projects } = useQuery({
  queryKey: ['projects'],
  queryFn: fetchProjects,
  staleTime: 5 * 60 * 1000, // 5 minutes
});
```

---

### Pitfall 4: Storing Derived State

❌ **Don't**:
```typescript
// Bad: Storing computed values
const [tasks, setTasks] = useState([]);
const [completedTasks, setCompletedTasks] = useState([]);

useEffect(() => {
  setCompletedTasks(tasks.filter(t => t.status === 'done'));
}, [tasks]);
```

✅ **Do**:
```typescript
// Good: Compute on render (React is fast!)
const { data: tasks } = useQuery(['tasks'], fetchTasks);
const completedTasks = tasks?.filter(t => t.status === 'done');
// Or useMemo if expensive:
const completedTasks = useMemo(
  () => tasks?.filter(t => t.status === 'done'),
  [tasks]
);
```

---

## 🎯 Quick Reference

| Pattern | Use When | Tool |
|---------|----------|------|
| **Fetch data from API** | Always | React Query |
| **Create/Update/Delete** | Always | React Query Mutation |
| **WebSocket connection state** | Multiple components | Redux or Zustand |
| **Real-time data updates** | With API data | React Query + WebSocket |
| **Theme** | App-wide, infrequent | Context |
| **Auth state** | App-wide, infrequent | Context |
| **Modal open/closed** | Single component | useState |
| **Form inputs** | Single component | useState or React Hook Form |
| **Selected items** | Single component | useState |
| **Filters** | Single component | useState or URL params |

---

## 📚 Additional Resources

### Code Examples

- See `src/hooks/useBranchSummaries.ts` - Current pattern (before)
- See this guide - Recommended patterns (after)
- See `src/tests/` - Testing patterns

### Documentation

- `state-management-analysis.md` - Current architecture audit
- `state-management-strategy.md` - Decision framework
- `state-management-comparison.md` - Technology comparison

### External Resources

- [React Query Docs](https://tanstack.com/query/latest/docs/react/overview)
- [Zustand Docs](https://github.com/pmndrs/zustand)
- [React Context Best Practices](https://kentcdodds.com/blog/how-to-use-react-context-effectively)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-05
**Next Review**: After refactoring pilots complete
**Maintained By**: Development Team
