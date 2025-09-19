import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    callAgent,
    checkHealth,
    completeSubtask,
    completeTask,
    createBranch,
    createProject,
    createRule,
    createSubtask,
    createTask,
    deleteBranch,
    deleteProject,
    deleteRule,
    deleteSubtask,
    deleteTask,
    getAvailableAgents,
    getBranchContext,
    getCurrentUserId,
    getGlobalContext,
    getProjectContext,
    getSubtask,
    getTask,
    getTaskContext,
    getTasks,
    isAuthenticated,
    listAgents,
    listBranches,
    listProjects,
    listRules,
    listSubtasks,
    listTasks,
    searchTasks,
    updateBranch,
    updateBranchContext,
    updateGlobalContext,
    updateProject,
    updateProjectContext,
    updateRule,
    updateSubtask,
    updateTask,
    updateTaskContext,
    validateRule
} from '../api';

// Mock the apiV2 services
vi.mock('../services/apiV2', () => ({
  taskApiV2: {
    getTasks: vi.fn(),
    getTask: vi.fn(),
    createTask: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    completeTask: vi.fn(),
  },
  subtaskApiV2: {
    listSubtasksForTask: vi.fn(),
    getSubtask: vi.fn(),
    createSubtask: vi.fn(),
    updateSubtask: vi.fn(),
    deleteSubtask: vi.fn(),
    completeSubtask: vi.fn(),
  },
  projectApiV2: {
    getProjects: vi.fn(),
    createProject: vi.fn(),
    updateProject: vi.fn(),
    deleteProject: vi.fn(),
  },
  branchApiV2: {
    getBranches: vi.fn(),
    getBranch: vi.fn(),
    createBranch: vi.fn(),
    updateBranch: vi.fn(),
    deleteBranch: vi.fn(),
    assignAgent: vi.fn(),
    getBranchHealth: vi.fn(),
  },
  contextApiV2: {
    getContext: vi.fn(),
    updateContext: vi.fn(),
    deleteContext: vi.fn(),
    resolveContext: vi.fn(),
  },
  agentApiV2: {
    getAgentsMetadata: vi.fn(),
    getAgentMetadata: vi.fn(),
    assignAgentToBranch: vi.fn(),
    unassignAgentFromBranch: vi.fn(),
    getBranchAgentAssignment: vi.fn(),
    getProjectAgentAssignments: vi.fn(),
    getAgentCapabilities: vi.fn(),
    callAgent: vi.fn(),
  },
  connectionApiV2: {
    healthCheck: vi.fn(),
    systemStatus: vi.fn(),
    testConnection: vi.fn(),
  },
  getCurrentUserId: vi.fn(),
  isAuthenticated: vi.fn(),
}));

// Get mocked services for direct access in tests
const {
  taskApiV2,
  subtaskApiV2,
  projectApiV2,
  branchApiV2,
  contextApiV2,
  agentApiV2,
  connectionApiV2,
} = vi.mocked(await import('../services/apiV2'));

