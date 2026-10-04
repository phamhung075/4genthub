import Cookies from 'js-cookie';
import {
  taskApiV2,
  projectApiV2,
  branchApiV2,
  isAuthenticated,
  getCurrentUserId
} from '../../services/apiV2';

// Mock js-cookie with default export for Vitest compatibility
vi.mock('js-cookie', () => {
  const mockCookies = {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn()
  };
  return {
    default: mockCookies,
    ...mockCookies
  };
});

// Mock fetch globally
global.fetch = vi.fn();

// Mock logger - apiV2 imports the default instance, so expose both default and named exports
vi.mock('../../utils/logger', () => {
  const mockLogger = {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    critical: vi.fn(),
  };
  return {
    default: mockLogger,
    ...mockLogger,
  };
});

// Mock request deduplication
vi.mock('../../utils/requestDeduplication', () => ({
  deduplicateRequest: vi.fn(
    (_url: string, _method: string, _body?: unknown, requestFn?: () => unknown) =>
      requestFn ? requestFn() : undefined
  ),
}));

describe('apiV2.ts', () => {
  const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsInVzZXJfaWQiOiJ1c2VyLTEyMyIsIm5hbWUiOiJUZXN0IFVzZXIiLCJpYXQiOjE1MTYyMzkwMjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
  const mockRefreshToken = 'refresh-token-123';

  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockReset();
    (Cookies.get as any).mockReset();
    (Cookies.set as any).mockReset();
    (Cookies.remove as any).mockReset();
    // Mock window.dispatchEvent
    window.dispatchEvent = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllEnvs();
  });

  describe('Token Refresh and Retry', () => {
    describe('401 handling on task requests', () => {
      it('should refresh token and update cookies', async () => {
        const newToken = 'new-access-token';
        const newRefreshToken = 'new-refresh-token';
        const mockTasks = [{ id: '1', title: 'Task 1' }];

        (Cookies.get as any).mockImplementation((key: string) =>
          key === 'access_token' ? mockToken : key === 'refresh_token' ? mockRefreshToken : undefined
        );

        (global.fetch as any)
          .mockResolvedValueOnce({
            ok: false,
            status: 401,
            json: vi.fn().mockResolvedValue({ detail: 'Token expired' })
          })
          .mockResolvedValueOnce({
            ok: true,
            json: vi.fn().mockResolvedValue({
              access_token: newToken,
              refresh_token: newRefreshToken
            })
          })
          .mockResolvedValueOnce({
            ok: true,
            json: vi.fn().mockResolvedValue(mockTasks)
          });

        const result = await taskApiV2.getTasks();

        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/auth/refresh',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: JSON.stringify({ refresh_token: mockRefreshToken }),
            credentials: 'include'
          }
        );

        expect(Cookies.set).toHaveBeenCalledWith('access_token', newToken, expect.any(Object));
        expect(Cookies.set).toHaveBeenCalledWith('refresh_token', newRefreshToken, expect.any(Object));
        expect(result).toEqual(mockTasks);
      });

      it('should handle refresh failure', async () => {
        (Cookies.get as any).mockImplementation((key: string) =>
          key === 'access_token' ? mockToken : key === 'refresh_token' ? mockRefreshToken : undefined
        );

        (global.fetch as any)
          .mockResolvedValueOnce({
            ok: false,
            status: 401,
            json: vi.fn().mockResolvedValue({ detail: 'Token expired' })
          })
          .mockResolvedValueOnce({
            ok: false,
            status: 401,
            json: vi.fn().mockResolvedValue({ detail: 'Invalid refresh token' })
          });

        await expect(taskApiV2.getTasks()).rejects.toThrow('Authentication required. Please log in again.');
        expect(Cookies.remove).toHaveBeenCalledWith('access_token');
        expect(Cookies.remove).toHaveBeenCalledWith('refresh_token');
      });
    });
  });

  describe('Authentication Helpers', () => {
    describe('isAuthenticated', () => {
      it('should return true when token exists', () => {
        (Cookies.get as any).mockReturnValue(mockToken);

        const result = isAuthenticated();

        expect(result).toBe(true);
        expect(Cookies.get).toHaveBeenCalledWith('access_token');
      });

      it('should return false when token does not exist', () => {
        (Cookies.get as any).mockReturnValue(null);

        const result = isAuthenticated();

        expect(result).toBe(false);
      });
    });

    describe('getCurrentUserId', () => {
      it('should extract user ID from JWT token', () => {
        (Cookies.get as any).mockReturnValue(mockToken);

        const userId = getCurrentUserId();

        expect(userId).toBe('user-123');
      });

      it('should return null when no token exists', () => {
        (Cookies.get as any).mockReturnValue(null);

        const userId = getCurrentUserId();

        expect(userId).toBeNull();
      });

      it('should return null for invalid token format', () => {
        (Cookies.get as any).mockReturnValue('invalid-token');

        const userId = getCurrentUserId();

        expect(userId).toBeNull();
      });

      it('should handle malformed JWT payload', () => {
        (Cookies.get as any).mockReturnValue('header.invalidbase64.signature');

        const userId = getCurrentUserId();

        expect(userId).toBeNull();
      });

      it('should use user_id field if sub is not present', () => {
        const tokenWithUserId = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidXNlci00NTYiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyfQ.vYD6h5b8_3olg6eKvLkYLpH6hR-WzG65P0-qGLKNc7M';
        (Cookies.get as any).mockReturnValue(tokenWithUserId);

        const userId = getCurrentUserId();

        expect(userId).toBe('user-456');
      });
    });
  });

  describe('Task API V2', () => {
    beforeEach(() => {
      (Cookies.get as any).mockReturnValue(mockToken);
    });

    describe('getTasks', () => {
      it('should fetch tasks with authentication', async () => {
        const mockTasks = [
          { id: '1', title: 'Task 1' },
          { id: '2', title: 'Task 2' }
        ];
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockTasks)
        });

        const result = await taskApiV2.getTasks();

        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v2/tasks/',
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${mockToken}`
            },
            credentials: 'include'
          }
        );
        expect(result).toEqual(mockTasks);
      });

      it('should fetch tasks with git_branch_id filter', async () => {
        const mockTasks = [{ id: '1', title: 'Branch Task' }];
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockTasks)
        });

        const result = await taskApiV2.getTasks({ git_branch_id: 'branch-123' });

        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v2/tasks/?git_branch_id=branch-123',
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${mockToken}`
            },
            credentials: 'include'
          }
        );
        expect(result).toEqual(mockTasks);
      });

      it('should handle 401 authentication error', async () => {
        (global.fetch as any).mockResolvedValue({
          ok: false,
          status: 401,
          json: vi.fn().mockResolvedValue({ detail: 'Token expired' })
        });

        await expect(taskApiV2.getTasks()).rejects.toThrow('Authentication required. Please log in again.');

        // The refresh flow uses the already-imported js-cookie client to clear tokens
        expect(Cookies.remove).toHaveBeenCalledWith('access_token');
        expect(Cookies.remove).toHaveBeenCalledWith('refresh_token');
      });

      it('should handle generic errors', async () => {
        (global.fetch as any).mockResolvedValue({
          ok: false,
          status: 500,
          json: vi.fn().mockResolvedValue({ detail: 'Server error' })
        });

        await expect(taskApiV2.getTasks()).rejects.toThrow('Server error');
      });

      it('should handle response without detail', async () => {
        (global.fetch as any).mockResolvedValue({
          ok: false,
          status: 400,
          json: vi.fn().mockRejectedValue(new Error('Parse error'))
        });

        // json() rejects, so the code falls back to the generic detail "Request failed"
        await expect(taskApiV2.getTasks()).rejects.toThrow('Request failed');
      });
    });

    describe('getTask', () => {
      const taskId = 'task-123';

      it('should fetch a specific task', async () => {
        const mockTask = { id: taskId, title: 'Test Task' };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockTask)
        });

        const result = await taskApiV2.getTask(taskId);

        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/api/v2/tasks/${taskId}`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${mockToken}`
            },
            credentials: 'include'
          }
        );
        expect(result).toEqual(mockTask);
      });
    });

    describe('createTask', () => {
      const taskData = {
        title: 'New Task',
        description: 'Task description',
        status: 'todo',
        priority: 'high',
        git_branch_id: 'branch-123'
      };

      it('should create a new task', async () => {
        const mockCreatedTask = { id: 'new-id', ...taskData };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockCreatedTask)
        });

        const result = await taskApiV2.createTask(taskData);

        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v2/tasks/',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${mockToken}`
            },
            body: JSON.stringify(taskData),
            credentials: 'include'
          }
        );
        expect(result).toEqual(mockCreatedTask);
      });

      it('should handle minimal task data', async () => {
        const minimalData = { title: 'Minimal Task' };
        const mockCreatedTask = { id: 'new-id', ...minimalData };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockCreatedTask)
        });

        const result = await taskApiV2.createTask(minimalData);

        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body).toEqual(minimalData);
        expect(result).toEqual(mockCreatedTask);
      });
    });

    describe('updateTask', () => {
      const taskId = 'task-123';
      const updates = {
        title: 'Updated Task',
        status: 'in_progress',
        progress_percentage: 50
      };

      it('should update a task', async () => {
        const mockUpdatedTask = { id: taskId, ...updates };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockUpdatedTask)
        });

        const result = await taskApiV2.updateTask(taskId, updates);

        // The code injects task_id into the request body
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/api/v2/tasks/${taskId}`,
          {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${mockToken}`
            },
            body: JSON.stringify({ task_id: taskId, ...updates }),
            credentials: 'include'
          }
        );
        expect(result).toEqual(mockUpdatedTask);
      });
    });

    describe('deleteTask', () => {
      const taskId = 'task-123';

      it('should delete a task', async () => {
        const mockResponse = { success: true };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockResponse)
        });

        const result = await taskApiV2.deleteTask(taskId);

        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/api/v2/tasks/${taskId}`,
          {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${mockToken}`
            },
            credentials: 'include'
          }
        );
        expect(result).toEqual(mockResponse);
      });
    });

    describe('completeTask', () => {
      const taskId = 'task-123';
      const completionData = {
        completion_summary: 'Task completed successfully',
        testing_notes: 'All tests passed'
      };

      it('should complete a task', async () => {
        const mockCompletedTask = {
          id: taskId,
          status: 'done',
          ...completionData
        };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockCompletedTask)
        });

        const result = await taskApiV2.completeTask(taskId, completionData);

        const fetchCall = (global.fetch as any).mock.calls[0];
        expect(fetchCall[0]).toBe(`http://localhost:8000/api/v2/tasks/${taskId}/complete`);
        expect(fetchCall[1].method).toBe('POST');
        expect(fetchCall[1].headers).toEqual({
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${mockToken}`
        });
        expect(fetchCall[1].credentials).toBe('include');
        const body = fetchCall[1].body as URLSearchParams;
        expect(body).toBeInstanceOf(URLSearchParams);
        expect(body.get('completion_summary')).toBe('Task completed successfully');
        expect(body.get('testing_notes')).toBe('All tests passed');
        expect(result).toEqual(mockCompletedTask);
      });

      it('should handle completion without testing notes', async () => {
        const minimalData = { completion_summary: 'Done' };
        const mockResponse = { id: taskId, status: 'done' };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockResponse)
        });

        const result = await taskApiV2.completeTask(taskId, minimalData);

        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = fetchCall[1].body as URLSearchParams;
        expect(body.get('completion_summary')).toBe('Done');
        expect(body.has('testing_notes')).toBe(false);
        expect(result).toEqual(mockResponse);
      });
    });

    describe('deleteTask with 204 No Content', () => {
      const taskId = 'task-456';

      it('should handle 204 No Content response', async () => {
        (global.fetch as any).mockResolvedValue({
          ok: true,
          status: 204,
          json: vi.fn().mockRejectedValue(new Error('No content'))
        });

        const result = await taskApiV2.deleteTask(taskId);

        expect(result).toEqual({
          success: true,
          message: 'Operation completed successfully'
        });
      });
    });
  });

  describe('Project API V2', () => {
    beforeEach(() => {
      (Cookies.get as any).mockReturnValue(mockToken);
    });

    describe('getProjects', () => {
      it('should fetch projects with authentication', async () => {
        const mockProjects = [
          { id: '1', name: 'Project 1' },
          { id: '2', name: 'Project 2' }
        ];
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockProjects)
        });

        const result = await projectApiV2.getProjects();

        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v2/projects/',
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${mockToken}`
            },
            credentials: 'include'
          }
        );
        expect(result).toEqual(mockProjects);
      });
    });

    describe('createProject', () => {
      const projectData = {
        name: 'New Project',
        description: 'Project description'
      };

      it('should create a new project', async () => {
        const mockCreatedProject = { id: 'proj-123', ...projectData };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue(mockCreatedProject)
        });

        const result = await projectApiV2.createProject(projectData);

        // createProject sends URL-encoded form data, not JSON
        const fetchCall = (global.fetch as any).mock.calls[0];
        expect(fetchCall[0]).toBe('http://localhost:8000/api/v2/projects/');
        expect(fetchCall[1].method).toBe('POST');
        expect(fetchCall[1].headers).toEqual({
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${mockToken}`
        });
        expect(fetchCall[1].credentials).toBe('include');
        const body = fetchCall[1].body as URLSearchParams;
        expect(body).toBeInstanceOf(URLSearchParams);
        expect(body.get('name')).toBe('New Project');
        expect(body.get('description')).toBe('Project description');
        expect(result).toEqual(mockCreatedProject);
      });
    });

    describe('updateProject', () => {
      const projectId = 'proj-123';
      const updates = {
        name: 'Updated Project',
        description: 'Updated description',
        status: 'active'
      };

      it('should update a project', async () => {
        const mockUpdatedProject = { id: projectId, ...updates };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          status: 200,
          url: `http://localhost:8000/api/v2/projects/${projectId}`,
          json: vi.fn().mockResolvedValue(mockUpdatedProject)
        });

        const result = await projectApiV2.updateProject(projectId, updates);

        // updateProject sends URL-encoded form data and only forwards name/description
        const fetchCall = (global.fetch as any).mock.calls[0];
        expect(fetchCall[0]).toBe(`http://localhost:8000/api/v2/projects/${projectId}`);
        expect(fetchCall[1].method).toBe('PUT');
        expect(fetchCall[1].headers).toEqual({
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${mockToken}`
        });
        expect(fetchCall[1].credentials).toBe('include');
        const body = new URLSearchParams(fetchCall[1].body as string);
        expect(body.get('name')).toBe('Updated Project');
        expect(body.get('description')).toBe('Updated description');
        expect(body.has('status')).toBe(false);
        expect(result).toEqual(mockUpdatedProject);
      });
    });

    describe('deleteProject', () => {
      const projectId = 'proj-123';

      it('should delete a project', async () => {
        const mockResponse = { success: true };
        (global.fetch as any).mockResolvedValue({
          ok: true,
          status: 200,
          url: `http://localhost:8000/api/v2/projects/${projectId}`,
          json: vi.fn().mockResolvedValue(mockResponse)
        });

        const result = await projectApiV2.deleteProject(projectId);

        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/api/v2/projects/${projectId}`,
          {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${mockToken}`
            },
            credentials: 'include'
          }
        );
        expect(result).toEqual(mockResponse);
      });
    });
  });

  describe('Branch API V2', () => {
    describe('createBranch', () => {
      it('posts to the trailing-slash collection route', async () => {
        vi.mocked(global.fetch).mockResolvedValue(
          new Response(JSON.stringify({ id: 'branch-1' }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );

        await branchApiV2.createBranch('proj-1', { git_branch_name: 'feat/trailing-slash' });

        const [url, init] = vi.mocked(global.fetch).mock.calls[0];
        // The Go server mounts POST /api/v2/branches/. Dropping the trailing slash
        // makes ServeMux answer 301 and fetch downgrades the POST to a GET, so the
        // create silently becomes a list-branches call.
        expect(url).toBe('http://localhost:8000/api/v2/branches/');
        expect(init?.method).toBe('POST');
        expect(String(init?.body)).toContain('project_id=proj-1');
        expect(String(init?.body)).toContain('git_branch_name=feat%2Ftrailing-slash');
      });
    });
  });

  describe('Error Handling', () => {
    beforeEach(() => {
      (Cookies.get as any).mockReturnValue(mockToken);
    });

    it('should handle network errors', async () => {
      (global.fetch as any).mockRejectedValue(new Error('Network error'));

      await expect(taskApiV2.getTasks()).rejects.toThrow('Network error');
    });

    it('should handle JSON parsing errors in response', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockRejectedValue(new Error('Invalid JSON'))
      });

      await expect(taskApiV2.getTasks()).rejects.toThrow('Invalid JSON');
    });

    it('should handle missing authorization header when no token', async () => {
      (Cookies.get as any).mockReturnValue(null);

      const mockResponse = { tasks: [] };
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse)
      });

      await taskApiV2.getTasks();

      const fetchCall = (global.fetch as any).mock.calls[0];
      expect(fetchCall[1].headers).toEqual({
        'Content-Type': 'application/json'
      });
      expect(fetchCall[1].headers['Authorization']).toBeUndefined();
    });
  });

  describe('Environment Configuration', () => {
    it('should use default API URL when env variable not set', async () => {
      // Clear the build-time API URL so environment.ts falls back to its default
      vi.stubEnv('VITE_API_URL', '');

      // Re-import the module so environment.ts is re-evaluated
      vi.resetModules();
      const { taskApiV2: freshTaskApiV2 } = await import('../../services/apiV2');

      (Cookies.get as any).mockReturnValue(mockToken);
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue([])
      });

      await freshTaskApiV2.getTasks();

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v2/tasks/',
        expect.any(Object)
      );

      vi.unstubAllEnvs();
    });
  });
});
