# State Management Strategy Guide
## agenthub Frontend Decision Framework

**Date**: 2025-11-05
**Audience**: Development Team
**Purpose**: Clear guidelines for choosing the right state management tool

---

## 🎯 TL;DR - Quick Decision Tree

```
📊 What type of state?
│
├─ 🌐 Server data (API-fetched)?
│   └─ Use: React Query
│
├─ ⚡ Real-time (WebSocket)?
│   └─ Use: Redux (webSocket slice) OR React Query + WebSocket
│
├─ 🎨 UI component-local?
│   └─ Use: useState / useReducer
│
├─ 🌍 Global UI state (theme, auth)?
│   └─ Use: Context API
│
└─ 📝 Form state?
    └─ Use: useState OR React Hook Form
```

---

## 📖 The 2025 State Management Philosophy

### Core Principle

> **"Use the simplest tool that solves the problem. Complexity should match the problem's complexity, not exceed it."**

### The Modern Stack (What We're Moving Toward)

| State Type | Tool | Why |
|------------|------|-----|
| **Server State** | React Query | Caching, revalidation, prefetching built-in |
| **Real-time State** | Redux (minimal) | WebSocket coordination across components |
| **Global UI** | Context API | Theme, auth - stable, infrequent changes |
| **Local UI** | useState | Modals, forms, toggles - component-scoped |

---

## 🔍 Detailed Decision Framework

### 1. Server State (API-Fetched Data)

**Examples**: Projects list, task data, branch summaries, agent info

#### ✅ Use: React Query

**Why**:
- Automatic caching (no manual cache management)
- Background revalidation (stale-while-revalidate)
- Request deduplication (multiple components requesting same data)
- Automatic retries with exponential backoff
- Optimistic updates
- Pagination & infinite scroll support
- DevTools for debugging

**Code Example**:
```typescript
// ✅ RECOMMENDED: React Query
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

function ProjectList() {
  const { data: projects, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const queryClient = useQueryClient();
  const createMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      // Auto-refetch projects list
      queryClient.invalidateQueries(['projects']);
    },
  });

  return <div>...</div>;
}
```

**vs. Current Approach**:
```typescript
// ❌ CURRENT: Manual fetching, no cache
function ProjectList() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoading(true);
        const data = await listProjects();
        setProjects(data);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };
    fetchProjects();
  }, []);

  return <div>...</div>;
}
// Problem: Every mount = new fetch, no caching!
```

#### ❌ Don't Use: Redux Actions

**Why Not**:
- Redux actions are boilerplate-heavy
- Manual cache invalidation
- Complex async action handling (thunks)
- Difficult testing
- Server state changes frequently (Redux is better for UI state)

---

### 2. Real-time State (WebSocket-Driven)

**Examples**: Connection status, live task updates, real-time notifications

#### Current Approach: Redux

**Location**: `src/store/slices/webSocketSlice.ts`

**Justification**:
- ✅ Multiple components need connection status
- ✅ Connection state changes frequently
- ✅ Need to coordinate reconnection logic

**Code Example**:
```typescript
// ✅ KEEP: Redux for WebSocket coordination
import { useAppSelector } from '../store/hooks';

function WebSocketStatus() {
  const isConnected = useAppSelector(state => state.websocket.isConnected);
  const error = useAppSelector(state => state.websocket.error);

  return <div>{isConnected ? 'Connected' : 'Disconnected'}</div>;
}
```

#### Alternative Approach: React Query + WebSocket

**For Real-time Data Updates** (not connection state):

```typescript
// 🆕 CONSIDER: React Query with WebSocket updates
import { useQuery, useQueryClient } from '@tanstack/react-query';

function useTasksWithRealtime(branchId: string) {
  const queryClient = useQueryClient();

  // Fetch tasks via React Query
  const query = useQuery({
    queryKey: ['tasks', branchId],
    queryFn: () => listTasks({ git_branch_id: branchId }),
  });

  // Subscribe to WebSocket updates
  useEffect(() => {
    const unsubscribe = webSocketClient.on('task_updated', (task) => {
      // Update React Query cache directly
      queryClient.setQueryData(['tasks', branchId], (oldTasks) =>
        oldTasks.map(t => t.id === task.id ? task : t)
      );
    });

    return unsubscribe;
  }, [branchId, queryClient]);

  return query;
}
```

**Benefits**:
- Single source of truth (React Query cache)
- No need for cascade slice
- Automatic UI updates
- Works with React Query DevTools

#### Decision Matrix

