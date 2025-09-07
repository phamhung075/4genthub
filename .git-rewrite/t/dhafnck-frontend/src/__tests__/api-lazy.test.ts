/**
 * Tests for Enhanced API Service with Lazy Loading Support
 */

import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import Cookies from 'js-cookie';
import {
  getBranchSummaries,
  getTaskSummaries,
  getFullTask,
  getSubtaskSummaries,
  getTaskContextSummary,
  getAgentSummaries,
  getPerformanceMetrics,
  lazyCache,
  getCachedTaskSummaries,
  getCachedSubtaskSummaries,
  getCachedAgentSummaries,
  invalidateTaskCache,
  invalidateAgentCache,
  clearAllCache,
  TaskSummary,
  SubtaskSummary,
  BranchSummary
} from '../api-lazy';

// Mock fetch globally
global.fetch = vi.fn();

// Mock js-cookie
vi.mock('js-cookie', () => ({
  default: {
    get: vi.fn()
  }
}));

// Mock the api module imports
vi.mock('../api', () => ({
  listTasks: vi.fn(),
  listSubtasks: vi.fn(),
  listAgents: vi.fn(),
  getAvailableAgents: vi.fn(),
  getTaskContext: vi.fn()
}));

describe('api-lazy', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearAllCache();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('getAuthHeaders', () => {
    test('should include bearer token when access_token exists', async () => {
      // Mock Cookies.get to return a token
      vi.mocked(Cookies.get).mockReturnValue('test-token-123');
      
      // Call a function that uses getAuthHeaders internally
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ subtasks: [] })
      });
      
      await getSubtaskSummaries('task-123');
      
      // Check that fetch was called with correct headers
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token-123',
            'Content-Type': 'application/json'
          })
        })
      );
    });

    test('should not include authorization header when no token', async () => {
      vi.mocked(Cookies.get).mockReturnValue(undefined);
      
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ subtasks: [] })
      });
      
      await getSubtaskSummaries('task-123');
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      );
      
      const headers = (global.fetch as any).mock.calls[0][1].headers;
      expect(headers['Authorization']).toBeUndefined();
    });
  });

  describe('getBranchSummaries', () => {
    test('should return branch summaries when API call succeeds', async () => {
      const mockResponse = {
        branches: [
          {
            id: 'branch-1',
            name: 'main',
            task_counts: {
              total: 10,
              by_status: { todo: 5, in_progress: 3, done: 2, blocked: 0 },
              by_priority: { urgent: 1, high: 2 },
              completion_percentage: 20
            },
            has_tasks: true,
            has_urgent_tasks: true,
            is_active: true,
            is_completed: false
          }
        ],
        project_summary: {
          branches: { total: 1, active: 1, inactive: 0 },
          tasks: { total: 10, todo: 5, in_progress: 3, done: 2, urgent: 1 },
          completion_percentage: 20
        },
        total_branches: 1,
        cache_status: 'cached'
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });

      const result = await getBranchSummaries('project-123');
      
      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/branches/summaries',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ project_id: 'project-123' })
        })
      );
    });

    test('should return empty response when API fails', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const result = await getBranchSummaries('project-123');
      
      expect(result.branches).toEqual([]);
      expect(result.total_branches).toBe(0);
      expect(result.cache_status).toBe('error');
    });
  });

  describe('getTaskSummaries', () => {
    test('should return task summaries from API endpoint', async () => {
      const mockResponse = {
        tasks: [
          {
            id: 'task-1',
            title: 'Test Task',
            status: 'todo',
            priority: 'high',
            subtask_count: 2,
            assignees_count: 1,
            has_dependencies: false,
            has_context: true
          }
        ],
        total: 1,
        page: 1,
        limit: 20,
        has_more: false
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });

      const result = await getTaskSummaries({
        git_branch_id: 'branch-123',
        page: 1,
        limit: 20
      });
      
      expect(result).toEqual(mockResponse);
    });

    test('should fallback to MCP endpoint when API fails', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('API error'));

      const mockTasks = [
        {
          id: 'task-1',
          title: 'Test Task',
          status: 'todo',
          priority: 'high',
          subtasks: ['sub-1', 'sub-2'],
          assignees: ['user-1'],
          dependencies: [],
          context_id: 'ctx-123',
          created_at: '2024-01-01',
          updated_at: '2024-01-02'
        }
      ];

      const { listTasks } = await import('../api');
      vi.mocked(listTasks).mockResolvedValue(mockTasks);

      const result = await getTaskSummaries({
        git_branch_id: 'branch-123',
        page: 1,
        limit: 20
      });
      
      expect(result.tasks[0]).toMatchObject({
        id: 'task-1',
        title: 'Test Task',
        status: 'todo',
        priority: 'high',
        subtask_count: 2,
        assignees_count: 1,
        has_dependencies: false,
        has_context: true
      });
    });

    test('should handle filters in task summaries', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ tasks: [], total: 0, page: 1, limit: 20, has_more: false })
      });

      await getTaskSummaries({
        git_branch_id: 'branch-123',
        status_filter: 'todo',
        priority_filter: 'high'
      });
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"status_filter":"todo"')
        })
      );
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"priority_filter":"high"')
        })
      );
    });
  });

  describe('getFullTask', () => {
    test('should return full task from API endpoint', async () => {
      const mockTask = {
        id: 'task-123',
        title: 'Full Task',
        description: 'Task description',
        status: 'todo'
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTask
      });

      const result = await getFullTask('task-123');
      
      expect(result).toEqual(mockTask);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/tasks/task-123',
        expect.objectContaining({
          method: 'GET'
        })
      );
    });

    test('should fallback to MCP when API fails', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('API error'));

      const mockTasks = [
        { id: 'task-123', title: 'Task 1' },
        { id: 'task-456', title: 'Task 2' }
      ];

      const { listTasks } = await import('../api');
      vi.mocked(listTasks).mockResolvedValue(mockTasks);

      const result = await getFullTask('task-123');
      
      expect(result).toEqual({ id: 'task-123', title: 'Task 1' });
    });
  });

  describe('getSubtaskSummaries', () => {
    test('should return subtask summaries from v2 endpoint', async () => {
      vi.mocked(Cookies.get).mockReturnValue('test-token');
      
      const mockResponse = {
        subtasks: [
          {
            id: 'sub-1',
            title: 'Subtask 1',
            status: 'done',
            priority: 'medium',
            assignees_count: 1,
            progress_percentage: 100
          }
        ],
        parent_task_id: 'task-123',
        total_count: 1,
        progress_summary: {
          total: 1,
          completed: 1,
          in_progress: 0,
          todo: 0,
          blocked: 0,
          completion_percentage: 100
        }
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });

      const result = await getSubtaskSummaries('task-123');
      
      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v2/tasks/task-123/subtasks/summaries',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          })
        })
      );
    });

    test('should calculate progress summary correctly in fallback', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('API error'));

      const mockSubtasks = [
        { id: 'sub-1', title: 'Sub 1', status: 'done', priority: 'high', assignees: ['user-1'], progress_percentage: 100 },
        { id: 'sub-2', title: 'Sub 2', status: 'in_progress', priority: 'medium', assignees: [], progress_percentage: 50 },
        { id: 'sub-3', title: 'Sub 3', status: 'todo', priority: 'low', assignees: [], progress_percentage: 0 }
      ];

      const { listSubtasks } = await import('../api');
      vi.mocked(listSubtasks).mockResolvedValue(mockSubtasks);

      const result = await getSubtaskSummaries('task-123');
      
      expect(result.progress_summary).toEqual({
        total: 3,
        completed: 1,
        in_progress: 1,
        todo: 1,
        blocked: 0,
        completion_percentage: 33
      });
    });
  });

  describe('getTaskContextSummary', () => {
    test('should return context summary from API', async () => {
      const mockResponse = {
        has_context: true,
        context_size: 1024,
        last_updated: '2024-01-01T00:00:00Z'
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });

      const result = await getTaskContextSummary('task-123');
      
      expect(result).toEqual(mockResponse);
    });

    test('should fallback to checking context existence', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('API error'));

      const mockContext = { data: 'test context' };
      const { getTaskContext } = await import('../api');
      vi.mocked(getTaskContext).mockResolvedValue(mockContext);

      const result = await getTaskContextSummary('task-123');
      
      expect(result.has_context).toBe(true);
      expect(result.context_size).toBe(JSON.stringify(mockContext).length);
    });

    test('should return no context when all methods fail', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('API error'));

      const { getTaskContext } = await import('../api');
      vi.mocked(getTaskContext).mockRejectedValue(new Error('Context error'));

      const result = await getTaskContextSummary('task-123');
      
      expect(result).toEqual({ has_context: false });
    });
  });

  describe('getAgentSummaries', () => {
    test('should return agent summaries from API', async () => {
      const mockResponse = {
        available_agents: [
          { id: '@agent1', name: 'Agent 1', type: 'coding' }
        ],
        project_agents: [
          { id: '@agent2', name: 'Agent 2', type: 'testing' }
        ],
        total_available: 1,
        total_assigned: 1
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });

      const result = await getAgentSummaries('project-123');
      
      expect(result).toEqual(mockResponse);
    });

    test('should fallback and transform agent data', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('API error'));

      const { listAgents, getAvailableAgents } = await import('../api');
      vi.mocked(listAgents).mockResolvedValue([
        { id: '@project_agent', name: 'Project Agent', type: 'coding' }
      ]);
      vi.mocked(getAvailableAgents).mockResolvedValue(['@coding_agent', '@test_agent']);

      const result = await getAgentSummaries('project-123');
      
      expect(result.available_agents).toHaveLength(2);
      expect(result.available_agents[0]).toEqual({
        id: '@coding_agent',
        name: 'coding agent',
        type: 'unknown'
      });
    });
  });

  describe('Caching System', () => {
    test('LazyCache should store and retrieve data', () => {
      const testData = { id: 'test', value: 123 };
      lazyCache.set('test-key', testData);
      
      const retrieved = lazyCache.get('test-key');
      expect(retrieved).toEqual(testData);
    });

    test('LazyCache should expire data after TTL', () => {
      const testData = { id: 'test' };
      
      // Set with 100ms TTL
      lazyCache.set('test-key', testData, 100);
      
      // Should exist immediately
      expect(lazyCache.get('test-key')).toEqual(testData);
      
      // Mock time passing
      vi.useFakeTimers();
      vi.advanceTimersByTime(150);
      
      // Should be expired
      expect(lazyCache.get('test-key')).toBeNull();
      
      vi.useRealTimers();
    });

    test('LazyCache invalidation should work with pattern matching', () => {
      lazyCache.set('task-1', { id: 'task-1' });
      lazyCache.set('task-2', { id: 'task-2' });
      lazyCache.set('subtask-1', { id: 'subtask-1' });
      
      expect(lazyCache.size()).toBe(3);
      
      lazyCache.invalidate('task');
      
      expect(lazyCache.size()).toBe(0); // All contain 'task'
    });

    test('getCachedTaskSummaries should use cache on second call', async () => {
      const mockResponse = {
        tasks: [{ id: 'task-1', title: 'Cached Task' }],
        total: 1,
        page: 1,
        limit: 20,
        has_more: false
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });

      // First call - should fetch
      const result1 = await getCachedTaskSummaries({ git_branch_id: 'branch-123' });
      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(result1).toEqual(mockResponse);

      // Second call - should use cache
      const result2 = await getCachedTaskSummaries({ git_branch_id: 'branch-123' });
      expect(global.fetch).toHaveBeenCalledTimes(1); // Still 1
      expect(result2).toEqual(mockResponse);
    });

    test('cache invalidation functions should work correctly', () => {
      // Add some cached data
      lazyCache.set('task-summaries-branch-123-1-20', { data: 'tasks' });
      lazyCache.set('subtask-summaries-task-456', { data: 'subtasks' });
      lazyCache.set('agent-summaries-project-789', { data: 'agents' });
      
      expect(lazyCache.size()).toBe(3);
      
      // Invalidate task cache for specific branch
      invalidateTaskCache('branch-123');
      expect(lazyCache.get('task-summaries-branch-123-1-20')).toBeNull();
      expect(lazyCache.get('agent-summaries-project-789')).not.toBeNull();
      
      // Invalidate all agent cache
      invalidateAgentCache();
      expect(lazyCache.get('agent-summaries-project-789')).toBeNull();
    });
  });

  describe('getPerformanceMetrics', () => {
    test('should return metrics when API available', async () => {
      const mockMetrics = {
        endpoints: {
          task_summaries: { avg_response_time: '45ms' }
        },
        recommendations: ['Use caching']
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockMetrics
      });

      const result = await getPerformanceMetrics();
      
      expect(result).toEqual(mockMetrics);
    });

    test('should return default recommendations when API fails', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('API error'));

      const result = await getPerformanceMetrics();
      
      expect(result.recommendations).toContain('Implement lazy loading endpoints for better performance');
    });
  });
});