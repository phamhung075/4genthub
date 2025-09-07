import * as api from '../api';
import * as apiV2 from '../services/apiV2';
import Cookies from 'js-cookie';
import { mcpTokenService } from '../services/mcpTokenService';

// Mock services/mcpTokenService
jest.mock('../services/mcpTokenService', () => ({
  mcpTokenService: {
    getMCPToken: jest.fn()
  }
}));

// Mock services/apiV2
jest.mock('../services/apiV2', () => ({
  taskApiV2: {
    getTasks: jest.fn(),
    createTask: jest.fn(),
    updateTask: jest.fn(),
    deleteTask: jest.fn(),
    completeTask: jest.fn()
  },
  projectApiV2: {
    getProjects: jest.fn(),
    createProject: jest.fn(),
    updateProject: jest.fn(),
    deleteProject: jest.fn()
  },
  agentApiV2: {
    getAgents: jest.fn(),
    createAgent: jest.fn(),
    updateAgent: jest.fn(),
    deleteAgent: jest.fn()
  },
  isAuthenticated: jest.fn()
}));

// Mock js-cookie
jest.mock('js-cookie', () => ({
  get: jest.fn(),
  set: jest.fn(),
  remove: jest.fn()
}));

// Mock fetch globally
global.fetch = jest.fn();

