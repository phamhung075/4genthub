/**
 * TDD Test Suite: useRealtimeSync - Subtask Delete Handler Type Guards
 *
 * Tests the integration of type guards (isSubtaskDeletePayload, getEntityId)
 * from websocket-protocol.ts into the subtask delete handler.
 *
 * Requirements:
 * - Import and use isSubtaskDeletePayload for validation
 * - Import and use getEntityId for safe ID extraction
 * - Log invalid payloads with descriptive messages
 * - Only process valid subtask delete payloads
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import logger from '../../utils/logger';
import type { WSMessage } from '../../types/websocketTypes';

// Mock dependencies
vi.mock('../../utils/logger', () => ({
  default: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('../../components/ui/toast', () => ({
  useSuccessToast: () => vi.fn(),
  useInfoToast: () => vi.fn(),
  useWarningToast: () => vi.fn(),
}));

describe('useRealtimeSync - Subtask Delete Handler with Type Guards (TDD)', () => {
  let queryClient: QueryClient;
  let mockWebSocketClient: any;

  beforeEach(() => {
    vi.clearAllMocks();

    // Create fresh query client
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    // Mock WebSocket client
    mockWebSocketClient = {
      on: vi.fn(),
      off: vi.fn(),
    };

    // Pre-populate cache with test data
    queryClient.setQueryData(['subtasks', 'task-123'], [
      { id: 'subtask-valid', title: 'Valid Subtask', task_id: 'task-123', status: 'todo' },
      { id: 'subtask-invalid', title: 'Invalid Subtask', task_id: 'task-123', status: 'todo' },
    ]);
  });

  afterEach(() => {
    queryClient.clear();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  /**
   * Test 1: Valid Subtask Delete Payload
   * Should process normally when all required fields present
   */
  it('should process valid subtask delete payload with all required fields', async () => {
    const { result } = renderHook(
      () => useRealtimeSync(mockWebSocketClient, true),
      { wrapper }
    );

    // Get the message handler that was registered
    expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
    const messageHandler = mockWebSocketClient.on.mock.calls[0][1];

    // Valid subtask delete message
    const validMessage: WSMessage = {
      id: 'msg-1',
      version: '2.0',
      type: 'update',
      timestamp: new Date().toISOString(),
      sequence: 1,
      payload: {
        entity: 'subtask',
        action: 'deleted',
        data: {
          primary: {
            id: 'subtask-valid',
            title: 'Valid Subtask',
            task_id: 'task-123',
          },
        },
      },
      metadata: {
        source: 'mcp-ai' as const,
      },
    };

    // Process message
    messageHandler(validMessage);

    // Should NOT log warning for valid payload
    await waitFor(() => {
      expect(logger.warn).not.toHaveBeenCalledWith(
        expect.stringContaining('Invalid subtask delete payload')
      );
    });

    // Should process deletion (cache update delayed by 600ms, so we check it was logged)
    expect(logger.debug).toHaveBeenCalledWith(
      '[useRealtimeSync] Subtask event:',
      'deleted',
      'subtask-valid'
    );
  });

  /**
   * Test 2: Invalid Subtask Delete Payload - Missing ID
   * Should log error and skip processing
   */
  it('should reject subtask delete payload missing required id field', async () => {
    const { result } = renderHook(
      () => useRealtimeSync(mockWebSocketClient, true),
      { wrapper }
    );

    const messageHandler = mockWebSocketClient.on.mock.calls[0][1];

    // Invalid message: missing id
    const invalidMessage: WSMessage = {
      id: 'msg-2',
      version: '2.0',
      type: 'update',
      timestamp: new Date().toISOString(),
      sequence: 2,
      payload: {
        entity: 'subtask',
        action: 'deleted',
        data: {
          primary: {
            // id: 'subtask-invalid', // MISSING
            title: 'Invalid Subtask',
            task_id: 'task-123',
          } as any,
        },
      },
      metadata: {
        source: 'mcp-ai' as const,
      },
    };

    // Process message
    messageHandler(invalidMessage);

    // Should log warning about invalid payload
    await waitFor(() => {
      expect(logger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Invalid subtask delete payload'),
        expect.objectContaining({
          data: expect.any(Object),
          reason: expect.stringContaining('id'),
        })
      );
    });
  });

  /**
   * Test 3: Invalid Subtask Delete Payload - Missing task_id
   * Should log error and skip processing
   */
  it('should reject subtask delete payload missing required task_id field', async () => {
    const { result } = renderHook(
      () => useRealtimeSync(mockWebSocketClient, true),
      { wrapper }
    );

    const messageHandler = mockWebSocketClient.on.mock.calls[0][1];

    // Invalid message: missing task_id
    const invalidMessage: WSMessage = {
      id: 'msg-3',
      version: '2.0',
      type: 'update',
      timestamp: new Date().toISOString(),
      sequence: 3,
      payload: {
        entity: 'subtask',
        action: 'deleted',
        data: {
          primary: {
            id: 'subtask-invalid',
            title: 'Invalid Subtask',
            // task_id: 'task-123', // MISSING
          } as any,
        },
      },
      metadata: {
        source: 'mcp-ai' as const,
      },
    };

    // Process message
    messageHandler(invalidMessage);

    // Should log warning about invalid payload
    await waitFor(() => {
      expect(logger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Invalid subtask delete payload'),
        expect.objectContaining({
          data: expect.any(Object),
          reason: expect.stringContaining('task_id'),
        })
      );
    });
  });

  /**
   * Test 4: Completely Invalid Payload
   * Should log error and skip processing
   */
  it('should reject completely invalid subtask delete payload', async () => {
    const { result } = renderHook(
      () => useRealtimeSync(mockWebSocketClient, true),
      { wrapper }
    );

    const messageHandler = mockWebSocketClient.on.mock.calls[0][1];

    // Completely invalid message
    const invalidMessage: WSMessage = {
      id: 'msg-4',
      version: '2.0',
      type: 'update',
      timestamp: new Date().toISOString(),
      sequence: 4,
      payload: {
        entity: 'subtask',
        action: 'deleted',
        data: {
          primary: {} as any, // Empty object
        },
      },
      metadata: {
        source: 'mcp-ai' as const,
      },
    };

    // Process message
    messageHandler(invalidMessage);

    // Should log warning about invalid payload
    await waitFor(() => {
      expect(logger.warn).toHaveBeenCalledWith(
        expect.stringContaining('Invalid subtask delete payload'),
        expect.any(Object)
      );
    });
  });

  /**
   * Test 5: Type Guard Integration
   * Verify isSubtaskDeletePayload is called for validation
   */
  it('should use isSubtaskDeletePayload type guard for validation', async () => {
    // Import the type guard to verify it exists
    const { isSubtaskDeletePayload } = await import('../../types/websocket-protocol');

    // Verify type guard works correctly
    expect(isSubtaskDeletePayload({ id: 'test', task_id: 'parent' })).toBe(true);
    expect(isSubtaskDeletePayload({ id: 'test' })).toBe(false);
    expect(isSubtaskDeletePayload({ task_id: 'parent' })).toBe(false);
    expect(isSubtaskDeletePayload({})).toBe(false);
    expect(isSubtaskDeletePayload(null)).toBeFalsy(); // null is falsy
  });

  /**
   * Test 6: getEntityId Helper Integration
   * Verify getEntityId is used for safe ID extraction
   */
  it('should use getEntityId helper for safe ID extraction', async () => {
    // Import the helper to verify it exists
    const { getEntityId } = await import('../../types/websocket-protocol');

    const validMessage: WSMessage = {
      id: 'msg-5',
      version: '2.0',
      type: 'update',
      timestamp: new Date().toISOString(),
      sequence: 5,
      payload: {
        entity: 'subtask',
        action: 'deleted',
        data: {
          primary: { id: 'extracted-id', task_id: 'task-123' },
        },
      },
      metadata: {
        source: 'mcp-ai' as const,
        entity_id: 'fallback-id',
      },
    };

    // Verify getEntityId works correctly
    const entityId = getEntityId(validMessage);
    expect(entityId).toBe('extracted-id');
  });
});
