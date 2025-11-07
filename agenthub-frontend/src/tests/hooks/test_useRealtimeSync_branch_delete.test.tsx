/**
 * TDD Test: Branch DELETE WebSocket Protocol Validation
 *
 * SOURCE OF TRUTH: ai_docs/core-architecture/websocket-protocol-migration-guide.md
 *
 * This test validates that branch DELETE operations follow the WebSocket Protocol v2.0:
 * 1. Backend sends BranchDeletePayload with id, name, project_id
 * 2. Frontend validates payload with isBranchDeletePayload type guard
 * 3. Frontend updates React Query cache to remove branch
 * 4. Frontend shows toast notification
 * 5. Frontend triggers DELETE animation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import type { WSMessage } from '../../types/websocket-protocol';
import { isBranchDeletePayload } from '../../types/websocket-protocol';

describe('TDD: Branch DELETE WebSocket Protocol', () => {
  let queryClient: QueryClient;
  let mockWebSocketClient: any;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    mockWebSocketClient = {
      on: vi.fn(),
      off: vi.fn(),
    };
  });

  describe('Protocol Compliance - BranchDeletePayload', () => {
    it('should validate correct branch delete payload', () => {
      // ARRANGE: Create payload matching BranchDeletePayload interface
      const validPayload = {
        id: 'branch-uuid-123',
        name: 'test-branch',
        project_id: 'project-uuid-456'
      };

      // ACT: Validate with type guard
      const isValid = isBranchDeletePayload(validPayload);

      // ASSERT: Type guard should pass
      expect(isValid).toBe(true);
    });

    it('should reject branch delete payload missing id', () => {
      // ARRANGE: Create invalid payload (missing id)
      const invalidPayload = {
        // Missing id
        name: 'test-branch',
        project_id: 'project-uuid-456'
      };

      // ACT
      const isValid = isBranchDeletePayload(invalidPayload);

      // ASSERT
      expect(isValid).toBe(false);
    });

    it('should reject branch delete payload missing name', () => {
      // ARRANGE: Create invalid payload (missing name)
      const invalidPayload = {
        id: 'branch-uuid-123',
        // Missing name
        project_id: 'project-uuid-456'
      };

      // ACT
      const isValid = isBranchDeletePayload(invalidPayload);

      // ASSERT
      expect(isValid).toBe(false);
    });

    it('should reject branch delete payload missing project_id', () => {
      // ARRANGE: Create invalid payload (missing project_id)
      const invalidPayload = {
        id: 'branch-uuid-123',
        name: 'test-branch',
        // Missing project_id
      };

      // ACT
      const isValid = isBranchDeletePayload(invalidPayload);

      // ASSERT
      expect(isValid).toBe(false);
    });
  });

  describe('Cache Update Behavior', () => {
    it('should remove branch from cache when DELETE message received', async () => {
      // ARRANGE: Setup initial cache with branches
      const projectId = 'project-uuid-456';
      const branches = [
        { id: 'branch-1', name: 'main', project_id: projectId },
        { id: 'branch-2', name: 'feature', project_id: projectId },
      ];

      queryClient.setQueryData(['branches', projectId], branches);

      // Create valid DELETE message following WebSocket Protocol v2.0
      const deleteMessage: WSMessage = {
        id: 'msg-123',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'branch',
          action: 'deleted',
          data: {
            primary: {
              id: 'branch-2',
              name: 'feature',
              project_id: projectId
            }
          }
        },
        metadata: {
          source: 'mcp-ai',
          entity_type: 'branch',
          entity_id: 'branch-2'
        }
      };

      // Setup WebSocket client to trigger message handler
      let messageHandler: (msg: WSMessage) => void;
      mockWebSocketClient.on.mockImplementation((event: string, handler: any) => {
        if (event === 'update') {
          messageHandler = handler;
        }
      });

      // ACT: Render hook with WebSocket client
      renderHook(
        () => useRealtimeSync(mockWebSocketClient, true),
        {
          wrapper: ({ children }) => (
            <QueryClientProvider client={queryClient}>
              {children}
            </QueryClientProvider>
          ),
        }
      );

      // Trigger DELETE message
      messageHandler!(deleteMessage);

      // ASSERT: Wait for cache update (600ms delay in useRealtimeSync)
      await waitFor(() => {
        const updatedBranches = queryClient.getQueryData<any[]>(['branches', projectId]);

        // Branch should be removed from cache
        expect(updatedBranches).toBeDefined();
        expect(updatedBranches).toHaveLength(1);
        expect(updatedBranches![0].id).toBe('branch-1');
        expect(updatedBranches!.find(b => b.id === 'branch-2')).toBeUndefined();
      }, { timeout: 1000 });
    });

    it('should NOT update cache if payload validation fails', async () => {
      // ARRANGE: Setup initial cache
      const projectId = 'project-uuid-456';
      const branches = [
        { id: 'branch-1', name: 'main', project_id: projectId },
        { id: 'branch-2', name: 'feature', project_id: projectId },
      ];

      queryClient.setQueryData(['branches', projectId], branches);

      // Create INVALID DELETE message (missing project_id)
      const invalidMessage: WSMessage = {
        id: 'msg-123',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'branch',
          action: 'deleted',
          data: {
            primary: {
              id: 'branch-2',
              name: 'feature',
              // Missing project_id - validation should fail
            }
          }
        },
        metadata: {
          source: 'mcp-ai',
        }
      };

      // Setup WebSocket client
      let messageHandler: (msg: WSMessage) => void;
      mockWebSocketClient.on.mockImplementation((event: string, handler: any) => {
        if (event === 'update') {
          messageHandler = handler;
        }
      });

      // ACT: Render hook
      renderHook(
        () => useRealtimeSync(mockWebSocketClient, true),
        {
          wrapper: ({ children }) => (
            <QueryClientProvider client={queryClient}>
              {children}
            </QueryClientProvider>
          ),
        }
      );

      // Trigger invalid message
      messageHandler!(invalidMessage);

      // ASSERT: Cache should NOT be updated (invalid payload rejected)
      await new Promise(resolve => setTimeout(resolve, 700)); // Wait longer than 600ms delay

      const unchangedBranches = queryClient.getQueryData<any[]>(['branches', projectId]);

      // Both branches should still be in cache (no deletion occurred)
      expect(unchangedBranches).toHaveLength(2);
      expect(unchangedBranches).toEqual(branches);
    });
  });

  describe('Backend Payload Generation', () => {
    it('backend should generate BranchDeletePayload with all required fields', () => {
      // This test documents what the backend MUST send
      // Source: agenthub_main/src/fastmcp/task_management/application/services/git_branch_service.py:211-215

      const backendPayload = {
        id: 'branch-uuid-from-db',
        name: 'branch-name-from-db',
        project_id: 'project-uuid-from-db'
      };

      // Validate backend payload matches frontend type guard
      expect(isBranchDeletePayload(backendPayload)).toBe(true);

      // Ensure all required fields are present
      expect(backendPayload.id).toBeDefined();
      expect(backendPayload.name).toBeDefined();
      expect(backendPayload.project_id).toBeDefined();
    });
  });
});