describe('api.ts', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as any).mockReset();
    (apiV2.isAuthenticated as any).mockReturnValue(false);
    (mcpTokenService.getMCPToken as any).mockRejectedValue(new Error('No token'));
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Task Management', () => {
    describe('listTasks', () => {
      it('should use V2 API when authenticated', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        const mockTasks = [
          { id: '1', title: 'Task 1', status: 'todo' },
          { id: '2', title: 'Task 2', status: 'done' }
        ];
        (apiV2.taskApiV2.getTasks as any).mockResolvedValue(mockTasks);

        const result = await api.listTasks();

        expect(apiV2.taskApiV2.getTasks).toHaveBeenCalled();
        expect(result).toEqual(mockTasks);
        expect(global.fetch).not.toHaveBeenCalled();
      });

      it('should fall back to V1 API when V2 fails', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        (apiV2.taskApiV2.getTasks as any).mockRejectedValue(new Error('V2 API error'));
        
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  tasks: [
                    { id: '1', title: 'Task 1', status: 'todo' }
                  ]
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listTasks();

        expect(apiV2.taskApiV2.getTasks).toHaveBeenCalled();
        expect(global.fetch).toHaveBeenCalled();
        expect(result).toHaveLength(1);
        expect(result[0].id).toBe('1');
      });

      it('should use V1 API when not authenticated', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(false);
        
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  tasks: [
                    { id: '1', title: 'Task 1', status: 'todo' }
                  ]
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listTasks();

        expect(apiV2.taskApiV2.getTasks).not.toHaveBeenCalled();
        const fetchCall = (global.fetch as any).mock.calls[0];
        expect(fetchCall[0]).toBe('http://localhost:8000/mcp/');
        expect(fetchCall[1].method).toBe('POST');
        // Headers are a promise now due to async withMcpHeaders
        expect(result).toHaveLength(1);
      });

      it('should handle empty response', async () => {
        const mockResponse = {
          result: {
            content: []
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listTasks();

        expect(result).toEqual([]);
      });

      it('should sanitize task data', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  tasks: [{
                    id: '1',
                    title: 'Task 1',
                    _events: 'should be removed',
                    _eventsCount: 42,
                    _maxListeners: 10,
                    assignees: ['user1', { id: 'user2' }, { name: 'user3' }],
                    subtasks: ['sub1', { id: 'sub2' }, { value: 'sub3' }]
                  }]
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listTasks();

        expect(result).toHaveLength(1);
        const task = result[0];
        expect(task._events).toBeUndefined();
        expect(task._eventsCount).toBeUndefined();
        expect(task._maxListeners).toBeUndefined();
        expect(task.assignees).toEqual(['user1', 'user2', 'user3']);
        expect(task.subtasks).toEqual(['sub1', 'sub2', 'sub3']);
      });
    });

    describe('createTask', () => {
      const newTask = {
        title: 'New Task',
        description: 'Task description',
        status: 'todo',
        priority: 'high'
      };

      it('should use V2 API when authenticated', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        const mockCreatedTask = { id: '123', ...newTask };
        (apiV2.taskApiV2.createTask as any).mockResolvedValue(mockCreatedTask);

        const result = await api.createTask(newTask);

        expect(apiV2.taskApiV2.createTask).toHaveBeenCalledWith({
          title: newTask.title,
          description: newTask.description,
          status: newTask.status,
          priority: newTask.priority,
          git_branch_id: undefined
        });
        expect(result).toEqual(mockCreatedTask);
      });

      it('should fall back to V1 API when V2 fails', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        (apiV2.taskApiV2.createTask as any).mockRejectedValue(new Error('V2 API error'));
        
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  task: { id: '123', ...newTask }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.createTask(newTask);

        expect(apiV2.taskApiV2.createTask).toHaveBeenCalled();
        expect(global.fetch).toHaveBeenCalled();
        expect(result).toMatchObject(newTask);
        expect(result?.id).toBe('123');
      });
    });

    describe('updateTask', () => {
      const taskId = '123';
      const updates = {
        title: 'Updated Task',
        status: 'in_progress'
      };

      it('should use V2 API when authenticated', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        const mockUpdatedTask = { id: taskId, ...updates };
        (apiV2.taskApiV2.updateTask as any).mockResolvedValue(mockUpdatedTask);

        const result = await api.updateTask(taskId, updates);

        expect(apiV2.taskApiV2.updateTask).toHaveBeenCalledWith(taskId, {
          title: updates.title,
          description: undefined,
          status: updates.status,
          priority: undefined,
          progress_percentage: undefined
        });
        expect(result).toEqual(mockUpdatedTask);
      });

      it('should handle error response', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false,
                error: 'Task not found'
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await expect(api.updateTask(taskId, updates)).rejects.toThrow('Task not found');
      });

      it('should handle success without task data', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.updateTask(taskId, updates);

        expect(result).toMatchObject({ id: taskId, ...updates });
      });
    });

    describe('deleteTask', () => {
      const taskId = '123';

      it('should use V2 API when authenticated', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        (apiV2.taskApiV2.deleteTask as any).mockResolvedValue(undefined);

        const result = await api.deleteTask(taskId);

        expect(apiV2.taskApiV2.deleteTask).toHaveBeenCalledWith(taskId);
        expect(result).toBe(true);
      });

      it('should return true on successful deletion', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.deleteTask(taskId);

        expect(result).toBe(true);
      });

      it('should return false on failed deletion', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.deleteTask(taskId);

        expect(result).toBe(false);
      });
    });

    describe('completeTask', () => {
      const taskId = '123';
      const completionSummary = 'Task completed successfully';
      const testingNotes = 'All tests passed';

      it('should use V2 API when authenticated', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        const mockCompletedTask = { 
          id: taskId, 
          status: 'done',
          completion_summary: completionSummary
        };
        (apiV2.taskApiV2.completeTask as any).mockResolvedValue(mockCompletedTask);

        const result = await api.completeTask(taskId, completionSummary, testingNotes);

        expect(apiV2.taskApiV2.completeTask).toHaveBeenCalledWith(taskId, {
          completion_summary: completionSummary,
          testing_notes: testingNotes
        });
        expect(result).toEqual(mockCompletedTask);
      });

      it('should handle completion without testing notes', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  task: { id: taskId, status: 'done' }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.completeTask(taskId, completionSummary);

        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'complete',
          task_id: taskId,
          completion_summary: completionSummary
        });
        expect(body.params.arguments.testing_notes).toBeUndefined();
        expect(result?.status).toBe('done');
      });
    });

    describe('searchTasks', () => {
      it('should search tasks with query', async () => {
        const query = 'test query';
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  tasks: [
                    { id: '1', title: 'Test Task 1' },
                    { id: '2', title: 'Test Task 2' }
                  ]
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.searchTasks(query);

        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'search',
          query: query,
          limit: 50
        });
        expect(result).toHaveLength(2);
      });

      it('should search with git_branch_id and custom limit', async () => {
        const query = 'test';
        const branchId = 'branch-123';
        const limit = 10;
        
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: { tasks: [] }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await api.searchTasks(query, branchId, limit);

        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'search',
          query: query,
          git_branch_id: branchId,
          limit: limit
        });
      });
    });
  });

  describe('Subtask Management', () => {
    describe('listSubtasks', () => {
      const taskId = 'task-123';

      it('should list subtasks for a task', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  subtasks: [
                    { id: 'sub1', title: 'Subtask 1' },
                    { id: 'sub2', title: 'Subtask 2' }
                  ]
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listSubtasks(taskId);

        expect(result).toHaveLength(2);
        expect(result[0].id).toBe('sub1');
        expect(result[1].id).toBe('sub2');
      });

      it('should handle subtask data with value property', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  subtasks: [
                    { id: 'sub1', title: { value: 'Subtask 1' }, priority: { value: 'high' } },
                    { id: 'sub2', title: 'Subtask 2', status: { value: 'in_progress' } }
                  ]
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listSubtasks(taskId);

        expect(result).toHaveLength(2);
        expect(result[0].title).toBe('Subtask 1');
        expect(result[0].priority).toBe('high');
        expect(result[1].status).toBe('in_progress');
      });

      it('should sanitize subtask data', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  subtasks: [{
                    id: 'sub1',
                    title: 'Subtask 1',
                    _events: 'should be removed',
                    _eventsCount: 10,
                    _maxListeners: 5,
                    assignees: ['user1', { value: 'user2' }, null, '[', ']'],
                    progress_percentage: { value: 75 }
                  }]
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listSubtasks(taskId);

        expect(result).toHaveLength(1);
        const subtask = result[0];
        expect(subtask._events).toBeUndefined();
        expect(subtask._eventsCount).toBeUndefined();
        expect(subtask._maxListeners).toBeUndefined();
        expect(subtask.assignees).toEqual(['user1', 'user2']);
        expect(subtask.progress_percentage).toBe(75);
      });
    });

    describe('updateSubtask', () => {
      const taskId = 'task-123';
      const subtaskId = 'sub-456';
      const updates = { title: 'Updated Subtask', status: 'done' };

      it('should update subtask successfully', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  subtask: {
                    id: subtaskId,
                    ...updates
                  }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.updateSubtask(taskId, subtaskId, updates);

        expect(result).toMatchObject({ id: subtaskId, ...updates });
      });

      it('should handle nested subtask structure', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  subtask: {
                    subtask: {
                      id: subtaskId,
                      ...updates
                    }
                  }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.updateSubtask(taskId, subtaskId, updates);

        expect(result).toMatchObject({ id: subtaskId, ...updates });
      });

      it('should extract and sanitize values from object properties', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  subtask: {
                    id: subtaskId,
                    title: { value: 'Updated Title' },
                    status: { value: 'done' },
                    assignees: [{ value: 'user1' }, 'user2', { assignee_id: 'user3' }]
                  }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.updateSubtask(taskId, subtaskId, updates);

        expect(result).toMatchObject({ 
          id: subtaskId, 
          title: 'Updated Title',
          status: 'done',
          assignees: ['user1', 'user2', 'user3']
        });
      });

      it('should handle error response', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false,
                error: { message: 'Subtask not found' }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await expect(api.updateSubtask(taskId, subtaskId, updates))
          .rejects.toThrow('Subtask not found');
      });
    });

    describe('completeSubtask', () => {
      const taskId = 'task-123';
      const subtaskId = 'sub-456';
      const completionSummary = 'Subtask completed';
      const impactOnParent = 'Task is now 50% complete';
      const challengesOvercome = ['Challenge 1', 'Challenge 2'];

      it('should complete subtask with all parameters', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  subtask: {
                    id: subtaskId,
                    status: 'done'
                  }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.completeSubtask(
          taskId,
          subtaskId,
          completionSummary,
          impactOnParent,
          challengesOvercome
        );

        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'complete',
          task_id: taskId,
          subtask_id: subtaskId,
          completion_summary: completionSummary,
          impact_on_parent: impactOnParent,
          challenges_overcome: challengesOvercome
        });
        expect(result).toMatchObject({ id: subtaskId, status: 'done' });
      });

      it('should complete subtask with minimal parameters', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.completeSubtask(taskId, subtaskId, completionSummary);

        expect(result).toMatchObject({ id: subtaskId, status: 'done' });
      });
    });
  });

  describe('Dependency Management', () => {
    const taskId = 'task-123';
    const dependencyId = 'dep-456';

    describe('addDependency', () => {
      it('should add dependency successfully', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({ success: true })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.addDependency(taskId, dependencyId);

        expect(result).toBe(true);
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'add_dependency',
          task_id: taskId,
          dependency_id: dependencyId
        });
      });
    });

    describe('removeDependency', () => {
      it('should remove dependency successfully', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({ success: true })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.removeDependency(taskId, dependencyId);

        expect(result).toBe(true);
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'remove_dependency',
          task_id: taskId,
          dependency_id: dependencyId
        });
      });
    });
  });

  describe('MCP Token Service Integration', () => {
    it('should use MCP token when available', async () => {
      (mcpTokenService.getMCPToken as any).mockResolvedValue('mcp-test-token');
      
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: { tasks: [] }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      await api.listTasks();

      expect(mcpTokenService.getMCPToken).toHaveBeenCalled();
    });

    it('should fallback to JWT token when MCP token fails', async () => {
      (mcpTokenService.getMCPToken as any).mockRejectedValue(new Error('MCP token error'));
      (Cookies.get as any).mockReturnValue('jwt-test-token');
      
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: { tasks: [] }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      await api.listTasks();

      expect(mcpTokenService.getMCPToken).toHaveBeenCalled();
      expect(Cookies.get).toHaveBeenCalledWith('access_token');
    });
  });

  describe('Context Management', () => {
    describe('getGlobalContext', () => {
      it('should get global context with user-specific ID', async () => {
        const mockContext = {
          id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          level: 'global',
          data: { global_settings: {} }
        };
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify(mockContext)
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.getGlobalContext();

        expect(result).toEqual(mockContext);
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'resolve',
          level: 'global',
          context_id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          force_refresh: false,
          include_inherited: false
        });
      });
    });

    describe('getTaskContext', () => {
      const taskId = 'task-123';

      it('should get task context with inheritance', async () => {
        const mockContext = {
          id: taskId,
          level: 'task',
          data: { some: 'data' },
          inherited: { project: 'context' }
        };
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify(mockContext)
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.getTaskContext(taskId);

        expect(result).toEqual(mockContext);
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'resolve',
          level: 'task',
          context_id: taskId,
          force_refresh: false,
          include_inherited: true
        });
      });

      it('should handle context not found', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false,
                error: { message: 'Context not found' }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.getTaskContext(taskId);

        expect(result).toBeNull();
      });
    });

    describe('addTaskInsight', () => {
      const taskId = 'task-123';
      const content = 'Important insight';
      const category = 'performance';
      const importance = 'high';

      it('should add task insight', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({ success: true, insight_id: 'insight-123' })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.addTaskInsight(taskId, content, category, importance);

        expect(result).toMatchObject({ success: true });
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'add_insight',
          level: 'task',
          context_id: taskId,
          content: content,
          category: category,
          importance: importance
        });
      });

      it('should use default values for category and importance', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({ success: true })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await api.addTaskInsight(taskId, content);

        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments.category).toBe('general');
        expect(body.params.arguments.importance).toBe('medium');
      });
    });

    describe('addTaskProgress', () => {
      const taskId = 'task-123';
      const content = 'Made significant progress';

      it('should add task progress', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({ success: true })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.addTaskProgress(taskId, content);

        expect(result).toMatchObject({ success: true });
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'add_progress',
          level: 'task',
          context_id: taskId,
          content: content
        });
      });
    });

    describe('updateGlobalContext', () => {
      const contextData = {
        organizationSettings: { theme: 'dark' },
        globalPatterns: { auth_pattern: 'jwt' },
        metadata: { version: '1.0' }
      };

      it('should update global context', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({ success: true, context_id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5' })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.updateGlobalContext(contextData);

        expect(result).toMatchObject({ success: true });
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'update',
          level: 'global',
          context_id: '7fa54328-bfb4-523c-ab6f-465e05e1bba5',
          data: {
            global_settings: {
              autonomous_rules: contextData.organizationSettings || {},
              security_policies: {},
              coding_standards: {},
              workflow_templates: contextData.globalPatterns || {},
              delegation_rules: contextData.metadata || {}
            }
          },
          propagate_changes: true
        });
      });

      it('should throw error on failure', async () => {
        const mockResponse = {
          result: {
            content: []
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await expect(api.updateGlobalContext(contextData))
          .rejects.toThrow('Failed to update global context');
      });
    });
  });

  describe('Project Management', () => {
    describe('listProjects', () => {
      it('should use V2 API when authenticated', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        const mockProjects = [
          { id: '1', name: 'Project 1', git_branchs: {} },
          { id: '2', name: 'Project 2', git_branchs: {} }
        ];
        (apiV2.projectApiV2.getProjects as any).mockResolvedValue(mockProjects);

        const result = await api.listProjects();

        expect(apiV2.projectApiV2.getProjects).toHaveBeenCalled();
        expect(result).toEqual(mockProjects);
      });

      it('should handle projects with git branches', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  projects: [{
                    id: 'proj1',
                    name: 'Project 1',
                    git_branchs: {
                      'branch1': { id: 'branch1', name: 'main' },
                      'branch2': { id: 'branch2', name: 'feature' }
                    }
                  }]
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listProjects();

        expect(result).toHaveLength(1);
        expect(result[0].git_branchs).toHaveProperty('branch1');
        expect(result[0].git_branchs).toHaveProperty('branch2');
      });
    });

    describe('createProject', () => {
      const newProject = {
        name: 'New Project',
        description: 'A new test project'
      };

      it('should create project successfully', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  project: { id: 'proj-123', ...newProject, git_branchs: {} }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.createProject(newProject);

        expect(result).toMatchObject(newProject);
        expect(result?.id).toBe('proj-123');
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'create',
          ...newProject
        });
      });

      it('should return null on failure', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false,
                error: 'Project name already exists'
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.createProject(newProject);

        expect(result).toBeNull();
      });
    });

    describe('updateProject', () => {
      const projectId = 'proj-123';
      const updates = {
        name: 'Updated Project Name',
        description: 'Updated description'
      };

      it('should update project successfully', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  project: { id: projectId, ...updates }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.updateProject(projectId, updates);

        expect(result).toMatchObject({ id: projectId, ...updates });
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'update',
          project_id: projectId,
          ...updates
        });
      });
    });

    describe('deleteProject', () => {
      const projectId = 'proj-123';

      it('should delete project successfully', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                message: 'Project deleted'
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.deleteProject(projectId);

        expect(result).toEqual({
          success: true,
          message: 'Project deleted',
          error: undefined
        });
      });

      it('should handle deletion failure', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false,
                error: 'Project has active tasks'
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.deleteProject(projectId);

        expect(result).toEqual({
          success: false,
          message: undefined,
          error: 'Project has active tasks'
        });
      });

      it('should handle parse error', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: 'invalid json'
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.deleteProject(projectId);

        expect(result).toEqual({
          success: false,
          error: 'Failed to parse response'
        });
      });
    });
  });

  describe('Branch Management', () => {
    const projectId = 'proj-123';
    const branchName = 'feature-auth';
    const description = 'Authentication feature branch';

    describe('listGitBranches', () => {
      it('should list branches for a project', async () => {
        const mockBranches = [
          { id: 'branch-1', name: 'main', description: 'Main branch' },
          { id: 'branch-2', name: 'feature', description: 'Feature branch' }
        ];
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  git_branchs: mockBranches
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listGitBranches(projectId);

        expect(result).toEqual(mockBranches);
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'list',
          project_id: projectId
        });
      });

      it('should return empty array on failure', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listGitBranches(projectId);

        expect(result).toEqual([]);
      });
    });

    describe('createBranch', () => {
      it('should create branch with git-friendly name', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  git_branch: {
                    id: 'branch-123',
                    name: 'feature-auth',
                    description: description
                  }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.createBranch(projectId, 'Feature Auth', description);

        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments.git_branch_name).toBe('feature-auth');
        expect(result).toMatchObject({
          id: 'branch-123',
          name: 'feature-auth'
        });
      });
    });

    describe('deleteBranch', () => {
      const branchId = 'branch-123';

      it('should delete branch successfully', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({ success: true })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.deleteBranch(projectId, branchId);

        expect(result).toBe(true);
      });

      it('should handle deletion failure', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({ success: false })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.deleteBranch(projectId, branchId);

        expect(result).toBe(false);
      });

      it('should handle network error', async () => {
        (global.fetch as any).mockRejectedValue(new Error('Network error'));

        const result = await api.deleteBranch(projectId, branchId);

        expect(result).toBe(false);
      });
    });
  });

  describe('Agent Management', () => {
    const projectId = 'proj-123';

    describe('listAgents', () => {
      it('should list agents for a project', async () => {
        const mockAgents = [
          { id: 'agent-1', name: '@coding_agent', project_id: projectId },
          { id: 'agent-2', name: '@test_agent', project_id: projectId }
        ];
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                agents: mockAgents
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listAgents(projectId);

        expect(result).toEqual(mockAgents);
        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments).toMatchObject({
          action: 'list',
          project_id: projectId
        });
      });

      it('should return empty array on error', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: 'invalid json'
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listAgents(projectId);

        expect(result).toEqual([]);
      });
    });

    describe('callAgent', () => {
      const agentName = '@test_orchestrator_agent';

      it('should call agent successfully', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                agent_info: { name: agentName }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.callAgent(agentName);

        expect(result).toMatchObject({
          success: true,
          agent_info: { name: agentName }
        });
      });

      it('should handle parse error', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: 'invalid json'
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.callAgent(agentName);

        expect(result).toEqual({
          success: false,
          error: 'Failed to parse response'
        });
      });

      it('should handle no response', async () => {
        const mockResponse = {
          result: {
            content: []
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.callAgent(agentName);

        expect(result).toEqual({
          success: false,
          error: 'No response from server'
        });
      });
    });

    describe('getAvailableAgents', () => {
      it('should return list of available agents', async () => {
        const agents = await api.getAvailableAgents();

        expect(agents).toBeInstanceOf(Array);
        expect(agents.length).toBeGreaterThan(0);
        expect(agents).toContain('@test_orchestrator_agent');
        expect(agents).toContain('@coding_agent');
        expect(agents).toContain('@debugger_agent');
      });
    });
  });

  describe('Rule Management', () => {
    describe('listRules', () => {
      it('should list rules successfully', async () => {
        const mockRules = [
          { id: 'rule1', name: 'Rule 1', type: 'validation' },
          { id: 'rule2', name: 'Rule 2', type: 'security' }
        ];
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                rules: mockRules
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listRules();

        expect(result).toEqual(mockRules);
      });

      it('should return empty array on failure', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.listRules();

        expect(result).toEqual([]);
      });
    });

    describe('validateRule', () => {
      const ruleId = 'rule-123';

      it('should validate rule successfully', async () => {
        const mockValidation = {
          success: true,
          valid: true,
          issues: []
        };
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify(mockValidation)
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.validateRule(ruleId);

        expect(result).toEqual(mockValidation);
      });

      it('should return null on failure', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false,
                error: 'Rule not found'
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.validateRule(ruleId);

        expect(result).toBeNull();
      });
    });
  });

  describe('Helper Functions', () => {
    describe('getTaskCount', () => {
      const branchId = 'branch-123';

      it('should return task count for branch', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  tasks: [
                    { id: '1', git_branch_id: branchId },
                    { id: '2', git_branch_id: branchId },
                    { id: '3', git_branch_id: branchId }
                  ]
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const count = await api.getTaskCount(branchId);

        expect(count).toBe(3);
      });

      it('should return 0 for empty branch', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: { tasks: [] }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const count = await api.getTaskCount(branchId);

        expect(count).toBe(0);
      });
    });
  });

  describe('V2 API Integration', () => {
    describe('listTasks with V2 API response format', () => {
      it('should handle V2 response with tasks array directly', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        const mockTasks = [
          { id: '1', title: 'Task 1', status: 'todo' },
          { id: '2', title: 'Task 2', status: 'done' }
        ];
        (apiV2.taskApiV2.getTasks as any).mockResolvedValue(mockTasks);

        const result = await api.listTasks();

        expect(result).toEqual(mockTasks);
      });

      it('should handle V2 response with nested tasks structure', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        const mockTasks = [
          { id: '1', title: 'Task 1', status: 'todo' },
          { id: '2', title: 'Task 2', status: 'done' }
        ];
        (apiV2.taskApiV2.getTasks as any).mockResolvedValue({ tasks: mockTasks });

        const result = await api.listTasks();

        expect(result).toEqual(mockTasks);
      });
    });

    describe('listProjects with V2 API response format', () => {
      it('should handle V2 response with projects wrapper', async () => {
        (apiV2.isAuthenticated as any).mockReturnValue(true);
        const mockProjects = [
          { id: '1', name: 'Project 1', git_branchs: {} },
          { id: '2', name: 'Project 2', git_branchs: {} }
        ];
        (apiV2.projectApiV2.getProjects as any).mockResolvedValue({ projects: mockProjects });

        const result = await api.listProjects();

        expect(result).toEqual(mockProjects);
      });
    });
  });

  describe('Error Handling Edge Cases', () => {
    describe('updateTask error handling', () => {
      it('should handle error object with message property', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false,
                error: { message: 'Detailed error message' }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await expect(api.updateTask('123', { title: 'Test' }))
          .rejects.toThrow('Detailed error message');
      });

      it('should handle error object without message', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false,
                error: { code: 'ERROR_CODE' }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await expect(api.updateTask('123', { title: 'Test' }))
          .rejects.toThrow('{"code":"ERROR_CODE"}');
      });

      it('should handle response with error property in data', async () => {
        const mockResponse = {
          error: {
            message: 'RPC error'
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await expect(api.updateTask('123', { title: 'Test' }))
          .rejects.toThrow('RPC error');
      });
    });

    describe('updateSubtask error handling', () => {
      it('should handle string error', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false,
                error: 'Simple error message'
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await expect(api.updateSubtask('task-123', 'sub-123', { title: 'Test' }))
          .rejects.toThrow('Simple error message');
      });

      it('should handle non-Error exceptions', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: false
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await expect(api.updateSubtask('task-123', 'sub-123', { title: 'Test' }))
          .rejects.toThrow('Unexpected response from server');
      });
    });
  });

  describe('Assignee Handling', () => {
    it('should handle assignees as objects with assignee_id', async () => {
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: {
                tasks: [{
                  id: '1',
                  title: 'Task 1',
                  assignees: [
                    { assignee_id: 'user1' },
                    { assignee_id: 'user2' }
                  ]
                }]
              }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await api.listTasks();

      expect(result).toHaveLength(1);
      expect(result[0].assignees).toEqual(['user1', 'user2']);
    });

    it('should handle assignees as JSON string', async () => {
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: {
                tasks: [{
                  id: '1',
                  title: 'Task 1',
                  assignees: '["user1", "user2"]'
                }]
              }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await api.listTasks();

      expect(result).toHaveLength(1);
      expect(result[0].assignees).toEqual(['user1', 'user2']);
    });

    it('should handle assignees as single string', async () => {
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: {
                tasks: [{
                  id: '1',
                  title: 'Task 1',
                  assignees: 'single-user'
                }]
              }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await api.listTasks();

      expect(result).toHaveLength(1);
      expect(result[0].assignees).toEqual(['single-user']);
    });

    it('should filter out invalid assignee entries', async () => {
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: {
                tasks: [{
                  id: '1',
                  title: 'Task 1',
                  assignees: ['user1', null, '[', ']', '', { id: 'user2' }, { invalid: 'object' }]
                }]
              }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await api.listTasks();

      expect(result).toHaveLength(1);
      expect(result[0].assignees).toEqual(['user1', 'user2']);
    });

    it('should handle empty or invalid assignees', async () => {
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: {
                tasks: [{
                  id: '1',
                  title: 'Task 1',
                  assignees: {}
                }]
              }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await api.listTasks();

      expect(result).toHaveLength(1);
      expect(result[0].assignees).toEqual([]);
    });
  });

  describe('Subtask ID handling', () => {
    it('should handle subtasks with value property', async () => {
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: {
                tasks: [{
                  id: '1',
                  title: 'Task 1',
                  subtasks: [
                    { value: 'subtask-uuid-1' },
                    { value: 'subtask-uuid-2' }
                  ]
                }]
              }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await api.listTasks();

      expect(result).toHaveLength(1);
      expect(result[0].subtasks).toEqual(['subtask-uuid-1', 'subtask-uuid-2']);
    });

    it('should filter out null subtask values', async () => {
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: {
                tasks: [{
                  id: '1',
                  title: 'Task 1',
                  subtasks: ['sub1', null, { id: 'sub2' }, { value: 'sub3' }, { invalid: 'object' }]
                }]
              }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await api.listTasks();

      expect(result).toHaveLength(1);
      expect(result[0].subtasks).toEqual(['sub1', 'sub2', 'sub3']);
    });
  });

  describe('Branch Management Edge Cases', () => {
    describe('createBranch', () => {
      it('should handle branch name with spaces and special characters', async () => {
        const projectId = 'proj-123';
        const branchName = 'Feature Branch With Spaces!';
        const expectedName = 'feature-branch-with-spaces!';
        
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                data: {
                  git_branch: {
                    id: 'branch-123',
                    name: expectedName,
                    description: 'Test'
                  }
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        await api.createBranch(projectId, branchName, 'Test');

        const fetchCall = (global.fetch as any).mock.calls[0];
        const body = JSON.parse(fetchCall[1].body);
        expect(body.params.arguments.git_branch_name).toBe(expectedName);
      });

      it('should handle response with git_branch in root', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: JSON.stringify({
                success: true,
                git_branch: {
                  id: 'branch-123',
                  name: 'feature-test'
                }
              })
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.createBranch('proj-123', 'Feature Test');

        expect(result).toMatchObject({
          id: 'branch-123',
          name: 'feature-test'
        });
      });
    });

    describe('deleteBranch', () => {
      it('should handle parse errors gracefully', async () => {
        const mockResponse = {
          result: {
            content: [{
              text: 'invalid json'
            }]
          }
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.deleteBranch('proj-123', 'branch-123');

        expect(result).toBe(false);
      });

      it('should handle missing result content', async () => {
        const mockResponse = {
          result: {}
        };
        (global.fetch as any).mockResolvedValue({
          json: jest.fn().mockResolvedValue(mockResponse)
        });

        const result = await api.deleteBranch('proj-123', 'branch-123');

        expect(result).toBe(false);
      });
    });
  });

  describe('fetchTasks', () => {
    it('should call listTasks with git_branch_id', async () => {
      const projectId = 'proj-123';
      const branchName = 'main';
      
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: { tasks: [] }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      await api.fetchTasks(projectId, branchName);

      // fetchTasks should call listTasks internally
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe('fetchSubtasks', () => {
    it('should call listSubtasks with task_id', async () => {
      const projectId = 'proj-123';
      const branchName = 'main';
      const taskId = 'task-123';
      
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              data: { subtasks: [] }
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await api.fetchSubtasks(projectId, branchName, taskId);

      expect(result).toEqual([]);
      const fetchCall = (global.fetch as any).mock.calls[0];
      const body = JSON.parse(fetchCall[1].body);
      expect(body.params.arguments.task_id).toBe(taskId);
    });
  });

  describe('listContexts', () => {
    it('should list contexts with filters', async () => {
      const filters = { status: 'active' };
      const mockResponse = {
        result: {
          content: [{
            text: JSON.stringify({
              success: true,
              contexts: [{ id: 'ctx-1' }, { id: 'ctx-2' }]
            })
          }]
        }
      };
      (global.fetch as any).mockResolvedValue({
        json: jest.fn().mockResolvedValue(mockResponse)
      });

      const result = await api.listContexts('task', filters);

      expect(result).toMatchObject({
        success: true,
        contexts: [{ id: 'ctx-1' }, { id: 'ctx-2' }]
      });
      
      const fetchCall = (global.fetch as any).mock.calls[0];
      const body = JSON.parse(fetchCall[1].body);
      expect(body.params.arguments.level).toBe('task');
      expect(body.params.arguments.filters).toEqual(filters);
    });
  });
});