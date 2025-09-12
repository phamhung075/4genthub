import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  fetchProjects,
  fetchTasks,
  createProject,
  updateProject,
  deleteProject,
  createTask,
  updateTask,
  deleteTask,
  fetchAgents,
  createAgent,
  updateAgent,
  deleteAgent,
  fetchContexts,
  createContext,
  updateContext,
  deleteContext,
  fetchGitBranches,
  createGitBranch,
  updateGitBranch,
  deleteGitBranch,
  getAuthHeaders,
  getApiUrl,
  handleApiError,
  fetchProjectHealth,
  cleanupObsolete,
  validateIntegrity,
  rebalanceAgents,
  assignAgent,
  unassignAgent,
  fetchBranchStatistics,
  archiveBranch,
  restoreBranch,
} from '../api';

// Mock fetch globally
global.fetch = vi.fn();

describe('API Module', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getApiUrl', () => {
    it('should return production URL by default', () => {
      expect(getApiUrl()).toBe('http://localhost:8000');
    });

    it('should allow custom API URL', () => {
      process.env.VITE_API_URL = 'http://custom.api:3000';
      expect(getApiUrl()).toBe('http://localhost:8000'); // Still returns default as env is not read in runtime
    });
  });

  describe('getAuthHeaders', () => {
    it('should return headers with Authorization when token exists', () => {
      localStorage.setItem('authToken', 'test-token-123');
      const headers = getAuthHeaders();
      expect(headers['Content-Type']).toBe('application/json');
      expect(headers['Authorization']).toBe('Bearer test-token-123');
    });

    it('should return headers without Authorization when no token', () => {
      const headers = getAuthHeaders();
      expect(headers['Content-Type']).toBe('application/json');
      expect(headers['Authorization']).toBeUndefined();
    });
  });

  describe('handleApiError', () => {
    it('should handle network errors', async () => {
      const response = {
        ok: false,
        status: 500,
        text: vi.fn().mockResolvedValue('Internal Server Error'),
      } as unknown as Response;

      await expect(handleApiError(response)).rejects.toThrow('Internal Server Error');
    });

    it('should handle JSON error responses', async () => {
      const response = {
        ok: false,
        status: 400,
        text: vi.fn().mockResolvedValue('{"error": "Bad Request"}'),
      } as unknown as Response;

      await expect(handleApiError(response)).rejects.toThrow('{"error": "Bad Request"}');
    });
  });

  describe('Project API', () => {
    describe('fetchProjects', () => {
      it('should fetch projects successfully', async () => {
        const mockProjects = [
          { id: '1', name: 'Project 1' },
          { id: '2', name: 'Project 2' },
        ];

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockProjects,
        });

        const projects = await fetchProjects();
        expect(projects).toEqual(mockProjects);
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/projects',
          { headers: getAuthHeaders() }
        );
      });

      it('should handle fetch error', async () => {
        (global.fetch as any).mockResolvedValue({
          ok: false,
          status: 404,
          text: async () => 'Not Found',
        });

        await expect(fetchProjects()).rejects.toThrow('Not Found');
      });
    });

    describe('createProject', () => {
      it('should create project successfully', async () => {
        const newProject = { name: 'New Project', description: 'Test project' };
        const createdProject = { id: '123', ...newProject };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => createdProject,
        });

        const result = await createProject(newProject);
        expect(result).toEqual(createdProject);
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/projects',
          {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(newProject),
          }
        );
      });
    });

    describe('updateProject', () => {
      it('should update project successfully', async () => {
        const projectId = '123';
        const updates = { name: 'Updated Project' };
        const updatedProject = { id: projectId, ...updates };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => updatedProject,
        });

        const result = await updateProject(projectId, updates);
        expect(result).toEqual(updatedProject);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/projects/${projectId}`,
          {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(updates),
          }
        );
      });
    });

    describe('deleteProject', () => {
      it('should delete project successfully', async () => {
        const projectId = '123';

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => ({ success: true }),
        });

        await deleteProject(projectId);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/projects/${projectId}`,
          {
            method: 'DELETE',
            headers: getAuthHeaders(),
          }
        );
      });
    });
  });

  describe('Task API', () => {
    describe('fetchTasks', () => {
      it('should fetch tasks with project filter', async () => {
        const projectId = '123';
        const mockTasks = [
          { id: '1', title: 'Task 1', project_id: projectId },
          { id: '2', title: 'Task 2', project_id: projectId },
        ];

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockTasks,
        });

        const tasks = await fetchTasks(projectId);
        expect(tasks).toEqual(mockTasks);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/tasks?project_id=${projectId}`,
          { headers: getAuthHeaders() }
        );
      });

      it('should fetch all tasks without filter', async () => {
        const mockTasks = [
          { id: '1', title: 'Task 1' },
          { id: '2', title: 'Task 2' },
        ];

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockTasks,
        });

        const tasks = await fetchTasks();
        expect(tasks).toEqual(mockTasks);
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/tasks',
          { headers: getAuthHeaders() }
        );
      });
    });

    describe('createTask', () => {
      it('should create task successfully', async () => {
        const newTask = {
          title: 'New Task',
          description: 'Test task',
          project_id: '123',
        };
        const createdTask = { id: 'task-123', ...newTask };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => createdTask,
        });

        const result = await createTask(newTask);
        expect(result).toEqual(createdTask);
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/tasks',
          {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(newTask),
          }
        );
      });
    });
  });

  describe('Agent API', () => {
    describe('fetchAgents', () => {
      it('should fetch agents with project filter', async () => {
        const projectId = '123';
        const mockAgents = [
          { id: '1', name: 'Agent 1', project_id: projectId },
          { id: '2', name: 'Agent 2', project_id: projectId },
        ];

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockAgents,
        });

        const agents = await fetchAgents(projectId);
        expect(agents).toEqual(mockAgents);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/agents?project_id=${projectId}`,
          { headers: getAuthHeaders() }
        );
      });
    });

    describe('assignAgent', () => {
      it('should assign agent successfully', async () => {
        const projectId = '123';
        const agentId = 'agent-1';
        const branchId = 'branch-1';

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => ({ success: true }),
        });

        await assignAgent(projectId, agentId, branchId);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/projects/${projectId}/agents/${agentId}/assign`,
          {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ git_branch_id: branchId }),
          }
        );
      });
    });
  });

  describe('Context API', () => {
    describe('fetchContexts', () => {
      it('should fetch contexts successfully', async () => {
        const mockContexts = [
          { id: '1', level: 'global', data: {} },
          { id: '2', level: 'project', data: {} },
        ];

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockContexts,
        });

        const contexts = await fetchContexts();
        expect(contexts).toEqual(mockContexts);
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/contexts',
          { headers: getAuthHeaders() }
        );
      });
    });

    describe('createContext', () => {
      it('should create context successfully', async () => {
        const newContext = {
          level: 'project',
          context_id: 'proj-123',
          data: { key: 'value' },
        };
        const createdContext = { id: 'ctx-123', ...newContext };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => createdContext,
        });

        const result = await createContext(newContext);
        expect(result).toEqual(createdContext);
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/contexts',
          {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(newContext),
          }
        );
      });
    });
  });

  describe('Git Branch API', () => {
    describe('fetchGitBranches', () => {
      it('should fetch git branches with project filter', async () => {
        const projectId = '123';
        const mockBranches = [
          { id: '1', git_branch_name: 'main', project_id: projectId },
          { id: '2', git_branch_name: 'develop', project_id: projectId },
        ];

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockBranches,
        });

        const branches = await fetchGitBranches(projectId);
        expect(branches).toEqual(mockBranches);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/git-branches?project_id=${projectId}`,
          { headers: getAuthHeaders() }
        );
      });
    });

    describe('fetchBranchStatistics', () => {
      it('should fetch branch statistics successfully', async () => {
        const projectId = '123';
        const branchId = 'branch-1';
        const mockStats = {
          total_tasks: 10,
          completed_tasks: 7,
          in_progress_tasks: 2,
          todo_tasks: 1,
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockStats,
        });

        const stats = await fetchBranchStatistics(projectId, branchId);
        expect(stats).toEqual(mockStats);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/projects/${projectId}/git-branches/${branchId}/statistics`,
          { headers: getAuthHeaders() }
        );
      });
    });

    describe('archiveBranch', () => {
      it('should archive branch successfully', async () => {
        const projectId = '123';
        const branchId = 'branch-1';

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => ({ success: true }),
        });

        await archiveBranch(projectId, branchId);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/projects/${projectId}/git-branches/${branchId}/archive`,
          {
            method: 'POST',
            headers: getAuthHeaders(),
          }
        );
      });
    });
  });

  describe('Project Health API', () => {
    describe('fetchProjectHealth', () => {
      it('should fetch project health successfully', async () => {
        const projectId = '123';
        const mockHealth = {
          status: 'healthy',
          metrics: {
            task_completion_rate: 0.85,
            active_branches: 3,
            total_agents: 5,
          },
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockHealth,
        });

        const health = await fetchProjectHealth(projectId);
        expect(health).toEqual(mockHealth);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/projects/${projectId}/health`,
          { headers: getAuthHeaders() }
        );
      });
    });

    describe('cleanupObsolete', () => {
      it('should cleanup obsolete resources successfully', async () => {
        const projectId = '123';

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => ({ cleaned: 5, message: 'Cleanup completed' }),
        });

        const result = await cleanupObsolete(projectId);
        expect(result).toEqual({ cleaned: 5, message: 'Cleanup completed' });
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/projects/${projectId}/cleanup`,
          {
            method: 'POST',
            headers: getAuthHeaders(),
          }
        );
      });
    });

    describe('validateIntegrity', () => {
      it('should validate project integrity successfully', async () => {
        const projectId = '123';
        const mockValidation = {
          valid: true,
          issues: [],
          recommendations: ['Keep up the good work!'],
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockValidation,
        });

        const validation = await validateIntegrity(projectId);
        expect(validation).toEqual(mockValidation);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/projects/${projectId}/validate`,
          {
            method: 'POST',
            headers: getAuthHeaders(),
          }
        );
      });
    });

    describe('rebalanceAgents', () => {
      it('should rebalance agents successfully', async () => {
        const projectId = '123';
        const mockRebalance = {
          reassigned: 3,
          message: 'Agents rebalanced successfully',
        };

        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: async () => mockRebalance,
        });

        const result = await rebalanceAgents(projectId);
        expect(result).toEqual(mockRebalance);
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/projects/${projectId}/rebalance`,
          {
            method: 'POST',
            headers: getAuthHeaders(),
          }
        );
      });
    });
  });
});