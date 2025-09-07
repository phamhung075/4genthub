import * as apiLazy from '../api-lazy';
import Cookies from 'js-cookie';
import * as api from '../api';

// Mock dependencies
jest.mock('js-cookie');
jest.mock('../api', () => ({
  listTasks: jest.fn(),
  listSubtasks: jest.fn(),
  getTaskContext: jest.fn(),
  listAgents: jest.fn(),
  getAvailableAgents: jest.fn()
}));

// Mock fetch globally
global.fetch = jest.fn();

describe('api-lazy.ts', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockReset();
    (Cookies.get as jest.Mock).mockReturnValue('test-token');
  });

  afterEach(() => {
    apiLazy.clearAllCache();
  });

  describe('getAuthHeaders', () => {
    it('should include authorization header when token exists', async () => {
      (Cookies.get as jest.Mock).mockReturnValue('test-token');
      
      const mockResponse = {
        branches: [],
        project_summary: {
          branches: { total: 0, active: 0, inactive: 0 },
          tasks: { total: 0, todo: 0, in_progress: 0, done: 0, urgent: 0 },
          completion_percentage: 0
        },
        total_branches: 0,
        cache_status: 'uncached'
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      await apiLazy.getBranchSummaries('proj-123');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
          })
        })
      );
    });

    it('should not include authorization header when no token', async () => {
      (Cookies.get as jest.Mock).mockReturnValue(null);

      const mockResponse = {
        branches: [],
        project_summary: {
          branches: { total: 0, active: 0, inactive: 0 },
          tasks: { total: 0, todo: 0, in_progress: 0, done: 0, urgent: 0 },
          completion_percentage: 0
        },
        total_branches: 0,
        cache_status: 'uncached'
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      await apiLazy.getBranchSummaries('proj-123');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            'Authorization': expect.any(String)
          })
        })
      );
    });
  });

  describe('getBranchSummaries', () => {
    const projectId = 'proj-123';

    it('should return branch summaries successfully', async () => {
      const mockBranches: apiLazy.BranchSummary[] = [
        {
          id: 'branch-1',
          name: 'main',
          description: 'Main branch',
          status: 'active',
          priority: 'high',
          created_at: '2024-01-01',
          updated_at: '2024-01-02',
          assigned_agent_id: 'agent-1',
          task_counts: {
            total: 10,
            by_status: { todo: 3, in_progress: 2, done: 5, blocked: 0 },
            by_priority: { urgent: 1, high: 2 },
            completion_percentage: 50
          },
          has_tasks: true,
          has_urgent_tasks: true,
          is_active: true,
          is_completed: false
        }
      ];

      const mockResponse: apiLazy.BranchSummariesResponse = {
        branches: mockBranches,
        project_summary: {
          branches: { total: 1, active: 1, inactive: 0 },
          tasks: { total: 10, todo: 3, in_progress: 2, done: 5, urgent: 1 },
          completion_percentage: 50
        },
        total_branches: 1,
        cache_status: 'cached'
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await apiLazy.getBranchSummaries(projectId);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/branches/summaries',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ project_id: projectId })
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should return fallback response when API is not available', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({})
      });

      const result = await apiLazy.getBranchSummaries(projectId);

      expect(result).toEqual({
        branches: [],
        project_summary: {
          branches: { total: 0, active: 0, inactive: 0 },
          tasks: { total: 0, todo: 0, in_progress: 0, done: 0, urgent: 0 },
          completion_percentage: 0
        },
        total_branches: 0,
        cache_status: 'uncached'
      });
    });

    it('should handle network errors gracefully', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const result = await apiLazy.getBranchSummaries(projectId);

      expect(result).toEqual({
        branches: [],
        project_summary: {
          branches: { total: 0, active: 0, inactive: 0 },
          tasks: { total: 0, todo: 0, in_progress: 0, done: 0, urgent: 0 },
          completion_percentage: 0
        },
        total_branches: 0,
        cache_status: 'error'
      });
    });
  });

  describe('getTaskSummaries', () => {
    const params = {
      git_branch_id: 'branch-123',
      page: 1,
      limit: 20,
      include_counts: true
    };

    it('should return task summaries from lightweight endpoint', async () => {
      const mockTasks: apiLazy.TaskSummary[] = [
        {
          id: 'task-1',
          title: 'Task 1',
          status: 'todo',
          priority: 'high',
          subtask_count: 2,
          assignees_count: 1,
          has_dependencies: true,
          has_context: true,
          created_at: '2024-01-01',
          updated_at: '2024-01-02'
        }
      ];

      const mockResponse: apiLazy.TaskSummariesResponse = {
        tasks: mockTasks,
        total: 1,
        page: 1,
        limit: 20,
        has_more: false
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await apiLazy.getTaskSummaries(params);

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/tasks/summaries',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            git_branch_id: params.git_branch_id,
            page: params.page,
            limit: params.limit,
            include_counts: params.include_counts,
            status_filter: undefined,
            priority_filter: undefined
          })
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should fallback to MCP endpoint when lightweight endpoint fails', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({})
      });

      const mockTasks = [
        {
          id: 'task-1',
          title: 'Task 1',
          status: 'todo',
          priority: 'high',
          subtasks: ['sub-1', 'sub-2'],
          assignees: ['user-1'],
          dependencies: ['dep-1'],
          context_id: 'ctx-1',
          created_at: '2024-01-01',
          updated_at: '2024-01-02'
        }
      ];

      (api.listTasks as jest.Mock).mockResolvedValue(mockTasks);

      const result = await apiLazy.getTaskSummaries(params);

      expect(api.listTasks).toHaveBeenCalledWith({ git_branch_id: params.git_branch_id });
      expect(result.tasks).toHaveLength(1);
      expect(result.tasks[0]).toMatchObject({
        id: 'task-1',
        title: 'Task 1',
        subtask_count: 2,
        assignees_count: 1,
        has_dependencies: true,
        has_context: true
      });
    });

    it('should support filtering by status and priority', async () => {
      const filterParams = {
        git_branch_id: 'branch-123',
        status_filter: 'in_progress',
        priority_filter: 'high'
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({
          tasks: [],
          total: 0,
          page: 1,
          limit: 20,
          has_more: false
        })
      });

      await apiLazy.getTaskSummaries(filterParams);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"status_filter":"in_progress"')
        })
      );
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"priority_filter":"high"')
        })
      );
    });

    it('should handle pagination correctly', async () => {
      const paginationParams = {
        git_branch_id: 'branch-123',
        page: 2,
        limit: 10
      };

      const mockTasks = Array.from({ length: 30 }, (_, i) => ({
        id: `task-${i}`,
        title: `Task ${i}`,
        status: 'todo',
        priority: 'medium'
      }));

      (api.listTasks as jest.Mock).mockResolvedValue(mockTasks);
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false });

      const result = await apiLazy.getTaskSummaries(paginationParams);

      expect(result.tasks).toHaveLength(10);
      expect(result.tasks[0].id).toBe('task-10');
      expect(result.tasks[9].id).toBe('task-19');
      expect(result.has_more).toBe(true);
    });
  });

  describe('getFullTask', () => {
    const taskId = 'task-123';

    it('should get full task from lightweight endpoint', async () => {
      const mockTask = {
        id: taskId,
        title: 'Full Task',
        description: 'Task description',
        status: 'in_progress',
        priority: 'high'
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockTask)
      });

      const result = await apiLazy.getFullTask(taskId);

      expect(global.fetch).toHaveBeenCalledWith(
        `http://localhost:8000/api/tasks/${taskId}`,
        expect.objectContaining({
          method: 'GET'
        })
      );
      expect(result).toEqual(mockTask);
    });

    it('should fallback to MCP endpoint when lightweight fails', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({})
      });

      const mockTask = {
        id: taskId,
        title: 'Full Task',
        status: 'todo'
      };

      (api.listTasks as jest.Mock).mockResolvedValue([
        { id: 'other-task', title: 'Other' },
        mockTask
      ]);

      const result = await apiLazy.getFullTask(taskId);

      expect(api.listTasks).toHaveBeenCalledWith({});
      expect(result).toEqual(mockTask);
    });

    it('should return null when task not found', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({})
      });

      (api.listTasks as jest.Mock).mockResolvedValue([]);

      const result = await apiLazy.getFullTask(taskId);

      expect(result).toBeNull();
    });
  });

  describe('getSubtaskSummaries', () => {
    const parentTaskId = 'task-123';

    it('should get subtask summaries from V2 endpoint', async () => {
      const mockSubtasks: apiLazy.SubtaskSummary[] = [
        {
          id: 'sub-1',
          title: 'Subtask 1',
          status: 'done',
          priority: 'medium',
          assignees_count: 1,
          progress_percentage: 100
        },
        {
          id: 'sub-2',
          title: 'Subtask 2',
          status: 'in_progress',
          priority: 'high',
          assignees_count: 2,
          progress_percentage: 50
        }
      ];

      const mockResponse: apiLazy.SubtaskSummariesResponse = {
        subtasks: mockSubtasks,
        parent_task_id: parentTaskId,
        total_count: 2,
        progress_summary: {
          total: 2,
          completed: 1,
          in_progress: 1,
          todo: 0,
          blocked: 0,
          completion_percentage: 50
        }
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await apiLazy.getSubtaskSummaries(parentTaskId);

      expect(global.fetch).toHaveBeenCalledWith(
        `http://localhost:8000/api/v2/tasks/${parentTaskId}/subtasks/summaries`,
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          }),
          body: JSON.stringify({ include_counts: true })
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should fallback to MCP endpoint when V2 fails', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({})
      });

      const mockSubtasks = [
        {
          id: 'sub-1',
          title: 'Subtask 1',
          status: 'done',
          priority: 'medium',
          assignees: ['user-1'],
          progress_percentage: 100
        },
        {
          id: 'sub-2',
          title: 'Subtask 2',
          status: 'in_progress',
          priority: 'high',
          assignees: ['user-1', 'user-2']
        }
      ];

      (api.listSubtasks as jest.Mock).mockResolvedValue(mockSubtasks);

      const result = await apiLazy.getSubtaskSummaries(parentTaskId);

      expect(api.listSubtasks).toHaveBeenCalledWith(parentTaskId);
      expect(result.subtasks).toHaveLength(2);
      expect(result.progress_summary).toEqual({
        total: 2,
        completed: 1,
        in_progress: 1,
        todo: 0,
        blocked: 0,
        completion_percentage: 50
      });
    });

    it('should calculate progress summary correctly', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false });

      const mockSubtasks = [
        { id: '1', title: 'Sub 1', status: 'done', priority: 'high', assignees: [] },
        { id: '2', title: 'Sub 2', status: 'done', priority: 'medium', assignees: [] },
        { id: '3', title: 'Sub 3', status: 'in_progress', priority: 'low', assignees: [] },
        { id: '4', title: 'Sub 4', status: 'todo', priority: 'medium', assignees: [] },
        { id: '5', title: 'Sub 5', status: 'blocked', priority: 'high', assignees: [] }
      ];

      (api.listSubtasks as jest.Mock).mockResolvedValue(mockSubtasks);

      const result = await apiLazy.getSubtaskSummaries(parentTaskId);

      expect(result.progress_summary).toEqual({
        total: 5,
        completed: 2,
        in_progress: 1,
        todo: 1,
        blocked: 1,
        completion_percentage: 40
      });
    });
  });

  describe('getTaskContextSummary', () => {
    const taskId = 'task-123';

    it('should get context summary from lightweight endpoint', async () => {
      const mockSummary = {
        has_context: true,
        context_size: 1024,
        last_updated: '2024-01-01T12:00:00Z'
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockSummary)
      });

      const result = await apiLazy.getTaskContextSummary(taskId);

      expect(global.fetch).toHaveBeenCalledWith(
        `http://localhost:8000/api/tasks/${taskId}/context/summary`,
        expect.objectContaining({
          method: 'GET'
        })
      );
      expect(result).toEqual(mockSummary);
    });

    it('should fallback to loading full context', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({})
      });

      const mockContext = {
        id: taskId,
        data: { some: 'context' }
      };

      (api.getTaskContext as jest.Mock).mockResolvedValue(mockContext);

      const result = await apiLazy.getTaskContextSummary(taskId);

      expect(api.getTaskContext).toHaveBeenCalledWith(taskId);
      expect(result).toEqual({
        has_context: true,
        context_size: JSON.stringify(mockContext).length
      });
    });

    it('should return no context when context is null', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
      (api.getTaskContext as jest.Mock).mockResolvedValue(null);

      const result = await apiLazy.getTaskContextSummary(taskId);

      expect(result).toEqual({
        has_context: false,
        context_size: 0
      });
    });

    it('should handle errors gracefully', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
      (api.getTaskContext as jest.Mock).mockRejectedValue(new Error('Context error'));

      const result = await apiLazy.getTaskContextSummary(taskId);

      expect(result).toEqual({ has_context: false });
    });
  });

  describe('getAgentSummaries', () => {
    const projectId = 'proj-123';

    it('should get agent summaries from lightweight endpoint', async () => {
      const mockResponse: apiLazy.AgentSummariesResponse = {
        available_agents: [
          { id: '@coding_agent', name: 'coding agent', type: 'development' },
          { id: '@test_agent', name: 'test agent', type: 'testing' }
        ],
        project_agents: [
          { id: 'agent-1', name: 'Project Agent 1', type: 'custom' }
        ],
        total_available: 2,
        total_assigned: 1
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await apiLazy.getAgentSummaries(projectId);

      expect(global.fetch).toHaveBeenCalledWith(
        `http://localhost:8000/api/agents/summary?project_id=${projectId}`,
        expect.objectContaining({
          method: 'GET'
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should fallback to loading full agent lists', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({})
      });

      const mockProjectAgents = [
        { id: 'agent-1', name: 'Agent 1', type: 'custom' }
      ];
      const mockAvailableAgents = [
        '@coding_agent',
        '@test_agent',
        '@debugger_agent'
      ];

      (api.listAgents as jest.Mock).mockResolvedValue(mockProjectAgents);
      (api.getAvailableAgents as jest.Mock).mockResolvedValue(mockAvailableAgents);

      const result = await apiLazy.getAgentSummaries(projectId);

      expect(api.listAgents).toHaveBeenCalledWith(projectId);
      expect(api.getAvailableAgents).toHaveBeenCalled();
      expect(result.available_agents).toHaveLength(3);
      expect(result.project_agents).toEqual(mockProjectAgents);
      expect(result.total_available).toBe(3);
      expect(result.total_assigned).toBe(1);
    });

    it('should handle errors and return empty response', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
      (api.listAgents as jest.Mock).mockRejectedValue(new Error('API error'));

      const result = await apiLazy.getAgentSummaries(projectId);

      expect(result).toEqual({
        available_agents: [],
        project_agents: [],
        total_available: 0,
        total_assigned: 0
      });
    });
  });

  describe('getPerformanceMetrics', () => {
    it('should get performance metrics successfully', async () => {
      const mockMetrics = {
        endpoints: {
          'tasks/summaries': { avg_time: 120, calls: 100 },
          'subtasks/summaries': { avg_time: 80, calls: 50 }
        },
        recommendations: ['Use pagination for large datasets']
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue(mockMetrics)
      });

      const result = await apiLazy.getPerformanceMetrics();

      expect(result).toEqual(mockMetrics);
    });

    it('should return default recommendations when endpoint not available', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({})
      });

      const result = await apiLazy.getPerformanceMetrics();

      expect(result.endpoints).toEqual({});
      expect(result.recommendations).toContain('Implement lazy loading endpoints for better performance');
    });
  });

  describe('LazyCache', () => {
    describe('basic operations', () => {
      it('should cache and retrieve data', () => {
        const testData = { test: 'data' };
        const cache = apiLazy.lazyCache;

        cache.set('test-key', testData);
        const retrieved = cache.get('test-key');

        expect(retrieved).toEqual(testData);
      });

      it('should respect TTL', async () => {
        const cache = apiLazy.lazyCache;
        const testData = { test: 'data' };

        // Set with 100ms TTL
        cache.set('test-key', testData, 100);
        
        // Should exist immediately
        expect(cache.get('test-key')).toEqual(testData);

        // Wait for expiration
        await new Promise(resolve => setTimeout(resolve, 150));

        // Should be expired
        expect(cache.get('test-key')).toBeNull();
      });

      it('should invalidate by pattern', () => {
        const cache = apiLazy.lazyCache;

        cache.set('task-1', { id: 'task-1' });
        cache.set('task-2', { id: 'task-2' });
        cache.set('subtask-1', { id: 'subtask-1' });

        cache.invalidate('task');

        expect(cache.get('task-1')).toBeNull();
        expect(cache.get('task-2')).toBeNull();
        expect(cache.get('subtask-1')).not.toBeNull();
      });

      it('should clear all cache', () => {
        const cache = apiLazy.lazyCache;

        cache.set('key-1', { data: 1 });
        cache.set('key-2', { data: 2 });

        expect(cache.size()).toBe(2);

        cache.clear();

        expect(cache.size()).toBe(0);
        expect(cache.get('key-1')).toBeNull();
        expect(cache.get('key-2')).toBeNull();
      });
    });

    describe('cached API functions', () => {
      it('should cache task summaries', async () => {
        const params = {
          git_branch_id: 'branch-123',
          page: 1,
          limit: 20
        };

        const mockResponse: apiLazy.TaskSummariesResponse = {
          tasks: [{ id: 'task-1', title: 'Task 1', status: 'todo', priority: 'high', subtask_count: 0, assignees_count: 0, has_dependencies: false, has_context: false }],
          total: 1,
          page: 1,
          limit: 20,
          has_more: false
        };

        // Mock successful response
        (global.fetch as jest.Mock).mockResolvedValue({
          ok: true,
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        // First call should hit the API
        const result1 = await apiLazy.getCachedTaskSummaries(params);
        expect(global.fetch).toHaveBeenCalledTimes(1);
        expect(result1).toEqual(mockResponse);

        // Second call should use cache
        const result2 = await apiLazy.getCachedTaskSummaries(params);
        expect(global.fetch).toHaveBeenCalledTimes(1); // Still only 1 call
        expect(result2).toEqual(mockResponse);
      });

      it('should cache subtask summaries', async () => {
        const parentTaskId = 'task-123';

        const mockResponse: apiLazy.SubtaskSummariesResponse = {
          subtasks: [],
          parent_task_id: parentTaskId,
          total_count: 0,
          progress_summary: {
            total: 0,
            completed: 0,
            in_progress: 0,
            todo: 0,
            blocked: 0,
            completion_percentage: 0
          }
        };

        (global.fetch as jest.Mock).mockResolvedValue({
          ok: true,
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        // First call
        await apiLazy.getCachedSubtaskSummaries(parentTaskId);
        expect(global.fetch).toHaveBeenCalledTimes(1);

        // Second call should use cache
        await apiLazy.getCachedSubtaskSummaries(parentTaskId);
        expect(global.fetch).toHaveBeenCalledTimes(1);
      });

      it('should cache agent summaries', async () => {
        const projectId = 'proj-123';

        const mockResponse: apiLazy.AgentSummariesResponse = {
          available_agents: [],
          project_agents: [],
          total_available: 0,
          total_assigned: 0
        };

        (global.fetch as jest.Mock).mockResolvedValue({
          ok: true,
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        // First call
        await apiLazy.getCachedAgentSummaries(projectId);
        expect(global.fetch).toHaveBeenCalledTimes(1);

        // Second call should use cache
        await apiLazy.getCachedAgentSummaries(projectId);
        expect(global.fetch).toHaveBeenCalledTimes(1);
      });
    });

    describe('cache invalidation', () => {
      it('should invalidate task cache', async () => {
        const branchId = 'branch-123';
        const params = { git_branch_id: branchId };

        (global.fetch as jest.Mock).mockResolvedValue({
          ok: true,
          json: jest.fn().mockResolvedValue({
            tasks: [],
            total: 0,
            page: 1,
            limit: 20,
            has_more: false
          })
        });

        // Load and cache
        await apiLazy.getCachedTaskSummaries(params);
        expect(global.fetch).toHaveBeenCalledTimes(1);

        // Invalidate
        apiLazy.invalidateTaskCache(branchId);

        // Next call should hit API again
        await apiLazy.getCachedTaskSummaries(params);
        expect(global.fetch).toHaveBeenCalledTimes(2);
      });

      it('should invalidate all task caches when no branch ID provided', async () => {
        // Set up some cached data
        apiLazy.lazyCache.set('task-summaries-branch1-1-20', { tasks: [] });
        apiLazy.lazyCache.set('task-summaries-branch2-1-20', { tasks: [] });
        apiLazy.lazyCache.set('subtask-summaries-task1', { subtasks: [] });

        apiLazy.invalidateTaskCache();

        expect(apiLazy.lazyCache.get('task-summaries-branch1-1-20')).toBeNull();
        expect(apiLazy.lazyCache.get('task-summaries-branch2-1-20')).toBeNull();
        expect(apiLazy.lazyCache.get('subtask-summaries-task1')).toBeNull();
      });

      it('should invalidate agent cache', () => {
        const projectId = 'proj-123';

        // Set up cached data
        apiLazy.lazyCache.set(`agent-summaries-${projectId}`, { agents: [] });
        apiLazy.lazyCache.set('agent-summaries-other', { agents: [] });

        apiLazy.invalidateAgentCache(projectId);

        expect(apiLazy.lazyCache.get(`agent-summaries-${projectId}`)).toBeNull();
        expect(apiLazy.lazyCache.get('agent-summaries-other')).not.toBeNull();
      });

      it('should clear all cache', () => {
        // Set up various cached data
        apiLazy.lazyCache.set('task-summaries-1', { tasks: [] });
        apiLazy.lazyCache.set('subtask-summaries-1', { subtasks: [] });
        apiLazy.lazyCache.set('agent-summaries-1', { agents: [] });

        expect(apiLazy.lazyCache.size()).toBe(3);

        apiLazy.clearAllCache();

        expect(apiLazy.lazyCache.size()).toBe(0);
      });
    });
  });

  describe('edge cases and error handling', () => {
    it('should handle malformed API responses', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockRejectedValue(new Error('Invalid JSON'))
      });

      await expect(apiLazy.getBranchSummaries('proj-123')).rejects.toThrow();
    });

    it('should handle network timeouts', async () => {
      (global.fetch as jest.Mock).mockImplementation(() => 
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Network timeout')), 100)
        )
      );

      const result = await apiLazy.getBranchSummaries('proj-123');
      
      expect(result.cache_status).toBe('error');
    });

    it('should handle concurrent requests to same endpoint', async () => {
      let callCount = 0;
      (global.fetch as jest.Mock).mockImplementation(() => {
        callCount++;
        return Promise.resolve({
          ok: true,
          json: jest.fn().mockResolvedValue({
            tasks: [],
            total: 0,
            page: 1,
            limit: 20,
            has_more: false
          })
        });
      });

      // Make multiple concurrent requests
      const promises = Array(5).fill(null).map(() => 
        apiLazy.getCachedTaskSummaries({ git_branch_id: 'branch-123' })
      );

      await Promise.all(promises);

      // Should only make one actual API call due to caching
      expect(callCount).toBe(1);
    });
  });
});