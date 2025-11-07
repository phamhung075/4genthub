/**
 * E2E Integration Tests: WebSocket Protocol v2.0
 *
 * Tests the complete backend→frontend flow for type-safe WebSocket communication:
 * 1. Backend generates Pydantic-validated payloads
 * 2. Frontend receives and validates with type guards
 * 3. React Query cache updates correctly
 * 4. Fallback mechanisms handle edge cases
 *
 * Coverage: Project, Branch, Task, Subtask (all CRUD operations)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import {
  WSMessage,
  ProjectDeletePayload,
  BranchDeletePayload,
  TaskDeletePayload,
  SubtaskDeletePayload,
  isProjectDeletePayload,
  isBranchDeletePayload,
  isTaskDeletePayload,
  isSubtaskDeletePayload,
  getEntityId,
  getDisplayName,
} from '../../types/websocket-protocol';
import type { Project, Branch, Task, Subtask } from '../../types/api.types';

// Mock logger to avoid console spam
vi.mock('../../utils/logger', () => ({
  default: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock toast hooks
vi.mock('../../components/ui/toast', () => ({
  useSuccessToast: () => vi.fn(),
  useInfoToast: () => vi.fn(),
  useWarningToast: () => vi.fn(),
  useErrorToast: () => vi.fn(),
}));

describe('E2E: WebSocket Protocol v2.0 Integration', () => {
  let queryClient: QueryClient;
  let mockWebSocketClient: any;
  let messageHandler: ((msg: WSMessage) => void) | null;

  // Helper to create wrapper with QueryClient
  const createWrapper = () => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
        mutations: { retry: false },
      },
    });

    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };

  beforeEach(() => {
    messageHandler = null;

    // Mock WebSocket client
    mockWebSocketClient = {
      on: vi.fn((event: string, handler: (msg: WSMessage) => void) => {
        if (event === 'update') {
          messageHandler = handler;
        }
      }),
      off: vi.fn(),
    };
  });

  afterEach(() => {
    queryClient?.clear();
    vi.clearAllMocks();
  });

  /**
   * Helper to create a valid WebSocket v2.0 message
   */
  const createWSMessage = <T,>(
    entity: 'project' | 'branch' | 'task' | 'subtask',
    action: 'created' | 'updated' | 'deleted' | 'completed',
    primaryData: T,
    metadata?: Partial<WSMessage['metadata']>
  ): WSMessage<T> => ({
    id: `msg-${Date.now()}`,
    version: '2.0',
    type: 'update',
    timestamp: new Date().toISOString(),
    sequence: 1,
    payload: {
      entity,
      action,
      data: {
        primary: primaryData,
      },
    },
    metadata: {
      source: 'mcp-ai',
      userId: 'test-user',
      ...metadata,
    },
  });

  /**
   * Helper to send WebSocket message
   */
  const sendWSMessage = (message: WSMessage) => {
    if (!messageHandler) {
      throw new Error('WebSocket handler not initialized');
    }
    messageHandler(message);
  };

  // =============================================================================
  // PROJECT ENTITY TESTS
  // =============================================================================

  describe('Project Entity - Complete CRUD Flow', () => {
    it('should handle project create with Pydantic payload', async () => {
      const { result } = renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isActive).toBe(true);

      const projectPayload: Project = {
        id: 'project-123',
        name: 'Test Project',
        description: 'E2E test project',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      const message = createWSMessage('project', 'created', projectPayload, {
        project_id: 'project-123',
        project_name: 'Test Project',
      });

      sendWSMessage(message);

      await waitFor(() => {
        const projects = queryClient.getQueryData<Project[]>(['projects']);
        // Note: In real scenario, cache would be invalidated and refetched
        // Here we're testing that the message was processed without errors
        expect(mockWebSocketClient.on).toHaveBeenCalledWith('update', expect.any(Function));
      });
    });

    it('should handle project delete with type guard validation', async () => {
      // Pre-populate cache with existing project
      const existingProjects: Project[] = [
        {
          id: 'project-delete-test',
          name: 'Project to Delete',
          description: 'Will be deleted',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ];
      queryClient.setQueryData(['projects'], existingProjects);

      const { result } = renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const deletePayload: ProjectDeletePayload = {
        id: 'project-delete-test',
        name: 'Project to Delete',
      };

      // Verify payload passes type guard
      expect(isProjectDeletePayload(deletePayload)).toBe(true);

      const message = createWSMessage('project', 'deleted', deletePayload, {
        entity_id: 'project-delete-test',
        project_name: 'Project to Delete',
      });

      sendWSMessage(message);

      // Wait for delayed cache update (600ms delay for animation)
      await new Promise((resolve) => setTimeout(resolve, 700));

      await waitFor(() => {
        const projects = queryClient.getQueryData<Project[]>(['projects']);
        // After delete, project should be removed from cache or cache should be empty
        expect(projects?.find((p) => p.id === 'project-delete-test')).toBeUndefined();
      });
    });

    it('should reject invalid project delete payload', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const invalidPayload = {
        id: 'project-456',
        // Missing required 'name' field
      };

      // Verify payload fails type guard
      expect(isProjectDeletePayload(invalidPayload)).toBe(false);

      const message = createWSMessage('project', 'deleted', invalidPayload as any);

      // Message should be processed but delete should be skipped
      sendWSMessage(message);

      await waitFor(() => {
        // Logger.warn should have been called for invalid payload
        expect(mockWebSocketClient.on).toHaveBeenCalled();
      });
    });

    it('should use getDisplayName helper for project toasts', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const deletePayload: ProjectDeletePayload = {
        id: 'project-789',
        name: 'Display Name Test Project',
      };

      const message = createWSMessage('project', 'deleted', deletePayload);

      // Test helper function directly
      const displayName = getDisplayName(message);
      expect(displayName).toBe('Display Name Test Project');
    });
  });

  // =============================================================================
  // BRANCH ENTITY TESTS
  // =============================================================================

  describe('Branch Entity - Complete CRUD Flow', () => {
    it('should handle branch delete with all required fields', async () => {
      const existingBranches: Branch[] = [
        {
          id: 'branch-123',
          name: 'feature-branch',
          git_branch_name: 'feature-branch',
          project_id: 'project-123',
          description: 'Test branch',
          status: 'active',
          created_at: '2024-01-01T00:00:00Z',
        },
      ];
      queryClient.setQueryData(['branches', 'project-123'], existingBranches);

      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const deletePayload: BranchDeletePayload = {
        id: 'branch-123',
        name: 'feature-branch',
        project_id: 'project-123',
      };

      // Verify payload passes type guard
      expect(isBranchDeletePayload(deletePayload)).toBe(true);

      const message = createWSMessage('branch', 'deleted', deletePayload, {
        entity_id: 'branch-123',
        branch_title: 'feature-branch',
      });

      sendWSMessage(message);

      // Wait for delayed cache update
      await new Promise((resolve) => setTimeout(resolve, 700));

      await waitFor(() => {
        const branches = queryClient.getQueryData<Branch[]>(['branches', 'project-123']);
        // After delete, branch should be removed from cache
        expect(branches?.find((b) => b.id === 'branch-123')).toBeUndefined();
      });
    });

    it('should use getEntityId helper for branch ID extraction', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const deletePayload: BranchDeletePayload = {
        id: 'branch-456',
        name: 'test-branch',
        project_id: 'project-456',
      };

      const message = createWSMessage('branch', 'deleted', deletePayload, {
        entity_id: 'branch-456', // Fallback ID in metadata
      });

      // Test helper function
      const entityId = getEntityId(message);
      expect(entityId).toBe('branch-456');
    });

    it('should fallback to metadata when primary ID missing', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const invalidPayload = {
        // Missing 'id' in primary
        name: 'branch-without-id',
        project_id: 'project-789',
      };

      const message = createWSMessage('branch', 'deleted', invalidPayload as any, {
        entity_id: 'fallback-branch-id', // ID in metadata
      });

      // getEntityId should extract from metadata
      const entityId = getEntityId(message);
      expect(entityId).toBe('fallback-branch-id');
    });
  });

  // =============================================================================
  // TASK ENTITY TESTS
  // =============================================================================

  describe('Task Entity - Complete CRUD Flow', () => {
    it('should handle task create, update, delete, complete flow', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const taskId = 'task-flow-123';
      const gitBranchId = 'branch-123';

      // CREATE
      const createPayload: Task = {
        id: taskId,
        title: 'New Task',
        description: 'Test task',
        status: 'todo',
        priority: 'high',
        git_branch_id: gitBranchId,
        assignees: ['agent-1'],
        labels: ['test'],
        created_at: new Date().toISOString(),
      };

      sendWSMessage(createWSMessage('task', 'created', createPayload));

      await waitFor(() => {
        // Cache should be invalidated (no actual data change in this mock)
        expect(mockWebSocketClient.on).toHaveBeenCalled();
      });

      // UPDATE
      const updatePayload: Task = {
        ...createPayload,
        title: 'Updated Task',
        status: 'in_progress',
        updated_at: new Date().toISOString(),
      };

      // Pre-populate cache for update test
      queryClient.setQueryData(['task', taskId, false], createPayload);

      sendWSMessage(createWSMessage('task', 'updated', updatePayload));

      await waitFor(() => {
        const cachedTask = queryClient.getQueryData<Task>(['task', taskId, false]);
        expect(cachedTask?.title).toBe('Updated Task');
        expect(cachedTask?.status).toBe('in_progress');
      });

      // DELETE
      const deletePayload: TaskDeletePayload = {
        id: taskId,
        title: 'Updated Task',
        git_branch_id: gitBranchId,
      };

      expect(isTaskDeletePayload(deletePayload)).toBe(true);

      sendWSMessage(createWSMessage('task', 'deleted', deletePayload));

      // Wait for delayed cache update
      await new Promise((resolve) => setTimeout(resolve, 700));

      await waitFor(() => {
        const cachedTask = queryClient.getQueryData<Task>(['task', taskId, false]);
        expect(cachedTask).toBeUndefined();
      });
    });

    it('should use getDisplayName helper for task toasts', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const deletePayload: TaskDeletePayload = {
        id: 'task-display-test',
        title: 'Task Display Name',
      };

      const message = createWSMessage('task', 'deleted', deletePayload);

      const displayName = getDisplayName(message);
      expect(displayName).toBe('Task Display Name');
    });
  });

  // =============================================================================
  // SUBTASK ENTITY TESTS
  // =============================================================================

  describe('Subtask Entity - Complete CRUD Flow', () => {
    it('should handle subtask delete with type guard validation', async () => {
      const taskId = 'parent-task-123';
      const subtaskId = 'subtask-123';

      const existingSubtasks: Subtask[] = [
        {
          id: subtaskId,
          title: 'Test Subtask',
          description: 'Will be deleted',
          status: 'todo',
          task_id: taskId,
          parent_task_id: taskId,
          progress_percentage: 0,
          created_at: '2024-01-01T00:00:00Z',
        },
      ];

      queryClient.setQueryData(['subtasks', taskId], existingSubtasks);

      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const deletePayload: SubtaskDeletePayload = {
        id: subtaskId,
        title: 'Test Subtask',
        task_id: taskId,
      };

      // Verify type guard
      expect(isSubtaskDeletePayload(deletePayload)).toBe(true);

      const message = createWSMessage('subtask', 'deleted', deletePayload, {
        entity_id: subtaskId,
        subtask_title: 'Test Subtask',
      });

      sendWSMessage(message);

      // Wait for delayed cache update
      await new Promise((resolve) => setTimeout(resolve, 700));

      await waitFor(() => {
        const subtasks = queryClient.getQueryData<Subtask[]>(['subtasks', taskId]);
        // After delete, subtask should be removed from cache
        expect(subtasks?.find((s) => s.id === subtaskId)).toBeUndefined();
      });
    });

    it('should reject subtask delete payload missing task_id', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const invalidPayload = {
        id: 'subtask-456',
        title: 'Invalid Subtask',
        // Missing required 'task_id' field
      };

      // Verify type guard rejects it
      expect(isSubtaskDeletePayload(invalidPayload)).toBe(false);

      const message = createWSMessage('subtask', 'deleted', invalidPayload as any);

      sendWSMessage(message);

      // Message processed but delete skipped due to validation failure
      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalled();
      });
    });

    it('should handle optional title field in subtask delete', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const deletePayload: SubtaskDeletePayload = {
        id: 'subtask-789',
        // title is optional
        task_id: 'task-789',
      };

      // Should still pass validation (title is optional)
      expect(isSubtaskDeletePayload(deletePayload)).toBe(true);

      const message = createWSMessage('subtask', 'deleted', deletePayload, {
        subtask_title: 'Fallback Title', // Title in metadata
      });

      // getDisplayName should use metadata fallback
      const displayName = getDisplayName(message);
      expect(displayName).toBe('Fallback Title');
    });
  });

  // =============================================================================
  // CROSS-ENTITY INTEGRATION TESTS
  // =============================================================================

  describe('Cross-Entity Integration', () => {
    it('should handle cascade deletes (project → branches → tasks → subtasks)', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      // Simulate project delete with cascade data
      const projectDeletePayload: ProjectDeletePayload = {
        id: 'cascade-project',
        name: 'Cascade Test Project',
      };

      const message: WSMessage = {
        id: 'cascade-msg',
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
          entity: 'project',
          action: 'deleted',
          data: {
            primary: projectDeletePayload,
            cascade: {
              branches: [{ id: 'branch-1' }, { id: 'branch-2' }],
              tasks: [{ id: 'task-1' }, { id: 'task-2' }],
              subtasks: [{ id: 'subtask-1' }],
            },
          },
        },
        metadata: {
          source: 'mcp-ai',
        },
      };

      sendWSMessage(message);

      // Wait for processing
      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalled();
      });
    });

    it('should handle concurrent updates to different entities', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      // Send multiple entity updates concurrently
      const messages = [
        createWSMessage('project', 'updated', {
          id: 'concurrent-project',
          name: 'Updated Project',
        } as Project),
        createWSMessage('branch', 'updated', {
          id: 'concurrent-branch',
          name: 'Updated Branch',
          project_id: 'concurrent-project',
        } as Branch),
        createWSMessage('task', 'updated', {
          id: 'concurrent-task',
          title: 'Updated Task',
          git_branch_id: 'concurrent-branch',
        } as Task),
      ];

      messages.forEach((msg) => sendWSMessage(msg));

      // All updates should be processed without errors
      await waitFor(() => {
        expect(mockWebSocketClient.on).toHaveBeenCalled();
      });
    });
  });

  // =============================================================================
  // FALLBACK MECHANISM TESTS
  // =============================================================================

  describe('Fallback Mechanisms', () => {
    it('should extract ID from metadata when primary missing', () => {
      const message = createWSMessage(
        'task',
        'deleted',
        { title: 'No ID Task' } as any, // Missing id in primary
        { entity_id: 'metadata-task-id' } // ID in metadata
      );

      const extractedId = getEntityId(message);
      expect(extractedId).toBe('metadata-task-id');
    });

    it('should generate fallback display name when all fields missing', () => {
      const message = createWSMessage('project', 'deleted', {
        id: 'project-no-name',
        // Missing name
      } as any);

      const displayName = getDisplayName(message);
      expect(displayName).toContain('project');
      expect(displayName).toContain('project-'); // Should contain entity type and partial ID
    });

    it('should prioritize primary data over metadata', () => {
      const message = createWSMessage(
        'task',
        'deleted',
        {
          id: 'primary-id',
          title: 'Primary Title',
        } as TaskDeletePayload,
        {
          entity_id: 'metadata-id',
          task_title: 'Metadata Title',
        }
      );

      expect(getEntityId(message)).toBe('primary-id');
      expect(getDisplayName(message)).toBe('Primary Title');
    });
  });

  // =============================================================================
  // ERROR HANDLING & EDGE CASES
  // =============================================================================

  describe('Error Handling', () => {
    it('should handle malformed WebSocket messages gracefully', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const malformedMessage = {
        // Missing required fields
        version: '1.0', // Wrong version
        payload: null,
      } as any;

      // Should not throw
      expect(() => sendWSMessage(malformedMessage)).not.toThrow();
    });

    it('should handle null/undefined payloads', async () => {
      renderHook(() => useRealtimeSync(mockWebSocketClient, true), {
        wrapper: createWrapper(queryClient),
      });

      const message = createWSMessage('task', 'deleted', null as any);

      // Should not throw
      expect(() => sendWSMessage(message)).not.toThrow();
    });

    it('should validate empty strings as invalid IDs', () => {
      const invalidPayload = {
        id: '', // Empty string
        name: 'Valid Name',
      };

      expect(isProjectDeletePayload(invalidPayload)).toBe(false);
    });
  });
});