| Use Case | Redux | React Query + WS |
|----------|-------|------------------|
| **WebSocket connection status** | ✅ Keep | ❌ Overkill |
| **Real-time data updates** | ⚠️ Current (cascade slice) | ✅ Better pattern |
| **Live notifications** | ⚠️ Could work | ✅ Cleaner |

---

### 3. Global UI State

**Examples**: Theme, authentication, user preferences, language

#### ✅ Use: Context API

**Why**:
- Built into React (no extra bundle size)
- Perfect for infrequent changes
- Simple to understand and test
- Type-safe with TypeScript

**Code Example**:
```typescript
// ✅ RECOMMENDED: Context for global UI state
import { createContext, useContext, useState } from 'react';

interface ThemeContext {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContext | null>(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};
```

**Performance Optimization**:
```typescript
// Split contexts to avoid unnecessary re-renders
const ThemeStateContext = createContext<'light' | 'dark'>('light');
const ThemeDispatchContext = createContext<() => void>(() => {});

// Components that only read theme
const theme = useContext(ThemeStateContext);

// Components that only toggle theme (won't re-render on theme change!)
const toggleTheme = useContext(ThemeDispatchContext);
```

#### ❌ Don't Use: Redux

**Why Not**:
- Overkill for infrequent changes
- More boilerplate
- Context is simpler and works fine

---

### 4. Component-Local UI State

**Examples**: Modal open/closed, form inputs, expandable sections, selected items

#### ✅ Use: useState / useReducer

**Why**:
- Simplest solution
- Co-located with component
- Easy to test
- No prop drilling if state is truly local

**Code Example**:
```typescript
// ✅ RECOMMENDED: useState for simple local state
function TaskDialog({ task }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button onClick={() => setIsOpen(true)}>View Details</button>
      <Dialog open={isOpen} onClose={() => setIsOpen(false)}>
        <TaskDetails task={task} />
      </Dialog>
    </>
  );
}

// ✅ RECOMMENDED: useReducer for complex local state
type State = { selected: string[]; filter: string; sort: 'asc' | 'desc' };
type Action =
  | { type: 'SELECT'; id: string }
  | { type: 'FILTER'; value: string }
  | { type: 'SORT'; direction: 'asc' | 'desc' };

function TaskList() {
  const [state, dispatch] = useReducer(reducer, initialState);

  return <div>...</div>;
}
```

#### ❌ Don't Use: Redux

**Why Not**:
- Massive overkill
- Unnecessary prop drilling from Redux store
- Makes component less reusable
- Harder to test

---

### 5. Form State

**Examples**: Create project form, edit task form, filters

#### ✅ Use: useState for Simple Forms

```typescript
// ✅ RECOMMENDED: useState for simple forms
function CreateProjectForm() {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    await createProject({ name, description });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={name} onChange={(e) => setName(e.target.value)} />
      <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
      <button type="submit">Create</button>
    </form>
  );
}
```

#### ✅ Use: React Hook Form for Complex Forms

```typescript
// ✅ RECOMMENDED: React Hook Form for complex forms
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high']),
});

function CreateTaskForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data) => {
    await createTask(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name')} />
      {errors.name && <span>{errors.name.message}</span>}

      <textarea {...register('description')} />

      <select {...register('priority')}>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </select>

      <button type="submit">Create</button>
    </form>
  );
}
```

#### ❌ Don't Use: Redux

**Why Not**:
- Form state is ephemeral (destroyed on unmount)
- No need to share across components
- Complex Redux setup for simple forms

---

## 🚦 Migration Strategy

### Phase 1: Add React Query (Low Risk)

**Timeline**: 2-3 days
**Impact**: High value, low risk

**Steps**:
1. Install React Query:
   ```bash
   npm install @tanstack/react-query
   ```

2. Setup QueryClient:
   ```typescript
   // src/main.tsx
   import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

   const queryClient = new QueryClient({
     defaultOptions: {
       queries: {
         staleTime: 5 * 60 * 1000, // 5 minutes
         retry: 1,
       },
     },
   });

   root.render(
     <QueryClientProvider client={queryClient}>
       <App />
     </QueryClientProvider>
   );
   ```

3. Migrate 1-2 hooks as proof of concept:
   - Start with `useBranchSummaries` (frequently used, clear caching benefit)
   - Measure impact on performance and test complexity

4. Team review and decide on full migration

---

### Phase 2: Simplify Redux (Medium Risk)

**Timeline**: 1 week
**Impact**: Reduced complexity, easier testing

**Options**:

**Option A: Keep Redux Minimal**
- ✅ Keep webSocketSlice (justified)
- ⚠️ Audit cascadeSlice usage
- Remove cascade if React Query handles real-time updates

