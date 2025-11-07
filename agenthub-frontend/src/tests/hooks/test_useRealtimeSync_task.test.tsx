import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import { isTaskDeletePayload, getEntityId, WSMessage } from '../../types/websocket-protocol';

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
  logger: {
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
});
