/**
 * TDD Tests for useRealtimeSync Project Handler Type Guards
 *
 * Purpose: Verify that handleProjectUpdate uses type guards from websocket-protocol.ts
 * - isProjectDeletePayload for validation
 * - getDisplayName for toast messages
 *
 * These tests are written FIRST (TDD), then implementation follows.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import * as websocketProtocol from '../../types/websocket-protocol';
import type { WSMessage } from '../../types/websocketTypes';
import type { Project } from '../../types/api.types';

// Mock dependencies
vi.mock('../../components/ui/toast', () => ({
  useSuccessToast: () => vi.fn(),
  useInfoToast: () => vi.fn(),
  useWarningToast: () => vi.fn(),
}));

vi.mock('../../utils/logger', () => ({
  default: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Spy on websocket-protocol functions
const isProjectDeletePayloadSpy = vi.spyOn(websocketProtocol, 'isProjectDeletePayload');
const getDisplayNameSpy = vi.spyOn(websocketProtocol, 'getDisplayName');

describe('useRealtimeSync - Project Handler Type Guards (TDD)', () => {
  let queryClient: QueryClient;
  let mockWebSocketClient: any;
  let messageHandler: ((msg: WSMessage) => void) | null;

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();
    messageHandler = null;

    // Create fresh query client
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    // Mock WebSocket client
    mockWebSocketClient = {
      on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
        if (event === 'update') {
          messageHandler = handler;
        }
      }),
      off: vi.fn(),
      isConnected: true,
    };

    // Pre-populate query cache with test projects
    queryClient.setQueryData<Project[]>(['projects'], [
      { id: 'project-1', name: 'Test Project 1', description: 'Test 1' },
      { id: 'project-2', name: 'Test Project 2', description: 'Test 2' },
    ]);
  });

  afterEach(() => {
    queryClient.clear();
  });

  const createWrapper = () => {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };

  describe('Type Guard Validation - isProjectDeletePayload', () => {
    it('should call isProjectDeletePayload to validate delete payload', async () => {
      const { result } = renderHook(
        () => useRealtimeSync(mockWebSocketClient, true),
        { wrapper: createWrapper() }
      );

      // Wait for hook to initialize
      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      });

      // Create valid delete message
      const validDeleteMessage: WSMessage = {
        id: 'msg-1',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'project',
          action: 'deleted',
          data: {
            primary: {
              id: 'project-1',
              name: 'Test Project 1',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      // Trigger message handler
      if (messageHandler) {
        messageHandler(validDeleteMessage);
      }

      // Verify type guard was called
      await waitFor(() => {
        expect(isProjectDeletePayloadSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            id: 'project-1',
            name: 'Test Project 1',
          })
        );
      });
    });

    it('should reject payload missing required id field', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const { result } = renderHook(
        () => useRealtimeSync(mockWebSocketClient, true),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      });

      // Create invalid message (missing id)
      const invalidMessage: WSMessage = {
        id: 'msg-2',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 2,
        payload: {
          entity: 'project',
          action: 'deleted',
          data: {
            primary: {
              // Missing 'id' field
              name: 'Test Project',
            } as any,
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      // Get initial projects count
      const initialProjects = queryClient.getQueryData<Project[]>(['projects']);
      const initialCount = initialProjects?.length || 0;

      // Trigger message handler
      if (messageHandler) {
        messageHandler(invalidMessage);
      }

      // Wait a bit for any potential processing
      await new Promise(resolve => setTimeout(resolve, 100));

      // Verify cache was NOT modified (invalid payload rejected)
      const finalProjects = queryClient.getQueryData<Project[]>(['projects']);
      expect(finalProjects?.length).toBe(initialCount);

      // Verify error was logged
      expect(consoleErrorSpy).toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });

    it('should reject payload missing required name field', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const { result } = renderHook(
        () => useRealtimeSync(mockWebSocketClient, true),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      });

      // Create invalid message (missing name)
      const invalidMessage: WSMessage = {
        id: 'msg-3',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 3,
        payload: {
          entity: 'project',
          action: 'deleted',
          data: {
            primary: {
              id: 'project-1',
              // Missing 'name' field
            } as any,
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      // Get initial projects
      const initialProjects = queryClient.getQueryData<Project[]>(['projects']);
      const initialCount = initialProjects?.length || 0;

      // Trigger message handler
      if (messageHandler) {
        messageHandler(invalidMessage);
      }

      // Wait for processing
      await new Promise(resolve => setTimeout(resolve, 100));

      // Verify cache was NOT modified
      const finalProjects = queryClient.getQueryData<Project[]>(['projects']);
      expect(finalProjects?.length).toBe(initialCount);

      // Verify error was logged
      expect(consoleErrorSpy).toHaveBeenCalled();

      consoleErrorSpy.mockRestore();
    });
  });

  describe('getDisplayName Helper Usage', () => {
    it('should use getDisplayName for toast messages instead of direct property access', async () => {
      const { result } = renderHook(
        () => useRealtimeSync(mockWebSocketClient, true),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      });

      // Create valid delete message
      const deleteMessage: WSMessage = {
        id: 'msg-4',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 4,
        payload: {
          entity: 'project',
          action: 'deleted',
          data: {
            primary: {
              id: 'project-1',
              name: 'Test Project 1',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      // Trigger message handler
      if (messageHandler) {
        messageHandler(deleteMessage);
      }

      // Verify getDisplayName was called with the message
      await waitFor(() => {
        expect(getDisplayNameSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            payload: expect.objectContaining({
              entity: 'project',
              action: 'deleted',
            }),
          })
        );
      });
    });

    it('should handle projects with different name structures using getDisplayName', async () => {
      const { result } = renderHook(
        () => useRealtimeSync(mockWebSocketClient, true),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      });

      // Create message with name in metadata (fallback scenario)
      const messageWithMetadata: WSMessage = {
        id: 'msg-5',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 5,
        payload: {
          entity: 'project',
          action: 'deleted',
          data: {
            primary: {
              id: 'project-2',
              name: 'Fallback Project Name',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
          project_name: 'Metadata Project Name',
        },
      };

      // Trigger handler
      if (messageHandler) {
        messageHandler(messageWithMetadata);
      }

      // Verify getDisplayName handles different name sources
      await waitFor(() => {
        expect(getDisplayNameSpy).toHaveBeenCalled();
        const result = websocketProtocol.getDisplayName(messageWithMetadata);
        expect(typeof result).toBe('string');
        expect(result.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Integration - Full Delete Flow with Type Guards', () => {
    it('should complete full delete flow when payload passes validation', async () => {
      const { result } = renderHook(
        () => useRealtimeSync(mockWebSocketClient, true),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      });

      // Verify initial state
      const initialProjects = queryClient.getQueryData<Project[]>(['projects']);
      expect(initialProjects).toHaveLength(2);
      expect(initialProjects?.find(p => p.id === 'project-1')).toBeDefined();

      // Create valid delete message
      const validDeleteMessage: WSMessage = {
        id: 'msg-6',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 6,
        payload: {
          entity: 'project',
          action: 'deleted',
          data: {
            primary: {
              id: 'project-1',
              name: 'Test Project 1',
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      // Trigger delete
      if (messageHandler) {
        messageHandler(validDeleteMessage);
      }

      // Verify type guard was called
      expect(isProjectDeletePayloadSpy).toHaveBeenCalled();

      // Verify getDisplayName was called
      expect(getDisplayNameSpy).toHaveBeenCalled();

      // Wait for animation delay (600ms) + buffer
      await waitFor(
        () => {
          const finalProjects = queryClient.getQueryData<Project[]>(['projects']);
          expect(finalProjects).toHaveLength(1);
          expect(finalProjects?.find(p => p.id === 'project-1')).toBeUndefined();
        },
        { timeout: 1500 }
      );
    });

    it('should not delete when type guard validation fails', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const { result } = renderHook(
        () => useRealtimeSync(mockWebSocketClient, true),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      });

      // Create multiple invalid messages
      const invalidMessages = [
        // Missing id
        {
          id: 'msg-7',
          version: '2.0' as const,
          type: 'update' as const,
          timestamp: new Date().toISOString(),
          sequence: 7,
          payload: {
            entity: 'project' as const,
            action: 'deleted' as const,
            data: { primary: { name: 'No ID Project' } as any },
          },
          metadata: { source: 'mcp-ai' as const },
        },
        // Missing name
        {
          id: 'msg-8',
          version: '2.0' as const,
          type: 'update' as const,
          timestamp: new Date().toISOString(),
          sequence: 8,
          payload: {
            entity: 'project' as const,
            action: 'deleted' as const,
            data: { primary: { id: 'project-1' } as any },
          },
          metadata: { source: 'mcp-ai' as const },
        },
      ];

      const initialProjects = queryClient.getQueryData<Project[]>(['projects']);
      const initialCount = initialProjects?.length || 0;

      // Trigger invalid messages
      invalidMessages.forEach(msg => {
        if (messageHandler) {
          messageHandler(msg);
        }
      });

      // Wait for processing
      await new Promise(resolve => setTimeout(resolve, 800));

      // Verify cache unchanged
      const finalProjects = queryClient.getQueryData<Project[]>(['projects']);
      expect(finalProjects?.length).toBe(initialCount);

      // All projects should still exist
      expect(finalProjects?.find(p => p.id === 'project-1')).toBeDefined();
      expect(finalProjects?.find(p => p.id === 'project-2')).toBeDefined();

      consoleErrorSpy.mockRestore();
    });
  });
});
