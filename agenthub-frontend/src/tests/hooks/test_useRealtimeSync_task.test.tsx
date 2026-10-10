import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import { animationFactory } from '../../services/AnimationFactory';
import { isTaskDeletePayload, getEntityId, WSMessage } from '../../types/websocket-protocol';
import type { Task } from '../../types/api.types';

// Mock toast hooks
vi.mock('../../components/ui/toast', () => ({
  useSuccessToast: vi.fn(() => vi.fn()),
  useInfoToast: vi.fn(() => vi.fn()),
  useWarningToast: vi.fn(() => vi.fn()),
}));

vi.mock('../../utils/logger', () => ({
  default: {
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

describe('useRealtimeSync - Task Handler with Type Guards', () => {
  let queryClient: QueryClient;

  // Helper to create wrapper with QueryClient
  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    queryClient?.clear();
  });

  describe('Type Guard Validation - isTaskDeletePayload', () => {
    it('should validate correct task delete payload structure', () => {
      const validPayload = {
        id: 'task-123',
        title: 'Test Task',
        git_branch_id: 'branch-456',
      };

      expect(isTaskDeletePayload(validPayload)).toBe(true);
    });

    it('should reject payload missing required id field', () => {
      const invalidPayload = {
        title: 'Test Task',
        git_branch_id: 'branch-456',
      };

      expect(isTaskDeletePayload(invalidPayload)).toBe(false);
    });

    it('should reject payload missing required title field', () => {
      const invalidPayload = {
        id: 'task-123',
        git_branch_id: 'branch-456',
      };

      expect(isTaskDeletePayload(invalidPayload)).toBe(false);
    });

    it('should reject payload with empty id string', () => {
      const invalidPayload = {
        id: '',
        title: 'Test Task',
      };

      expect(isTaskDeletePayload(invalidPayload)).toBe(false);
    });

    it('should reject null or undefined payload', () => {
      expect(isTaskDeletePayload(null)).toBe(false);
      expect(isTaskDeletePayload(undefined)).toBe(false);
    });

    it('should reject payload with non-string id', () => {
      const invalidPayload = {
        id: 123,
        title: 'Test Task',
      };

      expect(isTaskDeletePayload(invalidPayload)).toBe(false);
    });
  });

  describe('Safe ID Extraction - getEntityId', () => {
    it('should extract id from payload.data.primary.id', () => {
      const message: WSMessage = {
        id: 'msg-1',
        version: '2.0',
        type: 'update',
        timestamp: '2025-11-06T19:00:00Z',
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'deleted',
          data: {
            primary: {
              id: 'task-123',
              title: 'Test Task',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      expect(getEntityId(message)).toBe('task-123');
    });

    it('should fallback to metadata.entity_id when primary.id is missing', () => {
      const message: WSMessage = {
        id: 'msg-2',
        version: '2.0',
        type: 'update',
        timestamp: '2025-11-06T19:00:00Z',
        sequence: 2,
        payload: {
          entity: 'task',
          action: 'deleted',
          data: {
            primary: {
              title: 'Test Task',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
          entity_id: 'task-456',
        },
      };

      expect(getEntityId(message)).toBe('task-456');
    });

    it('should return null when both primary.id and metadata.entity_id are missing', () => {
      const message: WSMessage = {
        id: 'msg-3',
        version: '2.0',
        type: 'update',
        timestamp: '2025-11-06T19:00:00Z',
        sequence: 3,
        payload: {
          entity: 'task',
          action: 'deleted',
          data: {
            primary: {
              title: 'Test Task',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      expect(getEntityId(message)).toBe(null);
    });
  });

  describe('Task Create Handler - ONE created event animates ONCE', () => {
    it('does NOT animate a create: WebSocketAnimationService owns that one', async () => {
      // THE OWNER'S REPORT, on the CREATE path: triggers A (this hook's 50ms call plus
      // WebSocketAnimationService's 150ms) and C (the mount effect) made one created
      // event animate more than once. This hook's call is the duplicate on the task
      // path: the service animates the same event and ITS call lands, because by then
      // the row is mounted. FAILED BEFORE THE FIX - this assertion used to see 1 call.
      const createdMessage: WSMessage = {
        id: 'msg-create-1',
        version: '2.0',
        type: 'update',
        timestamp: '2025-11-06T19:00:00Z',
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'created',
          data: {
            primary: {
              id: 'task-created-1',
              title: 'Task to Create',
              git_branch_id: 'branch-created-1',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      const mockWebSocketClient = {
        on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
          if (event === 'update') {
            setTimeout(() => handler(createdMessage), 10);
          }
        }),
        off: vi.fn(),
      };

      const wrapper = createWrapper();
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), { wrapper });

      // The cache update IS still this hook's job, so the row really was added.
      await waitFor(
        () => {
          expect(queryClient.getQueryData(['tasks', 'branch-created-1'])).toBeDefined();
        },
        { timeout: 1000 }
      );

      // Past the 50ms the duplicate used to wait for, so this is not a race.
      await new Promise((resolve) => setTimeout(resolve, 250));

      expect(animationFactory.animate).not.toHaveBeenCalledWith(
        'task-created-1',
        'create',
        expect.anything()
      );
    });
  });

  describe('Task Delete Handler - Integration Tests', () => {
    it('should handle valid task delete message with type guard validation', async () => {
      const validDeleteMessage: WSMessage = {
        id: 'msg-delete-1',
        version: '2.0',
        type: 'update',
        timestamp: '2025-11-06T19:00:00Z',
        sequence: 1,
        payload: {
          entity: 'task',
          action: 'deleted',
          data: {
            primary: {
              id: 'task-delete-123',
              title: 'Task to Delete',
              git_branch_id: 'branch-789',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      // Create mock WebSocket client
      const mockWebSocketClient = {
        on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
          // Immediately call handler to simulate message reception
          if (event === 'update') {
            setTimeout(() => handler(validDeleteMessage), 10);
          }
        }),
        off: vi.fn(),
      };

      // Pre-populate query cache with task
      const wrapper = createWrapper();
      queryClient.setQueryData(['task', 'task-delete-123', false], {
        id: 'task-delete-123',
        title: 'Task to Delete',
      });
      queryClient.setQueryData(['tasks', 'branch-789'], [
        { id: 'task-delete-123', title: 'Task to Delete' },
      ]);

      renderHook(() => useRealtimeSync(mockWebSocketClient, true), { wrapper });

      // Wait for the delete handler to process (600ms delay for animation)
      await waitFor(
        () => {
          const taskCache = queryClient.getQueryData(['task', 'task-delete-123', false]);
          expect(taskCache).toBeUndefined();
        },
        { timeout: 1000 }
      );
    });

    it('should safely handle invalid task delete payload (missing id)', async () => {
      const loggerModule = await import('../../utils/logger');
      const mockLogger = vi.mocked(loggerModule.default);

      const invalidDeleteMessage: WSMessage = {
        id: 'msg-delete-invalid',
        version: '2.0',
        type: 'update',
        timestamp: '2025-11-06T19:00:00Z',
        sequence: 2,
        payload: {
          entity: 'task',
          action: 'deleted',
          data: {
            primary: {
              // Missing id field - should be caught by getEntityId
              title: 'Invalid Task',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      // Create mock WebSocket client
      const mockWebSocketClient = {
        on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
          if (event === 'update') {
            setTimeout(() => handler(invalidDeleteMessage), 10);
          }
        }),
        off: vi.fn(),
      };

      const wrapper = createWrapper();
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), { wrapper });

      // Verify that a warning was logged for missing ID
      await waitFor(() => {
        expect(mockLogger.warn).toHaveBeenCalledWith(
          expect.stringContaining('[useRealtimeSync] Task update missing ID')
        );
      });
    });

    it('should use getEntityId for safe extraction with fallback', async () => {
      // Message with ID in metadata (fallback scenario) - but delete will fail type guard validation
      // because isTaskDeletePayload requires both id and title in data.primary
      const messageWithMetadataId: WSMessage = {
        id: 'msg-delete-fallback',
        version: '2.0',
        type: 'update',
        timestamp: '2025-11-06T19:00:00Z',
        sequence: 3,
        payload: {
          entity: 'task',
          action: 'deleted',
          data: {
            primary: {
              id: 'task-fallback-999',  // Include id in primary for type guard
              title: 'Task with Metadata ID',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
          entity_id: 'task-fallback-999',
        },
      };

      // Create mock WebSocket client
      const mockWebSocketClient = {
        on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
          if (event === 'update') {
            setTimeout(() => handler(messageWithMetadataId), 10);
          }
        }),
        off: vi.fn(),
      };

      const wrapper = createWrapper();
      queryClient.setQueryData(['task', 'task-fallback-999', false], {
        id: 'task-fallback-999',
        title: 'Task with Metadata ID',
      });

      renderHook(() => useRealtimeSync(mockWebSocketClient, true), { wrapper });

      // The implementation should successfully extract ID from metadata and process delete
      await waitFor(
        () => {
          const taskCache = queryClient.getQueryData(['task', 'task-fallback-999', false]);
          expect(taskCache).toBeUndefined();
        },
        { timeout: 1000 }
      );
    });
  });

  describe('Task Delete - Type Safety Enforcement', () => {
    it('should not process delete when type guard validation fails', async () => {
      const malformedMessage: WSMessage = {
        id: 'msg-malformed',
        version: '2.0',
        type: 'update',
        timestamp: '2025-11-06T19:00:00Z',
        sequence: 4,
        payload: {
          entity: 'task',
          action: 'deleted',
          data: {
            primary: {
              // Has id but missing title - should fail type guard
              id: 'task-malformed-456',
              status: 'deleted',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      // Create mock WebSocket client
      const mockWebSocketClient = {
        on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
          if (event === 'update') {
            setTimeout(() => handler(malformedMessage), 10);
          }
        }),
        off: vi.fn(),
      };

      const wrapper = createWrapper();

      // Add a task to cache
      queryClient.setQueryData(['tasks', 'branch-123'], [
        { id: 'task-safe-123', title: 'Safe Task' },
      ]);

      renderHook(() => useRealtimeSync(mockWebSocketClient, true), { wrapper });

      // Wait and verify the task is still in cache (not deleted)
      await waitFor(
        () => {
          const tasks = queryClient.getQueryData(['tasks', 'branch-123']);
          expect(tasks).toEqual([{ id: 'task-safe-123', title: 'Safe Task' }]);
        },
        { timeout: 1000 }
      );
    });
  });

  // THE OWNER'S REPORT, UPDATE PATH: a task status changes and the frontend does not show it.
  // The layer split was GO - the frame is stamped user 'system' and the delivery gate refuses
  // it - so this block pins the CLIENT half of the contract instead: whether the real handler,
  // on the real keys, applies a frame that DOES arrive. Both are the keys production reads:
  //   detail: ['task', taskId, includeContext]  (useTasks.ts:40, both variants are written)
  //   list:   ['tasks', git_branch_id]          (useTasks.ts:14)
  describe('Task Update Handler - an arriving status change must reach the detail and the list', () => {
    const BRANCH_ID = 'branch-status-1';
    const TASK_ID = 'task-status-1';

    const taskAt = (status: string): Task =>
      ({
        id: TASK_ID,
        title: 'Status Task',
        description: '',
        status,
        priority: 'high',
        git_branch_id: BRANCH_ID,
        progress_percentage: 0,
        assignees: ['fe-dev-agent'],
        labels: [],
        created_at: '2026-10-09T18:00:00Z',
        updated_at: '2026-10-09T18:00:00Z',
      }) as unknown as Task;

    // FIELD FOR FIELD the frame agenthub_go's BroadcastDataChange builds for a task update
    // (fastmcp/server/routes/websocket_routes.go): version 2.0, type 'update', payload.entity
    // 'task', payload.data.primary = the task dict, metadata.source 'user' (because 'updated'
    // is in that function's userTriggered set). metadata.userId is the ACTING USER - it used to
    // be the literal 'system', which is what the delivery gate refused for every connection
    // before 62e76c3e. The client never reads this value, and the case below pins that.
    const updateFrame = (status: string, userId = 'u-actor'): WSMessage =>
      ({
        id: 'broadcast-task-424242',
        version: '2.0',
        type: 'update',
        timestamp: '2026-10-09T20:00:00.000000+00:00',
        sequence: 4242,
        payload: {
          entity: 'task',
          action: 'updated',
          data: { primary: taskAt(status) },
        },
        metadata: {
          source: 'user',
          userId,
          entity_type: 'task',
          entity_id: TASK_ID,
          event_type: 'updated',
        },
      }) as unknown as WSMessage;

    it('writes the frame values into both detail variants, and invalidates the list so a live list refetches', async () => {
      const wrapper = createWrapper();

      // What the operator is looking at before the change.
      queryClient.setQueryData(['task', TASK_ID, false], taskAt('todo'));
      queryClient.setQueryData(['task', TASK_ID, true], taskAt('todo'));
      queryClient.setQueryData(['tasks', BRANCH_ID], [taskAt('todo')]);

      // A REAL subscriber on the REAL list key. It answers with whatever status the server holds
      // at fetch time, so a cache merely left alone stays distinguishable from one that was
      // invalidated and refetched.
      let servedStatus = 'todo';
      const fetches: string[] = [];
      const listObserver = renderHook(
        () =>
          useQuery({
            queryKey: ['tasks', BRANCH_ID],
            queryFn: async () => {
              fetches.push(servedStatus);
              return [taskAt(servedStatus)];
            },
            staleTime: 0,
          }),
        { wrapper }
      );

      await waitFor(() => expect(listObserver.result.current.data?.[0].status).toBe('todo'));
      expect(fetches).toEqual(['todo']);

      servedStatus = 'in_progress';
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
      const mockWebSocketClient = {
        on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
          if (event === 'update') {
            setTimeout(() => handler(updateFrame('in_progress')), 10);
          }
        }),
        off: vi.fn(),
      };
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), { wrapper });

      // The handler holds its cache write for 150ms to let the update animation play.
      await waitFor(
        () => {
          expect(queryClient.getQueryData<Task>(['task', TASK_ID, false])?.status).toBe('in_progress');
          expect(queryClient.getQueryData<Task>(['task', TASK_ID, true])?.status).toBe('in_progress');
        },
        { timeout: 2000 }
      );

      // The list is not written directly - it is invalidated, on the real key, and a live
      // subscriber re-reads it.
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['tasks', BRANCH_ID] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['tasks'] });
      await waitFor(
        () => expect(listObserver.result.current.data?.[0].status).toBe('in_progress'),
        { timeout: 2000 }
      );
      expect(fetches[fetches.length - 1]).toBe('in_progress');

      invalidateSpy.mockRestore();
    });

    it('re-reads the EXECUTION LEDGER, so an open timeline follows the same status change', async () => {
      const wrapper = createWrapper();

      // The ledger the open task details view is showing, and the server's copy of it. The
      // subscriber carries the hook's OWN staleTime (30s), so a refetch inside this case cannot be
      // ordinary staleness - it has to be the frame's invalidation.
      const ledgerAt = (status: string) => ({
        success: true,
        events: [
          {
            id: `ev-${status}`,
            task_id: TASK_ID,
            seq: 4,
            kind: 'status_changed',
            actor_kind: 'agent',
            actor_id: 'fe-dev',
            payload: { old: 'review', new: status },
            created_at: '2026-10-09T20:00:00Z',
          },
        ],
        count: 1,
        after_seq: 0,
      });

      let servedLatest = 'review';
      const fetches: string[] = [];
      const ledgerObserver = renderHook(
        () =>
          useQuery({
            queryKey: ['task-events', TASK_ID],
            queryFn: async () => {
              fetches.push(servedLatest);
              return ledgerAt(servedLatest);
            },
            staleTime: 30 * 1000,
          }),
        { wrapper }
      );

      await waitFor(() =>
        expect(ledgerObserver.result.current.data?.events[0].payload?.['new']).toBe('review'),
      );
      expect(fetches).toEqual(['review']);

      servedLatest = 'done';
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
      const mockWebSocketClient = {
        on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
          if (event === 'update') {
            setTimeout(() => handler(updateFrame('done')), 10);
          }
        }),
        off: vi.fn(),
      };
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), { wrapper });

      // The ledger is not patched out of the payload - the frame carries the task, not the row the
      // write produced - so the query is invalidated on its own key and the timeline re-reads it.
      await waitFor(() =>
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['task-events', TASK_ID] }),
      );
      await waitFor(() => expect(fetches).toEqual(['review', 'done']), { timeout: 2000 });
      await waitFor(() =>
        expect(ledgerObserver.result.current.data?.events[0].payload?.['new']).toBe('done'),
      );

      invalidateSpy.mockRestore();
    });

    it('caches the frame whatever the userId stamp is, so the client is not a second gate', async () => {
      // Delivery is the only place allowed to refuse a frame by its userId stamp (the Go gate
      // does, deliberately, for 'system'). If the client also keyed on it, go-dev's choice of
      // stamp would silently change client behavior, and the stale-'system' shape below would
      // be dropped here as well as there.
      const wrapper = createWrapper();
      queryClient.setQueryData(['task', TASK_ID, false], taskAt('todo'));

      const mockWebSocketClient = {
        on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
          if (event === 'update') {
            setTimeout(() => handler(updateFrame('in_progress', 'system')), 10);
          }
        }),
        off: vi.fn(),
      };
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), { wrapper });

      await waitFor(
        () =>
          expect(queryClient.getQueryData<Task>(['task', TASK_ID, false])?.status).toBe('in_progress'),
        { timeout: 2000 }
      );
    });
  });
});