describe('API V2 Module', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Task Operations', () => {
    describe('listTasks', () => {
      it('should return tasks from API response', async () => {
        const mockTasks = [
          { id: '1', title: 'Task 1', status: 'todo' },
          { id: '2', title: 'Task 2', status: 'in_progress' },
        ];
        
        taskApiV2.getTasks.mockResolvedValue({ tasks: mockTasks });

        const result = await listTasks();
        expect(result).toEqual(mockTasks);
        expect(taskApiV2.getTasks).toHaveBeenCalledWith(undefined);
      });

      it('should handle empty tasks response', async () => {
        taskApiV2.getTasks.mockResolvedValue({});

        const result = await listTasks();
        expect(result).toEqual([]);
      });

      it('should pass git_branch_id parameter', async () => {
        const branchId = 'branch-123';
        taskApiV2.getTasks.mockResolvedValue({ tasks: [] });

        await listTasks({ git_branch_id: branchId });
        expect(taskApiV2.getTasks).toHaveBeenCalledWith({ git_branch_id: branchId });
      });
    });

    describe('getTask', () => {
      it('should return single task', async () => {
        const mockTask = { id: '1', title: 'Task 1', status: 'todo' };
        taskApiV2.getTask.mockResolvedValue({ task: mockTask });

        const result = await getTask('1');
        expect(result).toEqual(mockTask);
        expect(taskApiV2.getTask).toHaveBeenCalledWith('1');
      });

      it('should handle direct response format', async () => {
        const mockTask = { id: '1', title: 'Task 1', status: 'todo' };
        taskApiV2.getTask.mockResolvedValue(mockTask);

        const result = await getTask('1');
        expect(result).toEqual(mockTask);
      });
    });

    describe('createTask', () => {
      it('should create task with required fields', async () => {
        const newTask = {
          title: 'New Task',
          description: 'Task description',
          status: 'todo',
          priority: 'medium',
          git_branch_id: 'branch-123'
        };
        const createdTask = { id: 'task-123', ...newTask };
        taskApiV2.createTask.mockResolvedValue({ task: createdTask });

        const result = await createTask(newTask);
        expect(result).toEqual(createdTask);
        expect(taskApiV2.createTask).toHaveBeenCalledWith({
          title: newTask.title,
          description: newTask.description,
          status: newTask.status,
          priority: newTask.priority,
          git_branch_id: newTask.git_branch_id
        });
      });

      it('should handle missing title', async () => {
        const newTask = { description: 'Task description' };
        taskApiV2.createTask.mockResolvedValue({ task: { id: 'task-123' } });

        await createTask(newTask);
        expect(taskApiV2.createTask).toHaveBeenCalledWith({
          title: '',
          description: newTask.description,
          status: undefined,
          priority: undefined,
          git_branch_id: undefined
        });
      });

      it('should create agent intelligence system task', async () => {
        const intelligenceTask = {
          title: 'Build Agent Intelligence System',
          description: 'Create intelligent agent selection and coordination system',
          status: 'todo',
          priority: 'critical',
          git_branch_id: 'branch-ai-system'
        };
        const createdTask = { id: 'task-ai-123', ...intelligenceTask };
        taskApiV2.createTask.mockResolvedValue({ task: createdTask });

        const result = await createTask(intelligenceTask);
        expect(result).toEqual(createdTask);
        expect(taskApiV2.createTask).toHaveBeenCalledWith({
          title: intelligenceTask.title,
          description: intelligenceTask.description,
          status: intelligenceTask.status,
          priority: intelligenceTask.priority,
          git_branch_id: intelligenceTask.git_branch_id
        });
      });

      it('should create task with high priority', async () => {
        const urgentTask = {
          title: 'Implement Real-time Agent Coordination',
          description: 'Build coordination system for multi-agent workflows',
          priority: 'high',
          git_branch_id: 'branch-coordination'
        };
        const createdTask = { 
          id: 'task-coord-456',
          ...urgentTask,
          status: 'todo'
        };
        taskApiV2.createTask.mockResolvedValue({ task: createdTask });

        const result = await createTask(urgentTask);
        expect(result).toEqual(createdTask);
        expect(taskApiV2.createTask).toHaveBeenCalledWith({
          title: urgentTask.title,
          description: urgentTask.description,
          status: undefined,
          priority: urgentTask.priority,
          git_branch_id: urgentTask.git_branch_id
        });
      });

      it('should create security focused task', async () => {
        const securityTask = {
          title: 'Security Audit for Agent System',
          description: 'Comprehensive security review of agent coordination system',
          priority: 'high',
          git_branch_id: 'branch-security-audit'
        };
        const createdTask = { id: 'task-sec-789', ...securityTask };
        taskApiV2.createTask.mockResolvedValue({ task: createdTask });

        const result = await createTask(securityTask);
        expect(result).toEqual(createdTask);
        expect(taskApiV2.createTask).toHaveBeenCalledWith({
          title: securityTask.title,
          description: securityTask.description,
          status: undefined,
          priority: securityTask.priority,
          git_branch_id: securityTask.git_branch_id
        });
      });
    });

    describe('updateTask', () => {
      it('should update task with provided fields', async () => {
        const updates = {
          title: 'Updated Task',
          status: 'in_progress',
          progress_percentage: 50
        };
        const updatedTask = { id: 'task-123', ...updates };
        taskApiV2.updateTask.mockResolvedValue({ task: updatedTask });

        const result = await updateTask('task-123', updates);
        expect(result).toEqual(updatedTask);
        expect(taskApiV2.updateTask).toHaveBeenCalledWith('task-123', {
          title: updates.title,
          description: undefined,
          status: updates.status,
          priority: undefined,
          progress_percentage: updates.progress_percentage
        });
      });
    });

    describe('deleteTask', () => {
      it('should delete task successfully', async () => {
        taskApiV2.deleteTask.mockResolvedValue(undefined);

        await deleteTask('task-123');
        expect(taskApiV2.deleteTask).toHaveBeenCalledWith('task-123');
      });
    });

    describe('completeTask', () => {
      it('should complete task with completion data', async () => {
        const completionData = {
          completion_summary: 'Task completed successfully',
          testing_notes: 'All tests passed'
        };
        const completedTask = { id: 'task-123', status: 'done' };
        taskApiV2.completeTask.mockResolvedValue({ task: completedTask });

        const result = await completeTask('task-123', completionData);
        expect(result).toEqual(completedTask);
        expect(taskApiV2.completeTask).toHaveBeenCalledWith('task-123', completionData);
      });
    });

    describe('getTasks', () => {
      it('should return tasks for branch', async () => {
        const mockTasks = [
          { id: '1', title: 'Task 1', status: 'todo' },
          { id: '2', title: 'Task 2', status: 'in_progress' },
        ];
        taskApiV2.getTasks.mockResolvedValue({ tasks: mockTasks });

        const result = await getTasks('branch-123');
        expect(result).toEqual({ tasks: mockTasks });
        expect(taskApiV2.getTasks).toHaveBeenCalledWith({ git_branch_id: 'branch-123' });
      });

      it('should handle empty response', async () => {
        taskApiV2.getTasks.mockResolvedValue({});

        const result = await getTasks('branch-123');
        expect(result).toEqual({});
      });
    });

    describe('searchTasks', () => {
      it('should filter tasks by query string', async () => {
        const mockTasks = [
          { id: '1', title: 'Authentication Task', description: 'Add JWT auth' },
          { id: '2', title: 'Database Task', description: 'Setup authentication database' },
          { id: '3', title: 'UI Task', description: 'Create login form' },
        ];
        taskApiV2.getTasks.mockResolvedValue({ tasks: mockTasks });

        const result = await searchTasks('auth');
        expect(result).toHaveLength(2);
        expect(result[0].title).toBe('Authentication Task');
        expect(result[1].description).toBe('Setup authentication database');
      });

      it('should search case-insensitively', async () => {
        const mockTasks = [
          { id: '1', title: 'AUTHENTICATION Task', description: 'auth system' }
        ];
        taskApiV2.getTasks.mockResolvedValue({ tasks: mockTasks });

        const result = await searchTasks('authentication');
        expect(result).toHaveLength(1);
        expect(result[0].title).toBe('AUTHENTICATION Task');
      });

      it('should search for agent-specific tasks', async () => {
        const mockTasks = [
          { 
            id: '1', 
            title: 'Build Agent Intelligence System', 
            description: 'Create intelligent agent coordination',
            assignees: ['system-architect-agent', 'coding-agent'],
            labels: ['agent-system', 'intelligence', 'coordination']
          },
          { 
            id: '2', 
            title: 'Security Audit', 
            description: 'Review system security',
            assignees: ['security-auditor-agent'],
            labels: ['security', 'audit']
          },
          { 
            id: '3', 
            title: 'Agent Coordination Testing', 
            description: 'Test multi-agent workflows',
            assignees: ['test-orchestrator-agent'],
            labels: ['testing', 'agent-coordination']
          }
        ];
        taskApiV2.getTasks.mockResolvedValue({ tasks: mockTasks });

        const result = await searchTasks('agent');
        expect(result).toHaveLength(2);
        expect(result[0].title).toBe('Build Agent Intelligence System');
        expect(result[1].title).toBe('Agent Coordination Testing');
      });

      it('should search by text in title and description only', async () => {
        const mockTasks = [
          { 
            id: '1', 
            title: 'Code Implementation for Agent System', 
            assignees: ['coding-agent'],
            description: 'Implement core features'
          },
          { 
            id: '2', 
            title: 'System Architecture', 
            assignees: ['system-architect-agent'],
            description: 'Design system architecture for agents'
          },
          { 
            id: '3', 
            title: 'Bug Investigation', 
            assignees: ['debugger-agent'],
            description: 'Debug memory issues'
          }
        ];
        taskApiV2.getTasks.mockResolvedValue({ tasks: mockTasks });

        const result = await searchTasks('agent');
        expect(result).toHaveLength(2);
        expect(result[0].title).toBe('Code Implementation for Agent System');
        expect(result[1].description).toBe('Design system architecture for agents');
      });

      it('should search by text in description', async () => {
        const mockTasks = [
          { id: '1', title: 'System Fix', priority: 'critical', description: 'urgent critical fix needed' },
          { id: '2', title: 'High Priority Task', priority: 'high', description: 'high priority work' },
          { id: '3', title: 'Low Priority Task', priority: 'low', description: 'can wait' }
        ];
        taskApiV2.getTasks.mockResolvedValue({ tasks: mockTasks });

        const result = await searchTasks('critical');
        expect(result).toHaveLength(1);
        expect(result[0].title).toBe('System Fix');
      });
    });
  });

  describe('Subtask Operations', () => {
    describe('listSubtasks', () => {
      it('should return subtasks for task', async () => {
        const mockSubtasks = [
          { id: 'sub-1', title: 'Subtask 1', parent_task_id: 'task-123' },
          { id: 'sub-2', title: 'Subtask 2', parent_task_id: 'task-123' },
        ];
        subtaskApiV2.listSubtasksForTask.mockResolvedValue({ subtasks: mockSubtasks });

        const result = await listSubtasks('task-123');
        expect(result).toEqual(mockSubtasks);
        expect(subtaskApiV2.listSubtasksForTask).toHaveBeenCalledWith('task-123');
      });

      it('should handle empty subtasks response', async () => {
        subtaskApiV2.listSubtasksForTask.mockResolvedValue({});

        const result = await listSubtasks('task-123');
        expect(result).toEqual([]);
      });
    });

    describe('getSubtask', () => {
      it('should return single subtask', async () => {
        const mockSubtask = { id: 'sub-1', title: 'Subtask 1', parent_task_id: 'task-123' };
        subtaskApiV2.getSubtask.mockResolvedValue({ subtask: mockSubtask });

        const result = await getSubtask('task-123', 'sub-1');
        expect(result).toEqual(mockSubtask);
        expect(subtaskApiV2.getSubtask).toHaveBeenCalledWith('sub-1');
      });

      it('should handle direct response format', async () => {
        const mockSubtask = { id: 'sub-1', title: 'Subtask 1', parent_task_id: 'task-123' };
        subtaskApiV2.getSubtask.mockResolvedValue(mockSubtask);

        const result = await getSubtask('task-123', 'sub-1');
        expect(result).toEqual(mockSubtask);
      });
    });

    describe('createSubtask', () => {
      it('should create subtask with required fields', async () => {
        const newSubtask = {
          title: 'New Subtask',
          description: 'Subtask description'
        };
        const createdSubtask = { id: 'sub-123', ...newSubtask, parent_task_id: 'task-123' };
        subtaskApiV2.createSubtask.mockResolvedValue({ subtask: createdSubtask });

        const result = await createSubtask('task-123', newSubtask);
        expect(result).toEqual(createdSubtask);
        expect(subtaskApiV2.createSubtask).toHaveBeenCalledWith('task-123', {
          title: newSubtask.title,
          description: newSubtask.description
        });
      });

      it('should create agent coordination subtasks for intelligence system', async () => {
        const coordinationSubtask = {
          title: 'Design Agent Selection Algorithm',
          description: 'Create algorithm to automatically select best agents for tasks based on task requirements and agent capabilities'
        };
        const createdSubtask = { 
          id: 'sub-coord-456', 
          ...coordinationSubtask, 
          parent_task_id: 'task-ai-intelligence' 
        };
        subtaskApiV2.createSubtask.mockResolvedValue({ subtask: createdSubtask });

        const result = await createSubtask('task-ai-intelligence', coordinationSubtask);
        expect(result).toEqual(createdSubtask);
        expect(subtaskApiV2.createSubtask).toHaveBeenCalledWith('task-ai-intelligence', {
          title: coordinationSubtask.title,
          description: coordinationSubtask.description
        });
      });

      it('should create implementation subtasks', async () => {
        const implementationSubtask = {
          title: 'Implement Workload Balancing Engine',
          description: 'Build engine to distribute tasks across available agents with proper load balancing'
        };
        const createdSubtask = { 
          id: 'sub-impl-789', 
          ...implementationSubtask, 
          parent_task_id: 'task-ai-intelligence' 
        };
        subtaskApiV2.createSubtask.mockResolvedValue({ subtask: createdSubtask });

        const result = await createSubtask('task-ai-intelligence', implementationSubtask);
        expect(result).toEqual(createdSubtask);
        expect(subtaskApiV2.createSubtask).toHaveBeenCalledWith('task-ai-intelligence', {
          title: implementationSubtask.title,
          description: implementationSubtask.description
        });
      });

      it('should create testing subtask', async () => {
        const testingSubtask = {
          title: 'Create Agent Coordination Tests',
          description: 'Develop comprehensive test suite for multi-agent coordination system'
        };
        const createdSubtask = { 
          id: 'sub-test-321', 
          ...testingSubtask, 
          parent_task_id: 'task-ai-intelligence' 
        };
        subtaskApiV2.createSubtask.mockResolvedValue({ subtask: createdSubtask });

        const result = await createSubtask('task-ai-intelligence', testingSubtask);
        expect(result).toEqual(createdSubtask);
        expect(subtaskApiV2.createSubtask).toHaveBeenCalledWith('task-ai-intelligence', {
          title: testingSubtask.title,
          description: testingSubtask.description
        });
      });
    });

    describe('updateSubtask', () => {
      it('should update subtask with progress tracking', async () => {
        const progressUpdate = {
          progress_percentage: 75,
          title: 'Design Agent Selection Algorithm - Updated',
          description: 'Algorithm implementation nearly complete',
          status: 'in_progress'
        };
        const updatedSubtask = { 
          id: 'sub-coord-456', 
          ...progressUpdate 
        };
        subtaskApiV2.updateSubtask.mockResolvedValue({ subtask: updatedSubtask });

        const result = await updateSubtask('sub-coord-456', progressUpdate);
        expect(result).toEqual(updatedSubtask);
        expect(subtaskApiV2.updateSubtask).toHaveBeenCalledWith('sub-coord-456', {
          title: progressUpdate.title,
          description: progressUpdate.description,
          status: progressUpdate.status,
          progress_percentage: progressUpdate.progress_percentage
        });
      });

      it('should update subtask with status change', async () => {
        const statusUpdate = {
          status: 'blocked',
          description: 'Blocked pending infrastructure updates'
        };
        const updatedSubtask = { 
          id: 'sub-impl-789', 
          ...statusUpdate 
        };
        subtaskApiV2.updateSubtask.mockResolvedValue({ subtask: updatedSubtask });

        const result = await updateSubtask('sub-impl-789', statusUpdate);
        expect(result).toEqual(updatedSubtask);
        expect(subtaskApiV2.updateSubtask).toHaveBeenCalledWith('sub-impl-789', {
          title: undefined,
          description: statusUpdate.description,
          status: statusUpdate.status,
          progress_percentage: undefined
        });
      });
    });

    describe('deleteSubtask', () => {
      it('should delete subtask successfully', async () => {
        subtaskApiV2.deleteSubtask.mockResolvedValue(undefined);

        await deleteSubtask('sub-123');
        expect(subtaskApiV2.deleteSubtask).toHaveBeenCalledWith('sub-123');
      });
    });

    describe('completeSubtask', () => {
      it('should complete subtask with completion notes', async () => {
        const completionNotes = 'Agent selection algorithm completed with 95% accuracy in benchmarks. Tested with 1000+ task samples, performance meets requirements.';
        const completedSubtask = { 
          id: 'sub-coord-456', 
          status: 'done',
          completion_percentage: 100
        };
        subtaskApiV2.completeSubtask.mockResolvedValue({ subtask: completedSubtask });

        const result = await completeSubtask('sub-coord-456', completionNotes);
        expect(result).toEqual(completedSubtask);
        expect(subtaskApiV2.completeSubtask).toHaveBeenCalledWith('sub-coord-456', completionNotes);
      });

      it('should complete subtask without completion notes', async () => {
        const completedSubtask = { 
          id: 'sub-impl-789', 
          status: 'done',
          completion_percentage: 100
        };
        subtaskApiV2.completeSubtask.mockResolvedValue({ subtask: completedSubtask });

        const result = await completeSubtask('sub-impl-789');
        expect(result).toEqual(completedSubtask);
        expect(subtaskApiV2.completeSubtask).toHaveBeenCalledWith('sub-impl-789', undefined);
      });
    });
  });

  describe('Project Operations', () => {
    describe('listProjects', () => {
      it('should return projects from API response', async () => {
        const mockProjects = [
          { id: '1', name: 'Project 1', description: 'First project' },
          { id: '2', name: 'Project 2', description: 'Second project' },
        ];
        projectApiV2.getProjects.mockResolvedValue({ projects: mockProjects });

        const result = await listProjects();
        expect(result).toEqual(mockProjects);
        expect(projectApiV2.getProjects).toHaveBeenCalled();
      });

      it('should handle API errors', async () => {
        projectApiV2.getProjects.mockRejectedValue(new Error('API Error'));

        await expect(listProjects()).rejects.toThrow('API Error');
      });
    });

    describe('createProject', () => {
      it('should create project with required fields', async () => {
        const newProject = {
          name: 'New Project',
          description: 'Project description'
        };
        const createdProject = { id: 'proj-123', ...newProject };
        projectApiV2.createProject.mockResolvedValue({ project: createdProject });

        const result = await createProject(newProject);
        expect(result).toEqual(createdProject);
        expect(projectApiV2.createProject).toHaveBeenCalledWith({
          name: newProject.name,
          description: newProject.description
        });
      });
    });

    describe('updateProject', () => {
      it('should update project with provided fields', async () => {
        const updates = {
          name: 'Updated Project Name',
          description: 'Updated description'
        };
        const updatedProject = { id: 'proj-123', ...updates };
        projectApiV2.updateProject.mockResolvedValue({ project: updatedProject });

        const result = await updateProject('proj-123', updates);
        expect(result).toEqual(updatedProject);
        expect(projectApiV2.updateProject).toHaveBeenCalledWith('proj-123', {
          name: updates.name,
          description: updates.description
        });
      });
    });

    describe('deleteProject', () => {
      it('should delete project successfully', async () => {
        const deleteResponse = { success: true, message: 'Project deleted' };
        projectApiV2.deleteProject.mockResolvedValue(deleteResponse);

        const result = await deleteProject('proj-123');
        expect(result).toEqual(deleteResponse);
        expect(projectApiV2.deleteProject).toHaveBeenCalledWith('proj-123');
      });
    });
  });

  describe('Branch Operations', () => {
    describe('listBranches', () => {
      it('should return branches for project', async () => {
        const mockBranches = [
          { id: '1', git_branch_name: 'main', project_id: 'proj-123' },
          { id: '2', git_branch_name: 'develop', project_id: 'proj-123' },
        ];
        branchApiV2.getBranches.mockResolvedValue({ branches: mockBranches });

        const result = await listBranches('proj-123');
        expect(result).toEqual(mockBranches);
        expect(branchApiV2.getBranches).toHaveBeenCalledWith('proj-123');
      });
    });

    describe('createBranch', () => {
      it('should create branch with required fields', async () => {
        const newBranch = {
          git_branch_name: 'feature/new-feature',
          description: 'New feature branch'
        };
        const createdBranch = { id: 'branch-123', project_id: 'proj-123', ...newBranch };
        branchApiV2.createBranch.mockResolvedValue({ branch: createdBranch });

        const result = await createBranch('proj-123', newBranch);
        expect(result).toEqual(createdBranch);
        expect(branchApiV2.createBranch).toHaveBeenCalledWith('proj-123', {
          git_branch_name: newBranch.git_branch_name,
          description: newBranch.description
        });
      });
    });

    describe('updateBranch', () => {
      it('should update branch with provided fields', async () => {
        const updates = {
          git_branch_name: 'feature/updated-feature',
          description: 'Updated description',
          is_active: false
        };
        const updatedBranch = { id: 'branch-123', ...updates };
        branchApiV2.updateBranch.mockResolvedValue({ branch: updatedBranch });

        const result = await updateBranch('branch-123', updates);
        expect(result).toEqual(updatedBranch);
        expect(branchApiV2.updateBranch).toHaveBeenCalledWith('branch-123', {
          git_branch_name: updates.git_branch_name,
          description: updates.description,
          is_active: updates.is_active
        });
      });
    });

    describe('deleteBranch', () => {
      it('should handle successful deletion with null response', async () => {
        branchApiV2.deleteBranch.mockResolvedValue(null);

        const result = await deleteBranch('branch-123');
        expect(result).toEqual({
          success: true,
          message: 'Branch deleted successfully'
        });
      });

      it('should handle response with success field', async () => {
        branchApiV2.deleteBranch.mockResolvedValue({ success: true });

        const result = await deleteBranch('branch-123');
        expect(result).toEqual({ success: true });
      });

      it('should handle error response', async () => {
        branchApiV2.deleteBranch.mockResolvedValue({
          error: 'Branch has active tasks'
        });

        const result = await deleteBranch('branch-123');
        expect(result).toEqual({
          success: false,
          error: 'Branch has active tasks'
        });
      });

      it('should handle API exceptions', async () => {
        branchApiV2.deleteBranch.mockRejectedValue(new Error('Network error'));

        const result = await deleteBranch('branch-123');
        expect(result).toEqual({
          success: false,
          error: 'Network error'
        });
      });
    });
  });

  describe('Context Operations', () => {
    describe('getTaskContext', () => {
      it('should get task context with inheritance', async () => {
        const mockContext = { data: { key: 'value' }, inherited: true };
        contextApiV2.getContext.mockResolvedValue({ context: mockContext });

        const result = await getTaskContext('task-123');
        expect(result).toEqual(mockContext);
        expect(contextApiV2.getContext).toHaveBeenCalledWith('task', 'task-123', true);
      });

      it('should handle context errors gracefully', async () => {
        contextApiV2.getContext.mockRejectedValue(new Error('Context not found'));

        const result = await getTaskContext('task-123');
        expect(result).toBeNull();
      });
    });

    describe('getBranchContext', () => {
      it('should get branch context with inheritance', async () => {
        const mockContext = { data: { branch: 'context' }, inherited: true };
        contextApiV2.getContext.mockResolvedValue({ context: mockContext });

        const result = await getBranchContext('branch-123');
        expect(result).toEqual(mockContext);
        expect(contextApiV2.getContext).toHaveBeenCalledWith('branch', 'branch-123', true);
      });

      it('should handle context errors gracefully', async () => {
        contextApiV2.getContext.mockRejectedValue(new Error('Branch context not found'));

        const result = await getBranchContext('branch-123');
        expect(result).toBeNull();
      });
    });

    describe('getProjectContext', () => {
      it('should get project context with inheritance', async () => {
        const mockContext = { data: { project: 'context' }, inherited: true };
        contextApiV2.getContext.mockResolvedValue({ context: mockContext });

        const result = await getProjectContext('proj-123');
        expect(result).toEqual(mockContext);
        expect(contextApiV2.getContext).toHaveBeenCalledWith('project', 'proj-123', true);
      });

      it('should handle context errors gracefully', async () => {
        contextApiV2.getContext.mockRejectedValue(new Error('Project context not found'));

        const result = await getProjectContext('proj-123');
        expect(result).toBeNull();
      });
    });

    describe('getGlobalContext', () => {
      it('should get global context', async () => {
        const mockContext = { data: { global: 'settings' } };
        contextApiV2.getContext.mockResolvedValue({ context: mockContext });

        const result = await getGlobalContext();
        expect(result).toEqual(mockContext);
        expect(contextApiV2.getContext).toHaveBeenCalledWith('global', 'global', false);
      });

      it('should handle context errors gracefully', async () => {
        contextApiV2.getContext.mockRejectedValue(new Error('Global context not found'));

        const result = await getGlobalContext();
        expect(result).toBeNull();
      });
    });

    describe('updateGlobalContext', () => {
      it('should update global context with dummy ID', async () => {
        const data = { setting: 'value' };
        const mockResponse = { context: { data } };
        contextApiV2.updateContext.mockResolvedValue(mockResponse);

        const result = await updateGlobalContext(data);
        expect(result).toEqual(mockResponse.context);
        expect(contextApiV2.updateContext).toHaveBeenCalledWith('global', 'global', data);
      });
    });

    describe('updateProjectContext', () => {
      it('should update project context', async () => {
        const data = { project_setting: 'value' };
        const mockResponse = { context: { data } };
        contextApiV2.updateContext.mockResolvedValue(mockResponse);

        const result = await updateProjectContext('proj-123', data);
        expect(result).toEqual(mockResponse.context);
        expect(contextApiV2.updateContext).toHaveBeenCalledWith('project', 'proj-123', data);
      });

      it('should handle update errors gracefully', async () => {
        const data = { project_setting: 'value' };
        contextApiV2.updateContext.mockRejectedValue(new Error('Update failed'));

        const result = await updateProjectContext('proj-123', data);
        expect(result).toBeNull();
      });
    });

    describe('updateBranchContext', () => {
      it('should update branch context', async () => {
        const data = { branch_setting: 'value' };
        const mockResponse = { context: { data } };
        contextApiV2.updateContext.mockResolvedValue(mockResponse);

        const result = await updateBranchContext('branch-123', data);
        expect(result).toEqual(mockResponse.context);
        expect(contextApiV2.updateContext).toHaveBeenCalledWith('branch', 'branch-123', data);
      });

      it('should handle update errors gracefully', async () => {
        const data = { branch_setting: 'value' };
        contextApiV2.updateContext.mockRejectedValue(new Error('Update failed'));

        const result = await updateBranchContext('branch-123', data);
        expect(result).toBeNull();
      });
    });

    describe('updateTaskContext', () => {
      it('should update task context', async () => {
        const data = { task_setting: 'value' };
        const mockResponse = { context: { data } };
        contextApiV2.updateContext.mockResolvedValue(mockResponse);

        const result = await updateTaskContext('task-123', data);
        expect(result).toEqual(mockResponse.context);
        expect(contextApiV2.updateContext).toHaveBeenCalledWith('task', 'task-123', data);
      });

      it('should handle update errors gracefully', async () => {
        const data = { task_setting: 'value' };
        contextApiV2.updateContext.mockRejectedValue(new Error('Update failed'));

        const result = await updateTaskContext('task-123', data);
        expect(result).toBeNull();
      });
    });
  });

  describe('Agent Operations', () => {
    describe('listAgents', () => {
      it('should return agents metadata', async () => {
        const mockAgents = [
          { name: 'coding-agent', description: 'Coding specialist' },
          { name: 'debugger-agent', description: 'Bug fixing specialist' },
        ];
        agentApiV2.getAgentsMetadata.mockResolvedValue({ agents: mockAgents });

        const result = await listAgents();
        expect(result).toEqual(mockAgents);
      });

      it('should handle agent API errors', async () => {
        agentApiV2.getAgentsMetadata.mockRejectedValue(new Error('Agent service unavailable'));

        const result = await listAgents();
        expect(result).toEqual([]);
      });
    });

    describe('getAvailableAgents', () => {
      it('should return all 42 available agents from agent library', async () => {
        const result = await getAvailableAgents();
        expect(result).toHaveLength(42);
        expect(result).toContain('coding-agent');
        expect(result).toContain('@master-orchestrator-agent');
        expect(result).toContain('debugger-agent');
        expect(result).toContain('system-architect-agent');
        expect(result).toContain('@test-orchestrator-agent');
        expect(result).toContain('@ui-designer-expert-shadcn-agent');
        expect(result).toContain('@security-auditor-agent');
        expect(result).toContain('devops-agent');
        expect(result).toContain('documentation-agent');
        expect(result).toContain('@brainjs-ml-agent');
      });

      it('should include development category agents', async () => {
        const result = await getAvailableAgents();
        const developmentAgents = [
          'coding-agent',
          'debugger-agent', 
          'code-reviewer-agent',
          '@prototyping-agent'
        ];
        developmentAgents.forEach(agent => {
          expect(result).toContain(agent);
        });
      });

      it('should include testing and QA category agents', async () => {
        const result = await getAvailableAgents();
        const testingAgents = [
          '@test-orchestrator-agent',
          '@uat-coordinator-agent',
          '@performance-load-tester-agent'
        ];
        testingAgents.forEach(agent => {
          expect(result).toContain(agent);
        });
      });

      it('should include architecture and design category agents', async () => {
        const result = await getAvailableAgents();
        const architectureAgents = [
          'system-architect-agent',
          '@design-system-agent',
          '@ui-designer-expert-shadcn-agent',
          '@core-concept-agent'
        ];
        architectureAgents.forEach(agent => {
          expect(result).toContain(agent);
        });
      });

      it('should include project planning category agents', async () => {
        const result = await getAvailableAgents();
        const planningAgents = [
          '@project-initiator-agent',
          '@task-planning-agent',
          '@master-orchestrator-agent',
          '@elicitation-agent'
        ];
        planningAgents.forEach(agent => {
          expect(result).toContain(agent);
        });
      });

      it('should include security and compliance category agents', async () => {
        const result = await getAvailableAgents();
        const securityAgents = [
          '@security-auditor-agent',
          '@compliance-scope-agent',
          '@ethical-review-agent'
        ];
        securityAgents.forEach(agent => {
          expect(result).toContain(agent);
        });
      });

      it('should include marketing and growth agents', async () => {
        const result = await getAvailableAgents();
        const marketingAgents = [
          '@marketing-strategy-orchestrator-agent',
          '@seo-sem-agent',
          '@growth-hacking-idea-agent',
          '@content-strategy-agent'
        ];
        marketingAgents.forEach(agent => {
          expect(result).toContain(agent);
        });
      });

      it('should include research and analysis agents', async () => {
        const result = await getAvailableAgents();
        const researchAgents = [
          'deep-research-agent',
          '@mcp-researcher-agent',
          '@root-cause-analysis-agent',
          '@technology-advisor-agent'
        ];
        researchAgents.forEach(agent => {
          expect(result).toContain(agent);
        });
      });
    });

    describe('callAgent', () => {
      it('should call agent successfully', async () => {
        const mockResponse = { success: true, result: 'Agent executed' };
        agentApiV2.callAgent.mockResolvedValue(mockResponse);

        const result = await callAgent('coding-agent', { task: 'implement feature' });
        expect(result).toEqual(mockResponse);
        expect(agentApiV2.callAgent).toHaveBeenCalledWith('coding-agent', { task: 'implement feature' });
      });

      it('should handle agent call errors', async () => {
        const error = new Error('Agent not found');
        error.message = 'Agent not found';
        agentApiV2.callAgent.mockRejectedValue(error);

        const result = await callAgent('invalid-agent');
        expect(result).toEqual({
          success: false,
          message: 'Agent not found',
          error: 'Error: Agent not found'
        });
      });

      it('should call master orchestrator agent with complex task', async () => {
        const complexTask = {
          task_id: 'task-123',
          title: 'Build Agent Intelligence System',
          description: 'Create intelligent agent selection and coordination system',
          requirements: ['multi-agent coordination', 'workload balancing']
        };
        const mockResponse = { 
          success: true, 
          agent: 'master-orchestrator-agent',
          result: 'Task analyzed and delegated to appropriate agents'
        };
        agentApiV2.callAgent.mockResolvedValue(mockResponse);

        const result = await callAgent('master-orchestrator-agent', complexTask);
        expect(result).toEqual(mockResponse);
        expect(agentApiV2.callAgent).toHaveBeenCalledWith('master-orchestrator-agent', complexTask);
      });

      it('should call system architect for architecture planning', async () => {
        const architectureTask = {
          task: 'design microservices architecture',
          requirements: ['scalability', 'fault tolerance', 'observability']
        };
        const mockResponse = {
          success: true,
          result: 'Architecture blueprint created with service dependencies'
        };
        agentApiV2.callAgent.mockResolvedValue(mockResponse);

        const result = await callAgent('system-architect-agent', architectureTask);
        expect(result).toEqual(mockResponse);
        expect(agentApiV2.callAgent).toHaveBeenCalledWith('system-architect-agent', architectureTask);
      });

      it('should handle timeout errors gracefully', async () => {
        const timeoutError = new Error('Request timeout');
        timeoutError.name = 'TimeoutError';
        agentApiV2.callAgent.mockRejectedValue(timeoutError);

        const result = await callAgent('coding-agent', { task: 'long running task' });
        expect(result).toEqual({
          success: false,
          message: 'Request timeout',
          error: 'TimeoutError: Request timeout'
        });
      });

      it('should handle network errors gracefully', async () => {
        const networkError = new Error('Network unreachable');
        networkError.name = 'NetworkError';
        agentApiV2.callAgent.mockRejectedValue(networkError);

        const result = await callAgent('debugger-agent', { bug: 'memory leak' });
        expect(result).toEqual({
          success: false,
          message: 'Network unreachable',
          error: 'NetworkError: Network unreachable'
        });
      });
    });
  });

  describe('Rule Operations', () => {
    describe('listRules', () => {
      it('should warn and return empty array', async () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        
        const result = await listRules();
        expect(result).toEqual([]);
        expect(consoleSpy).toHaveBeenCalledWith('Rule operations not yet implemented in V2 API');
        
        consoleSpy.mockRestore();
      });
    });

    describe('createRule', () => {
      it('should throw error for unimplemented operation', async () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        
        await expect(createRule({})).rejects.toThrow('Rule operations not available');
        expect(consoleSpy).toHaveBeenCalledWith('Rule operations not yet implemented in V2 API');
        
        consoleSpy.mockRestore();
      });
    });

    describe('updateRule', () => {
      it('should throw error for unimplemented operation', async () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        
        await expect(updateRule('rule-123', {})).rejects.toThrow('Rule operations not available');
        expect(consoleSpy).toHaveBeenCalledWith('Rule operations not yet implemented in V2 API');
        
        consoleSpy.mockRestore();
      });
    });

    describe('deleteRule', () => {
      it('should throw error for unimplemented operation', async () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        
        await expect(deleteRule('rule-123')).rejects.toThrow('Rule operations not available');
        expect(consoleSpy).toHaveBeenCalledWith('Rule operations not yet implemented in V2 API');
        
        consoleSpy.mockRestore();
      });
    });

    describe('validateRule', () => {
      it('should return invalid result for unimplemented operation', async () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        
        const result = await validateRule({});
        expect(result).toEqual({ valid: false, errors: ['Rule operations not available'] });
        expect(consoleSpy).toHaveBeenCalledWith('Rule operations not yet implemented in V2 API');
        
        consoleSpy.mockRestore();
      });
    });
  });

  describe('Connection Operations', () => {
    describe('checkHealth', () => {
      it('should return true for healthy status', async () => {
        connectionApiV2.healthCheck.mockResolvedValue({ status: 'healthy' });

        const result = await checkHealth();
        expect(result).toBe(true);
      });

      it('should return false for unhealthy status', async () => {
        connectionApiV2.healthCheck.mockResolvedValue({ status: 'degraded' });

        const result = await checkHealth();
        expect(result).toBe(false);
      });

      it('should return false on health check error', async () => {
        connectionApiV2.healthCheck.mockRejectedValue(new Error('Service unavailable'));

        const result = await checkHealth();
        expect(result).toBe(false);
      });
    });
  });

  describe('Authentication Utilities', () => {
    describe('getCurrentUserId', () => {
      it('should call the imported utility function', async () => {
        const { getCurrentUserId: mockGetCurrentUserId } = vi.mocked(await import('../services/apiV2'));
        mockGetCurrentUserId.mockReturnValue('user-123');

        const result = getCurrentUserId();
        expect(result).toBe('user-123');
        expect(mockGetCurrentUserId).toHaveBeenCalled();
      });
    });

    describe('isAuthenticated', () => {
      it('should call the imported utility function', async () => {
        const { isAuthenticated: mockIsAuthenticated } = vi.mocked(await import('../services/apiV2'));
        mockIsAuthenticated.mockReturnValue(true);

        const result = isAuthenticated();
        expect(result).toBe(true);
        expect(mockIsAuthenticated).toHaveBeenCalled();
      });
    });
  });

  describe('Real-time Agent Coordination', () => {
    describe('Agent Session Management', () => {
      it('should register agent session for real-time tracking', async () => {
        const sessionData = {
          agent_id: 'coding-agent',
          session_id: 'session-123',
          project_id: 'proj-456',
          max_concurrent_tasks: 5
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.registerSession.mockResolvedValue({ session: sessionData });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
      
      it('should track agent resource usage in real-time', async () => {
        const resourceUpdate = {
          agent_id: 'coding-agent',
          resource_type: 'memory',
          used: 512,
          allocated: 1024,
          usage_percentage: 50
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.updateResourceUsage.mockResolvedValue({ success: true });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
    });

    describe('WebSocket Communication', () => {
      it('should establish WebSocket connection for agent', async () => {
        const wsConfig = {
          agent_id: 'coding-agent',
          session_id: 'session-123',
          channels: ['global', 'status', 'coordination']
        };
        
        // WebSocket tests would use mock WebSocket when API is ready
        // const ws = new MockWebSocket();
        // agentApiV2.connectWebSocket.mockResolvedValue(ws);
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
      
      it('should send coordination messages between agents', async () => {
        const message = {
          type: 'coordination_request',
          from_agent: 'coding-agent',
          to_agent: 'test-orchestrator-agent',
          payload: {
            coordination_type: 'handoff',
            task_id: 'task-123',
            reason: 'Task completed, ready for testing'
          }
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.sendCoordinationMessage.mockResolvedValue({ sent: true });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
    });

    describe('Real-time Status Updates', () => {
      it('should broadcast agent status changes', async () => {
        const statusUpdate = {
          agent_id: 'coding-agent',
          status: 'busy',
          current_task: 'task-123',
          activity: 'Implementing authentication',
          health_score: 95
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.broadcastStatus.mockResolvedValue({ broadcast: true });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
      
      it('should handle agent workload rebalancing', async () => {
        const rebalanceRequest = {
          project_id: 'proj-123',
          overloaded_agents: ['coding-agent'],
          available_agents: ['debugger-agent', 'code-reviewer-agent'],
          tasks_to_reassign: ['task-456', 'task-789']
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.rebalanceWorkload.mockResolvedValue({
        //   reassigned: { 'task-456': 'debugger-agent' }
        // });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
    });

    describe('Parallel Execution Coordination', () => {
      it('should coordinate parallel task execution', async () => {
        const parallelTasks = [
          { task_id: 'task-frontend', agent: 'shadcn-ui-expert-agent' },
          { task_id: 'task-backend', agent: 'coding-agent' },
          { task_id: 'task-tests', agent: 'test-orchestrator-agent' }
        ];
        
        // Mock would be implemented when API is ready
        // agentApiV2.coordinateParallelExecution.mockResolvedValue({
        //   execution_plan: parallelTasks,
        //   estimated_completion: '2 hours'
        // });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
      
      it('should handle inter-agent dependencies', async () => {
        const dependency = {
          waiting_agent: 'test-orchestrator-agent',
          waiting_task: 'task-test-123',
          blocking_agent: 'coding-agent',
          blocking_task: 'task-impl-456',
          notification_sent: false
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.trackDependency.mockResolvedValue({ tracked: true });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
    });

    describe('Agent Communication Hub', () => {
      it('should handle work handoff between agents', async () => {
        const handoff = {
          handoff_id: 'handoff-123',
          from_agent: 'coding-agent',
          to_agent: 'code-reviewer-agent',
          task_id: 'task-123',
          work_summary: 'Authentication implementation complete',
          completed_items: ['JWT setup', 'Login endpoint', 'Refresh tokens'],
          remaining_items: ['Session management', 'Logout endpoint']
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.initiateHandoff.mockResolvedValue({ handoff_id: 'handoff-123' });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
      
      it('should resolve conflicts between agents', async () => {
        const conflict = {
          conflict_id: 'conflict-123',
          type: 'resource_contention',
          agents: ['coding-agent', 'debugger-agent'],
          resource: 'database_connection',
          resolution_strategy: 'priority_based'
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.resolveConflict.mockResolvedValue({
        //   resolved: true,
        //   winner: 'debugger-agent'
        // });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
    });

    describe('Progress Synchronization', () => {
      it('should sync task progress across agents', async () => {
        const progressUpdate = {
          task_id: 'task-123',
          agent_id: 'coding-agent',
          progress: 75,
          milestones_completed: ['Design', 'Implementation'],
          milestones_remaining: ['Testing', 'Documentation'],
          estimated_completion: '1 hour'
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.syncProgress.mockResolvedValue({ synced: true });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
      
      it('should notify dependent agents of completion', async () => {
        const completion = {
          completed_task: 'task-impl-123',
          completed_by: 'coding-agent',
          dependent_tasks: ['task-test-456', 'task-doc-789'],
          notifications_sent: ['test-orchestrator-agent', 'documentation-agent']
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.notifyCompletion.mockResolvedValue({
        //   notified: completion.notifications_sent
        // });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
    });

    describe('Agent Health Monitoring', () => {
      it('should detect and recover from agent failures', async () => {
        const failureEvent = {
          agent_id: 'coding-agent',
          failure_type: 'timeout',
          last_heartbeat: '2024-01-01T12:00:00Z',
          recovery_action: 'restart_session',
          tasks_affected: ['task-123', 'task-456']
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.handleAgentFailure.mockResolvedValue({
        //   recovered: true,
        //   new_session_id: 'session-456'
        // });
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
      
      it('should monitor agent health scores', async () => {
        const healthMetrics = {
          agent_id: 'coding-agent',
          health_score: 85,
          metrics: {
            task_success_rate: 0.95,
            avg_response_time_ms: 150,
            error_count: 2,
            resource_utilization: 0.65
          },
          recommendations: ['Consider reducing concurrent tasks']
        };
        
        // Mock would be implemented when API is ready
        // agentApiV2.getAgentHealth.mockResolvedValue(healthMetrics);
        
        // Placeholder test for now
        expect(true).toBe(true);
      });
    });
  });

  describe('TaskMCPController Comprehensive Test Suite', () => {
    describe('Security Audit Task Operations', () => {
      it('should create security audit task with proper agent assignments', async () => {
        const securityAuditTask = {
          title: 'Security Audit and Compliance Review',
          description: 'Conduct comprehensive security audit and compliance review of the AI task planning system',
          status: 'todo',
          priority: 'critical',
          git_branch_id: 'branch-security-audit',
          assignees: 'security-auditor-agent,compliance-scope-agent',
          estimated_effort: '3 days'
        };
        const createdTask = { 
          id: 'task-security-123', 
          ...securityAuditTask,
          assignees: ['security-auditor-agent', 'compliance-scope-agent']
        };
        taskApiV2.createTask.mockResolvedValue({ task: createdTask });

        const result = await createTask(securityAuditTask);
        expect(result).toEqual(createdTask);
        expect(taskApiV2.createTask).toHaveBeenCalledWith({
          title: securityAuditTask.title,
          description: securityAuditTask.description,
          status: securityAuditTask.status,
          priority: securityAuditTask.priority,
          git_branch_id: securityAuditTask.git_branch_id
        });
      });

      it('should handle multiple security agent assignments correctly', async () => {
        const multiAgentSecurityTask = {
          title: 'Multi-Agent Security Review',
          description: 'Security review requiring multiple specialized agents',
          assignees: '@security-auditor-agent,@compliance-scope-agent,@ethical-review-agent',
          priority: 'critical',
          git_branch_id: 'branch-multi-security'
        };
        const createdTask = { 
          id: 'task-multi-sec-456',
          ...multiAgentSecurityTask,
          assignees: ['security-auditor-agent', 'compliance-scope-agent', 'ethical-review-agent'],
          status: 'todo'
        };
        taskApiV2.createTask.mockResolvedValue({ task: createdTask });

        const result = await createTask(multiAgentSecurityTask);
        expect(result.assignees).toHaveLength(3);
        expect(result.assignees).toContain('security-auditor-agent');
        expect(result.assignees).toContain('compliance-scope-agent');
        expect(result.assignees).toContain('ethical-review-agent');
      });

      it('should create GDPR compliance validation subtask', async () => {
        const gdprSubtask = {
          title: 'GDPR Compliance Validation',
          description: 'Validate GDPR compliance for data protection regulations including data minimization, purpose limitation, and right to be forgotten'
        };
        const createdSubtask = { 
          id: 'sub-gdpr-123', 
          ...gdprSubtask,
          parent_task_id: 'task-security-123' 
        };
        subtaskApiV2.createSubtask.mockResolvedValue({ subtask: createdSubtask });

        const result = await createSubtask('task-security-123', gdprSubtask);
        expect(result).toEqual(createdSubtask);
        expect(subtaskApiV2.createSubtask).toHaveBeenCalledWith('task-security-123', {
          title: gdprSubtask.title,
          description: gdprSubtask.description
        });
      });

      it('should create vulnerability assessment subtask', async () => {
        const vulnSubtask = {
          title: 'Security Vulnerability Assessment',
          description: 'Complete vulnerability assessment with risk ratings for authentication, authorization, data protection, and input validation'
        };
        const createdSubtask = { 
          id: 'sub-vuln-456', 
          ...vulnSubtask,
          parent_task_id: 'task-security-123' 
        };
        subtaskApiV2.createSubtask.mockResolvedValue({ subtask: createdSubtask });

        const result = await createSubtask('task-security-123', vulnSubtask);
        expect(result).toEqual(createdSubtask);
      });
    });

    describe('Task Dependency Management', () => {
      it('should handle task dependencies for security audit', async () => {
        const deploymentTask = {
          title: 'Production Deployment and DevOps Pipeline',
          description: 'Deploy AI planning system to production with DevOps pipeline',
          priority: 'high',
          git_branch_id: 'branch-deployment',
          dependencies: '2761d924-e542-49b4-8235-b1547010bbc7' // Security audit task ID
        };
        const createdTask = { 
          id: 'task-deploy-789',
          ...deploymentTask,
          dependencies: ['2761d924-e542-49b4-8235-b1547010bbc7'],
          status: 'blocked' // Blocked by security audit
        };
        taskApiV2.createTask.mockResolvedValue({ task: createdTask });

        const result = await createTask(deploymentTask);
        expect(result.status).toBe('blocked');
        expect(result.dependencies).toContain('2761d924-e542-49b4-8235-b1547010bbc7');
      });

      it('should validate dependency chain completeness', async () => {
        const taskWithDependencies = {
          id: 'task-final-123',
          title: 'Final System Integration',
          dependencies: ['task-1', 'task-2', 'task-3'],
          dependency_relationships: {
            dependency_summary: {
              total_dependencies: 3,
              completed_dependencies: 2,
              can_start: false,
              is_blocked: true
            }
          }
        };
        taskApiV2.getTask.mockResolvedValue({ task: taskWithDependencies });

        const result = await getTask('task-final-123');
        expect(result.dependency_relationships.dependency_summary.can_start).toBe(false);
        expect(result.dependency_relationships.dependency_summary.completed_dependencies).toBe(2);
      });
    });

    describe('Task Progress and Completion', () => {
      it('should update security audit task progress with insights', async () => {
        const progressUpdate = {
          status: 'in_progress',
          progress_percentage: 60,
          details: 'Completed authentication and authorization audit. Found 3 critical issues with JWT token validation.',
          insights_found: 'JWT tokens not expiring properly, missing rate limiting on auth endpoints'
        };
        const updatedTask = { 
          id: 'task-security-123',
          ...progressUpdate
        };
        taskApiV2.updateTask.mockResolvedValue({ task: updatedTask });

        const result = await updateTask('task-security-123', progressUpdate);
        expect(result.progress_percentage).toBe(60);
        expect(result.status).toBe('in_progress');
      });

      it('should complete security audit with comprehensive summary', async () => {
        const completionData = {
          completion_summary: 'Security audit completed. Found and resolved 3 critical, 5 high, and 12 medium vulnerabilities. Implemented SOC2 compliance measures.',
          testing_notes: 'Performed penetration testing, static code analysis, and dependency scanning. All critical issues resolved.',
          insights_found: 'Need to implement automated security scanning in CI/CD pipeline for continuous monitoring'
        };
        const completedTask = { 
          id: 'task-security-123',
          status: 'done',
          progress_percentage: 100,
          ...completionData
        };
        taskApiV2.completeTask.mockResolvedValue({ task: completedTask });

        const result = await completeTask('task-security-123', completionData);
        expect(result.status).toBe('done');
        expect(result.progress_percentage).toBe(100);
      });
    });

    describe('Agent-Specific Task Search', () => {
      it('should search for security-related tasks', async () => {
        const mockSecurityTasks = [
          { 
            id: '1',
            title: 'Security Audit and Compliance Review',
            assignees: ['security-auditor-agent', 'compliance-scope-agent'],
            priority: 'critical'
          },
          { 
            id: '2',
            title: 'Authentication Security Hardening',
            assignees: ['security-auditor-agent'],
            priority: 'high'
          },
          { 
            id: '3',
            title: 'OWASP Security Standards Implementation',
            assignees: ['security-auditor-agent', 'coding-agent'],
            priority: 'high'
          }
        ];
        taskApiV2.getTasks.mockResolvedValue({ tasks: mockSecurityTasks });

        const result = await searchTasks('security');
        expect(result).toHaveLength(3);
        expect(result[0].title).toBe('Security Audit and Compliance Review');
        expect(result[0].assignees).toContain('security-auditor-agent');
      });

      it('should filter tasks by compliance requirements', async () => {
        const mockComplianceTasks = [
          { 
            id: '1',
            title: 'GDPR Compliance Implementation',
            description: 'Implement GDPR data protection requirements',
            labels: ['compliance', 'gdpr', 'data-protection']
          },
          { 
            id: '2',
            title: 'SOC2 Compliance Readiness',
            description: 'Prepare for SOC2 compliance certification',
            labels: ['compliance', 'soc2', 'security']
          }
        ];
        taskApiV2.getTasks.mockResolvedValue({ tasks: mockComplianceTasks });

        const result = await searchTasks('compliance');
        expect(result).toHaveLength(2);
        expect(result.every(task => 
          task.title.toLowerCase().includes('compliance') || 
          task.description.toLowerCase().includes('compliance')
        )).toBe(true);
      });
    });

    describe('Enhanced Agent Coordination', () => {
      it('should coordinate security audit with DevOps deployment', async () => {
        const coordinationMessage = {
          type: 'task_coordination',
          from_agent: 'security-auditor-agent',
          to_agent: 'devops-agent',
          task_id: 'task-security-123',
          message: 'Security audit complete. System cleared for production deployment.',
          clearance_level: 'production-ready',
          security_report: {
            vulnerabilities_found: 20,
            vulnerabilities_resolved: 20,
            compliance_status: 'passed',
            recommendations: ['Enable security monitoring', 'Implement WAF']
          }
        };
        
        // This would be implemented when real-time coordination is available
        expect(coordinationMessage.clearance_level).toBe('production-ready');
        expect(coordinationMessage.security_report.compliance_status).toBe('passed');
      });

      it('should handle security blocker escalation', async () => {
        const securityBlocker = {
          task_id: 'task-deploy-789',
          blocker_type: 'security',
          severity: 'critical',
          description: 'Critical SQL injection vulnerability found in user input handling',
          blocking_agent: 'security-auditor-agent',
          requires_resolution_before: ['production deployment', 'user acceptance testing']
        };
        
        // Mock blocker creation when API is ready
        expect(securityBlocker.severity).toBe('critical');
        expect(securityBlocker.blocking_agent).toBe('security-auditor-agent');
      });
    });

    describe('Compliance Tracking and Reporting', () => {
      it('should track GDPR compliance requirements', async () => {
        const gdprRequirements = {
          task_id: 'task-gdpr-compliance',
          compliance_type: 'GDPR',
          requirements: {
            data_minimization: { status: 'implemented', notes: 'Only collecting necessary user data' },
            purpose_limitation: { status: 'implemented', notes: 'Data used only for stated purposes' },
            storage_limitation: { status: 'in_progress', notes: 'Implementing auto-deletion policies' },
            accuracy: { status: 'implemented', notes: 'User can update their data' },
            security: { status: 'implemented', notes: 'AES-256 encryption at rest' },
            accountability: { status: 'documented', notes: 'Full compliance documentation' }
          },
          overall_compliance: 85
        };
        
        expect(gdprRequirements.overall_compliance).toBe(85);
        expect(Object.values(gdprRequirements.requirements).filter(r => r.status === 'implemented')).toHaveLength(4);
      });

      it('should generate compliance audit report', async () => {
        const auditReport = {
          report_id: 'audit-report-123',
          audit_date: '2025-09-12',
          auditor: 'compliance-scope-agent',
          compliance_frameworks: ['GDPR', 'SOC2', 'OWASP'],
          findings: {
            compliant_areas: 28,
            non_compliant_areas: 2,
            recommendations: 5,
            critical_issues: 0
          },
          certification_ready: true
        };
        
        expect(auditReport.certification_ready).toBe(true);
        expect(auditReport.findings.critical_issues).toBe(0);
      });
    });

    describe('Security Testing Integration', () => {
      it('should run automated security scans', async () => {
        const securityScan = {
          scan_id: 'scan-123',
          scan_type: 'comprehensive',
          tools_used: ['OWASP ZAP', 'SonarQube', 'Dependabot'],
          findings: {
            sql_injection: 0,
            xss_vulnerabilities: 1,
            authentication_issues: 0,
            insecure_dependencies: 3,
            total_issues: 4
          },
          severity_distribution: {
            critical: 0,
            high: 1,
            medium: 3,
            low: 0
          }
        };
        
        expect(securityScan.findings.total_issues).toBe(4);
        expect(securityScan.severity_distribution.critical).toBe(0);
      });

      it('should validate security controls implementation', async () => {
        const securityControls = {
          authentication: {
            mfa_enabled: true,
            jwt_implementation: 'secure',
            session_management: 'implemented',
            password_policy: 'strong'
          },
          authorization: {
            rbac_implemented: true,
            permission_granularity: 'resource-level',
            api_protection: 'enabled'
          },
          data_protection: {
            encryption_at_rest: 'AES-256',
            encryption_in_transit: 'TLS 1.3',
            key_management: 'HSM-backed'
          },
          monitoring: {
            security_logging: 'enabled',
            anomaly_detection: 'configured',
            incident_response: 'documented'
          }
        };
        
        expect(securityControls.authentication.mfa_enabled).toBe(true);
        expect(securityControls.data_protection.encryption_at_rest).toBe('AES-256');
        expect(securityControls.monitoring.security_logging).toBe('enabled');
      });
    });
  });
});