**Option B: Replace with Zustand**
- Lighter alternative (3KB vs 52KB)
- Simpler API
- No Provider needed
- Better for our minimal Redux usage

**Zustand Example**:
```typescript
// src/store/websocket.ts
import create from 'zustand';

interface WebSocketStore {
  isConnected: boolean;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
}

export const useWebSocketStore = create<WebSocketStore>((set) => ({
  isConnected: false,
  error: null,
  connect: () => set({ isConnected: true }),
  disconnect: () => set({ isConnected: false }),
}));

// Usage in component:
const isConnected = useWebSocketStore(state => state.isConnected);
```

---

### Phase 3: Standardize Patterns (Long-term)

**Timeline**: Ongoing
**Impact**: Consistency, easier onboarding

**Goals**:
1. Document patterns for team
2. Update all custom hooks to follow standards
3. Create reusable hook factories
4. Automated linting/enforcement

---

## 📊 Technology Comparison at a Glance

| Feature | Redux | React Query | Context | useState |
|---------|-------|-------------|---------|----------|
| **Bundle Size** | 52 KB | 38 KB | 0 KB (built-in) | 0 KB (built-in) |
| **Learning Curve** | Steep | Moderate | Easy | Easy |
| **Boilerplate** | High | Low | Medium | None |
| **Use Case** | Global state | Server state | Global UI | Local UI |
| **Caching** | Manual | Automatic | N/A | N/A |
| **Testing** | Complex | Simple | Simple | Simple |
| **DevTools** | ✅ Excellent | ✅ Excellent | ❌ None | ❌ None |
| **TypeScript** | ✅ Good | ✅ Excellent | ✅ Good | ✅ Excellent |

---

## 🧪 Testing Implications

### Redux Testing (Current)

```typescript
// ❌ COMPLEX: Mock Redux store + Provider
import { renderWithProviders } from './test-utils';

test('shows connection status', () => {
  const { store } = renderWithProviders(<WebSocketStatus />, {
    preloadedState: {
      websocket: { isConnected: true },
      cascade: {}
    }
  });
  // Test hangs with real Redux Provider...
});
```

### React Query Testing (Proposed)

```typescript
// ✅ SIMPLE: Mock data directly
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

test('shows projects', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  // Pre-populate cache
  queryClient.setQueryData(['projects'], mockProjects);

  render(
    <QueryClientProvider client={queryClient}>
      <ProjectList />
    </QueryClientProvider>
  );

  expect(screen.getByText('Project Alpha')).toBeInTheDocument();
});
```

---

## 🎯 Team Guidelines

### When in Doubt, Use This Checklist:

1. **Is it server data?** → React Query
2. **Is it WebSocket connection status?** → Redux (or Context)
3. **Is it real-time data updates?** → React Query + WebSocket
4. **Is it global UI (theme/auth)?** → Context
5. **Is it component-local?** → useState
6. **Is it a form?** → useState or React Hook Form

### Red Flags (Don't Do This)

❌ Storing API response in Redux just to cache it
❌ Using Redux for modal open/closed state
❌ Creating Redux actions for every API call
❌ Putting form state in Redux
❌ Using Context for frequently changing data

---

## 📚 Further Reading

### Official Documentation
- [React Query Docs](https://tanstack.com/query/latest)
- [Redux Toolkit Docs](https://redux-toolkit.js.org/)
- [React Context API](https://react.dev/learn/passing-data-deeply-with-context)
- [Zustand Docs](https://github.com/pmndrs/zustand)

### Articles
- "You Might Not Need Redux" - Dan Abramov
- "Why We Don't Always Need Redux Anymore (2025)" - Referenced by user

### Internal Docs
- `state-management-analysis.md` - Current architecture analysis
- `state-management-comparison.md` - Detailed technology comparison
- `state-management-patterns.md` - Code examples and refactoring guides

---

## ✅ Action Items

**For Developers**:
1. Read this guide
2. Follow decision tree for new features
3. Ask in team chat if unsure
4. Update this guide if you find gaps

**For Team Lead**:
1. Review React Query pilot results
2. Decide on Redux future (keep minimal or migrate to Zustand)
3. Schedule knowledge sharing session
4. Update onboarding materials

**For Architects**:
1. Monitor bundle size impact
2. Track test complexity metrics
3. Measure render performance
4. Plan Phase 2 migration if approved

---

**Document Version**: 1.0
**Last Updated**: 2025-11-05
**Next Review**: After React Query pilot (Phase 1)
**Maintained By**: Development Team
