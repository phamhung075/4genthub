/**
 * DTO Integration Tests - Phase 2: Gradual Replacement
 *
 * Tests that backend DTO responses match frontend TypeScript interfaces
 * and that all refactored endpoints return correct structure.
 *
 * Backend DTOs tested:
 * - TaskResponse (from task_response.py)
 * - TaskListResponse (from task_list_response.py)
 * - SubtaskResponse (from subtask_response.py)
 *
 * Frontend Types tested:
 * - TaskSummary (from taskTypes.ts)
 * - SubtaskSummary (from subtaskTypes.ts)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { taskApiV2, subtaskApiV2, projectApiV2, branchApiV2 } from '../../services/apiV2';
import type { TaskSummary, SubtaskSummary } from '../../types/taskTypes';
import Cookies from 'js-cookie';

// Mock js-cookie
vi.mock('js-cookie', () => ({
  default: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn()
  }
}));

describe('DTO Integration Tests - Backend to Frontend', () => {
  const mockToken = 'test-jwt-token';

  beforeEach(() => {
    vi.clearAllMocks();
    (Cookies.get as any) = vi.fn().mockReturnValue(mockToken);
    global.fetch = vi.fn() as any;
  });

  describe('Task API DTO Tests', () => {
    describe('GET /api/v2/tasks/ - TaskListResponse', () => {
      it('should return TaskSummary[] structure matching backend TaskListResponse', async () => {
        // Backend returns TaskListResponse with tasks array
        const mockBackendResponse = {
          tasks: [
            {
              id: 'task-1',
              title: 'Test Task',
              status: 'todo',
              priority: 'high',
              subtasks: [],
              assignees: ['coding-agent'],
              labels: ['backend'],
              dependencies: [],
              has_dependencies: false,
              has_context: true,
              created_at: '2025-09-30T10:00:00Z',
              updated_at: '2025-09-30T10:00:00Z'
            }
          ],
          count: 1
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockBackendResponse)
        });

        const result = await taskApiV2.getTasks();

        // Verify response structure matches TaskListResponse DTO
        expect(result).toHaveProperty('tasks');
        expect(result).toHaveProperty('count');
        expect(Array.isArray(result.tasks)).toBe(true);
        expect(result.count).toBe(1);

        // Verify each task matches TaskSummary interface
        const task = result.tasks[0];
        expect(task).toHaveProperty('id');
        expect(task).toHaveProperty('title');
        expect(task).toHaveProperty('status');
        expect(task).toHaveProperty('priority');
        expect(task).toHaveProperty('assignees');
        expect(task).toHaveProperty('has_dependencies');
        expect(task).toHaveProperty('has_context');
      });

      it('should handle TaskSummary arrays correctly', async () => {
        const mockBackendResponse = {
          tasks: [
            {
              id: 'task-2',
              title: 'Task with arrays',
              status: 'in_progress',
              priority: 'medium',
              subtasks: ['sub-1', 'sub-2'],
              assignees: ['agent-1', 'agent-2'],
              has_dependencies: true,
              dependencies: ['dep-1'],
              has_context: false
            }
          ],
          count: 1
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockBackendResponse)
        });

        const result = await taskApiV2.getTasks();
        const task = result.tasks[0];

        // Verify arrays are present
        expect(task.subtasks).toHaveLength(2);
        expect(task.assignees).toHaveLength(2);
        expect(task.dependencies).toHaveLength(1);
      });
    });

    describe('GET /api/v2/tasks/{id} - TaskResponse', () => {
      it('should return full Task object matching backend TaskResponse', async () => {
        // Phase 2: Embedded context without duplicate fields
        const mockBackendResponse = {
          id: 'task-1',
          title: 'Full Task',
          description: 'Complete task description',
          status: 'todo',
          priority: 'high',
          details: 'Progress notes',
          estimatedEffort: '2 days',
          assignees: ['coding-agent'],
          labels: ['backend', 'dto'],
          dependencies: [],
          subtasks: [],
          dueDate: '2025-10-01',
          created_at: '2025-09-30T10:00:00Z',
          updated_at: '2025-09-30T10:00:00Z',
          git_branch_id: 'branch-1',
          context_id: 'context-1',
          // Phase 2: context_data embedded without id (id omitted when embedded)
          context_data: {
            // id omitted when embedded in task
            metadata: {
              // task_id, status, priority, timestamp omitted when embedded
              version: '1.0',
              source: 'mcp-ai'
            }
          },
          dependency_relationships: null,
          progress_percentage: 0,
          progress_history: {},
          progress_count: 0
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockBackendResponse)
        });

        const result = await taskApiV2.getTask('task-1');

        // Verify all TaskResponse fields are present
        expect(result).toHaveProperty('id');
        expect(result).toHaveProperty('title');
        expect(result).toHaveProperty('description');
        expect(result).toHaveProperty('status');
        expect(result).toHaveProperty('priority');
        expect(result).toHaveProperty('details');
        expect(result).toHaveProperty('estimatedEffort');
        expect(result).toHaveProperty('assignees');
        expect(result).toHaveProperty('labels');
        expect(result).toHaveProperty('dependencies');
        expect(result).toHaveProperty('subtasks');
        expect(result).toHaveProperty('git_branch_id');
        expect(result).toHaveProperty('context_id');
        expect(result).toHaveProperty('progress_percentage');
        expect(result).toHaveProperty('progress_history');
      });
    });

    describe('POST /api/v2/tasks/ - CreateTaskResponse', () => {
      it('should create task and return TaskResponse structure', async () => {
        const taskData = {
          title: 'New Task',
          description: 'New task description',
          git_branch_id: 'branch-1',
          assignees: ['coding-agent']
        };

        const mockBackendResponse = {
          id: 'new-task-id',
          ...taskData,
          status: 'todo',
          priority: 'medium',
          details: '',
          estimatedEffort: '',
          labels: [],
          dependencies: [],
          subtasks: [],
          dueDate: null,
          created_at: '2025-09-30T10:00:00Z',
          updated_at: '2025-09-30T10:00:00Z',
          context_id: 'new-context-id',
          progress_percentage: 0
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockBackendResponse)
        });

        const result = await taskApiV2.createTask(taskData);

        // Verify created task has all required fields
        expect(result).toHaveProperty('id');
        expect(result.title).toBe(taskData.title);
        expect(result.description).toBe(taskData.description);
        expect(result).toHaveProperty('status');
        expect(result).toHaveProperty('priority');
      });
    });

    describe('PUT /api/v2/tasks/{id} - UpdateTaskResponse', () => {
      it('should update task and return updated TaskResponse', async () => {
        const updates = {
          title: 'Updated Task',
          status: 'in_progress',
          progress_percentage: 50
        };

        const mockBackendResponse = {
          id: 'task-1',
          ...updates,
          description: 'Original description',
          priority: 'high',
          details: 'Progress: 50%',
          estimatedEffort: '2 days',
          assignees: ['coding-agent'],
          labels: [],
          dependencies: [],
          subtasks: [],
          created_at: '2025-09-30T10:00:00Z',
          updated_at: '2025-09-30T10:30:00Z',
          progress_history: {
            progress_1: {
              content: 'Updated to 50%',
              timestamp: '2025-09-30T10:30:00Z'
            }
          },
          progress_count: 1
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockBackendResponse)
        });

        const result = await taskApiV2.updateTask('task-1', updates);

        // Verify updated fields
        expect(result.title).toBe(updates.title);
        expect(result.status).toBe(updates.status);
        expect(result.progress_percentage).toBe(updates.progress_percentage);
        expect(result.progress_count).toBe(1);
      });
    });

    describe('DELETE /api/v2/tasks/{id} - DeleteResponse', () => {
      it('should return success response on task deletion', async () => {
        const mockBackendResponse = {
          success: true,
          message: 'Task deleted successfully'
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          status: 204,
          json: vi.fn().mockResolvedValue(mockBackendResponse)
        });

        const result = await taskApiV2.deleteTask('task-1');

        // Verify delete response
        expect(result).toHaveProperty('success');
        expect(result.success).toBe(true);
      });
    });
  });

  describe('Subtask API DTO Tests', () => {
    describe('GET /api/v2/subtasks/task/{id} - SubtasksResponse', () => {
      it('should return SubtaskSummary[] matching backend SubtasksResponse', async () => {
        // Phase 2: Subtasks nested in parent response - parent_task_id omitted
        const mockBackendResponse = {
          subtasks: [
            {
              id: 'subtask-1',
              // parent_task_id omitted when nested in parent task response
              title: 'Subtask 1',
              status: 'todo',
              priority: 'high',
              assignees: ['coding-agent'],
              progress_percentage: 0,
              created_at: '2025-09-30T10:00:00Z',
              updated_at: '2025-09-30T10:00:00Z'
            }
          ],
          count: 1
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          headers: new Headers(),  // Add headers to prevent logging error
          json: vi.fn().mockResolvedValue(mockBackendResponse)
        });

        const result = await subtaskApiV2.listSubtasksForTask('task-1');

        // Verify SubtasksResponse structure
        expect(result).toHaveProperty('subtasks');
        expect(Array.isArray(result.subtasks)).toBe(true);

        // Verify SubtaskSummary fields
        const subtask = result.subtasks[0];
        expect(subtask).toHaveProperty('id');
        expect(subtask).toHaveProperty('title');
        expect(subtask).toHaveProperty('status');
        expect(subtask).toHaveProperty('priority');
        expect(subtask).toHaveProperty('assignees');
        expect(subtask).toHaveProperty('progress_percentage');
      });
    });

    describe('GET /api/v2/subtasks/{id} - SubtaskResponse', () => {
      it('should return full Subtask object matching backend SubtaskResponse', async () => {
        // Use valid UUID format for subtask ID
        const validSubtaskId = '550e8400-e29b-41d4-a716-446655440000';

        // Phase 2: Standalone subtask response KEEPS parent_task_id
        const mockBackendResponse = {
          task_id: 'task-1',
          subtask: {
            id: validSubtaskId,
            parent_task_id: 'task-1',  // ✅ Included when standalone
            title: 'Full Subtask',
            description: 'Subtask description',
            status: 'in_progress',
            priority: 'medium',
            assignees: ['coding-agent'],
            progress_percentage: 50,
            created_at: '2025-09-30T10:00:00Z',
            updated_at: '2025-09-30T10:15:00Z'
          },
          progress: {
            total: 1,
            completed: 0,
            percentage: 0
          }
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockBackendResponse)
        });

        const result = await subtaskApiV2.getSubtask(validSubtaskId);

        // Verify SubtaskResponse structure
        expect(result).toHaveProperty('task_id');
        expect(result).toHaveProperty('subtask');
        expect(result).toHaveProperty('progress');

        // Verify subtask fields
        const subtask = result.subtask;
        expect(subtask).toHaveProperty('id');
        expect(subtask).toHaveProperty('title');
        expect(subtask).toHaveProperty('description');
        expect(subtask).toHaveProperty('status');
        expect(subtask).toHaveProperty('progress_percentage');
      });
    });

    describe('POST /api/v2/subtasks - CreateSubtaskResponse', () => {
      it('should create subtask and return SubtaskResponse', async () => {
        const subtaskData = {
          title: 'New Subtask',
          description: 'Subtask description'
        };

        const mockBackendResponse = {
          task_id: 'task-1',
          subtask: {
            id: 'new-subtask-id',
            ...subtaskData,
            status: 'todo',
            priority: 'medium',
            assignees: [],
            progress_percentage: 0,
            created_at: '2025-09-30T10:00:00Z',
            updated_at: '2025-09-30T10:00:00Z'
          },
          progress: {
            total: 1,
            completed: 0,
            percentage: 0
          }
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockBackendResponse)
        });

        const result = await subtaskApiV2.createSubtask('task-1', subtaskData);

        expect(result.task_id).toBe('task-1');
        expect(result.subtask.title).toBe(subtaskData.title);
      });
    });
  });

  describe('Error Handling DTO Tests', () => {
    it('should handle 404 Not Found with proper error structure', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: false,
        status: 404,
        url: 'http://localhost:8000/api/v2/tasks/invalid-id',
        json: vi.fn().mockResolvedValue({ detail: 'Task not found' })
      });

      await expect(taskApiV2.getTask('invalid-id')).rejects.toThrow('Task not found');
    });

    it('should handle 422 Validation Error with detailed messages', async () => {
      const mockValidationError = {
        detail: [
          {
            loc: ['body', 'title'],
            msg: 'field required',
            type: 'value_error.missing'
          }
        ]
      };

      (global.fetch as any).mockResolvedValue({
        ok: false,
        status: 422,
        json: vi.fn().mockResolvedValue(mockValidationError)
      });

      await expect(taskApiV2.createTask({ title: '' } as any)).rejects.toThrow();
    });

    it('should handle 401 Authentication Error', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: false,
        status: 401,
        json: vi.fn().mockResolvedValue({ detail: 'Token expired' })
      });

      // The 401 handler will try to refresh, then fail
      // We expect an authentication error to be thrown
      await expect(taskApiV2.getTasks()).rejects.toThrow();
    });
  });

  describe('Field Type Validation', () => {
    it('should handle datetime fields as ISO strings', async () => {
      const mockBackendResponse = {
        tasks: [
          {
            id: 'task-1',
            title: 'Test Task',
            status: 'todo',
            priority: 'high',
            created_at: '2025-09-30T10:00:00.000000+00:00',
            updated_at: '2025-09-30T10:30:00.000000+00:00',
            assignees: [],
            labels: [],
            dependencies: [],
            subtasks: []
          }
        ],
        count: 1
      };

      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockBackendResponse)
      });

      const result = await taskApiV2.getTasks();
      const task = result.tasks[0];

      // Verify datetime fields are strings
      expect(typeof task.created_at).toBe('string');
      expect(typeof task.updated_at).toBe('string');

      // Verify they can be parsed as dates
      expect(new Date(task.created_at)).toBeInstanceOf(Date);
      expect(new Date(task.updated_at)).toBeInstanceOf(Date);
    });

    it('should handle arrays correctly (assignees, labels, dependencies)', async () => {
      const mockBackendResponse = {
        tasks: [
          {
            id: 'task-1',
            title: 'Test Task',
            status: 'todo',
            priority: 'high',
            assignees: ['agent-1', 'agent-2'],
            labels: ['backend', 'dto', 'testing'],
            dependencies: ['dep-1'],
            subtasks: []
          }
        ],
        count: 1
      };

      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockBackendResponse)
      });

      const result = await taskApiV2.getTasks();
      const task = result.tasks[0];

      // Verify arrays
      expect(Array.isArray(task.assignees)).toBe(true);
      expect(Array.isArray(task.labels)).toBe(true);
      expect(Array.isArray(task.dependencies)).toBe(true);
      expect(task.assignees).toHaveLength(2);
      expect(task.labels).toHaveLength(3);
      expect(task.dependencies).toHaveLength(1);
    });

    it('should handle optional fields correctly', async () => {
      const mockBackendResponse = {
        tasks: [
          {
            id: 'task-1',
            title: 'Minimal Task',
            status: 'todo',
            priority: 'medium',
            assignees: [],
            labels: [],
            dependencies: [],
            subtasks: [],
            // Optional fields are null or undefined
            due_date: null,
            git_branch_id: undefined,
            context_id: null
          }
        ],
        count: 1
      };

      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockBackendResponse)
      });

      const result = await taskApiV2.getTasks();
      const task = result.tasks[0];

      // Verify optional fields don't break parsing
      expect(task.due_date).toBeNull();
    });
  });
});