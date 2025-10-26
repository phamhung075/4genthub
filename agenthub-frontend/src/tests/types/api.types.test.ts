import { describe, it, expect } from 'vitest';
import type {
  Task,
  Subtask,
  Project,
  Branch,
  Rule,
  ApiResponse,
  TaskResponse,
  TasksResponse,
  SubtaskResponse,
  SubtasksResponse,
  ProjectResponse,
  ProjectsResponse,
  BranchResponse,
  BranchesResponse,
  ContextResponse,
  DeleteResponse,
  HealthResponse,
  AgentsResponse,
  BulkSummaryRequest,
  BranchSummary,
  ProjectSummary,
  BulkSummaryMetadata,
  BulkSummaryResponse,
  LegacyBranchResponse
} from '../../types/api.types';

describe('API Types', () => {
  describe('Core Entity Types', () => {
    describe('Task Type', () => {
      it('should have required properties', () => {
        const task: Task = {
          id: 'task-123',
          title: 'Test Task',
          status: 'in_progress',
          priority: 'high',
          assignees: ['user1', 'user2'],
          subtasks: ['sub-1', 'sub-2', 'sub-3'],
          has_dependencies: true,
          has_context: true,
          git_branch_id: 'branch-123',
          project_id: 'project-123'
        };

        expect(task.id).toBe('task-123');
        expect(task.title).toBe('Test Task');
        expect(task.status).toBe('in_progress');
        expect(task.priority).toBe('high');
        expect(task.assignees).toHaveLength(2);
        expect(task.subtasks).toHaveLength(3);
        expect(task.has_dependencies).toBe(true);
        expect(task.has_context).toBe(true);
        expect(task.git_branch_id).toBe('branch-123');
        expect(task.project_id).toBe('project-123');
      });

      it('should allow optional properties', () => {
        const task: Task = {
          id: 'task-123',
          title: 'Test Task',
          description: 'Task description',
          status: 'todo',
          priority: 'medium',
          assignees: ['user1', 'user2'],
          subtasks: [],
          has_dependencies: false,
          dependencies: ['dep-1', 'dep-2'],
          has_context: true,
          context_id: 'context-123',
          context_data: { key: 'value' },
          git_branch_id: 'branch-123',
          project_id: 'project-123',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-02T00:00:00Z',
          due_date: '2025-01-31T23:59:59Z',
          estimated_effort: '3 days',
          labels: ['frontend', 'urgent'],
          details: 'Additional details',
          progress_percentage: 75,
          subtasks: ['sub-1', 'sub-2'],
          parent_task_id: 'parent-123',
          progress_history: { '2025-01-01': { status: 'todo' } },
          progress_count: 5
        };

        expect(task.description).toBe('Task description');
        expect(task.assignees).toEqual(['user1', 'user2']);
        expect(task.dependencies).toEqual(['dep-1', 'dep-2']);
        expect(task.context_id).toBe('context-123');
        expect(task.context_data).toEqual({ key: 'value' });
        expect(task.created_at).toBe('2025-01-01T00:00:00Z');
        expect(task.updated_at).toBe('2025-01-02T00:00:00Z');
        expect(task.due_date).toBe('2025-01-31T23:59:59Z');
        expect(task.estimated_effort).toBe('3 days');
        expect(task.labels).toEqual(['frontend', 'urgent']);
        expect(task.details).toBe('Additional details');
        expect(task.progress_percentage).toBe(75);
        expect(task.subtasks).toEqual(['sub-1', 'sub-2']);
        expect(task.parent_task_id).toBe('parent-123');
        expect(task.progress_history).toEqual({ '2025-01-01': { status: 'todo' } });
        expect(task.progress_count).toBe(5);
      });

      it('should support subtasks as array of objects', () => {
        const subtaskObjects: Subtask[] = [
          {
            id: 'sub-1',
            task_id: 'task-123',
            title: 'Subtask 1',
            status: 'done',
            priority: 'high',
            assignees: ['user1']
          },
          {
            id: 'sub-2',
            task_id: 'task-123',
            title: 'Subtask 2',
            status: 'in_progress',
            priority: 'medium',
            assignees: ['user1', 'user2']
          }
        ];

        const task: Task = {
          id: 'task-123',
          title: 'Test Task',
          status: 'in_progress',
          priority: 'high',
          assignees: ['user1', 'user2'],
          subtasks: subtaskObjects,
          has_dependencies: false,
          has_context: false,
          git_branch_id: 'branch-123',
          project_id: 'project-123'
        };

        expect(task.subtasks).toHaveLength(2);
        expect((task.subtasks as Subtask[])[0].id).toBe('sub-1');
        expect((task.subtasks as Subtask[])[1].id).toBe('sub-2');
      });
    });

    describe('Subtask Type', () => {
      it('should have required properties', () => {
        const subtask: Subtask = {
          id: 'sub-123',
          task_id: 'task-123',
          title: 'Test Subtask',
          status: 'todo',
          priority: 'medium',
          assignees: ['user1']
        };

        expect(subtask.id).toBe('sub-123');
        expect(subtask.task_id).toBe('task-123');
        expect(subtask.title).toBe('Test Subtask');
        expect(subtask.status).toBe('todo');
        expect(subtask.priority).toBe('medium');
        expect(subtask.assignees).toEqual(['user1']);
      });

      it('should allow optional properties', () => {
        const subtask: Subtask = {
          id: 'sub-123',
          task_id: 'task-123',
          title: 'Test Subtask',
          description: 'Subtask description',
          status: 'done',
          priority: 'high',
          assignees: ['user1'],
          progress_percentage: 100,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-02T00:00:00Z',
          progress_notes: 'Completed implementation',
          completion_summary: 'Successfully implemented feature'
        };

        expect(subtask.description).toBe('Subtask description');
        expect(subtask.assignees).toEqual(['user1']);
        expect(subtask.progress_percentage).toBe(100);
        expect(subtask.created_at).toBe('2025-01-01T00:00:00Z');
        expect(subtask.updated_at).toBe('2025-01-02T00:00:00Z');
        expect(subtask.progress_notes).toBe('Completed implementation');
        expect(subtask.completion_summary).toBe('Successfully implemented feature');
      });
    });

    describe('Project Type', () => {
      it('should have required properties', () => {
        const project: Project = {
          id: 'project-123',
          name: 'Test Project'
        };

        expect(project.id).toBe('project-123');
        expect(project.name).toBe('Test Project');
      });

      it('should allow optional properties', () => {
        const project: Project = {
          id: 'project-123',
          name: 'Test Project',
          description: 'Project description',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-02T00:00:00Z',
          owner_id: 'user-123',
          status: 'active',
          branch_count: 5,
          task_count: 25
        };

        expect(project.description).toBe('Project description');
        expect(project.created_at).toBe('2025-01-01T00:00:00Z');
        expect(project.updated_at).toBe('2025-01-02T00:00:00Z');
        expect(project.owner_id).toBe('user-123');
        expect(project.status).toBe('active');
        expect(project.branch_count).toBe(5);
        expect(project.task_count).toBe(25);
      });

      it('should support branches as record and array formats', () => {
        const branch1: Branch = {
          id: 'branch-1',
          project_id: 'project-123',
          name: 'Feature Branch',
          git_branch_name: 'feature/test'
        };

        const branch2: Branch = {
          id: 'branch-2',
          project_id: 'project-123',
          name: 'Main Branch',
          git_branch_name: 'main'
        };

        // Record format
        const projectWithRecord: Project = {
          id: 'project-123',
          name: 'Test Project',
          git_branchs: {
            'branch-1': branch1,
            'branch-2': branch2
          }
        };

        expect(projectWithRecord.git_branchs).toBeDefined();
        expect(projectWithRecord.git_branchs!['branch-1']).toEqual(branch1);
        expect(projectWithRecord.git_branchs!['branch-2']).toEqual(branch2);

        // Array format
        const projectWithArray: Project = {
          id: 'project-123',
          name: 'Test Project',
          branches: [branch1, branch2]
        };

        expect(projectWithArray.branches).toBeDefined();
        expect(projectWithArray.branches).toHaveLength(2);
        expect(projectWithArray.branches![0]).toEqual(branch1);
        expect(projectWithArray.branches![1]).toEqual(branch2);
      });
    });

    describe('Branch Type', () => {
      it('should have required properties', () => {
        const branch: Branch = {
          id: 'branch-123',
          project_id: 'project-123',
          name: 'Feature Branch',
          git_branch_name: 'feature/test'
        };

        expect(branch.id).toBe('branch-123');
        expect(branch.project_id).toBe('project-123');
        expect(branch.name).toBe('Feature Branch');
        expect(branch.git_branch_name).toBe('feature/test');
      });

      it('should allow optional properties', () => {
        const branch: Branch = {
          id: 'branch-123',
          project_id: 'project-123',
          name: 'Feature Branch',
          git_branch_name: 'feature/test',
          description: 'Branch for testing feature',
          status: 'active',
          is_active: true,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-02T00:00:00Z',
          task_count: 10,
          completed_tasks: 7
        };

        expect(branch.description).toBe('Branch for testing feature');
        expect(branch.status).toBe('active');
        expect(branch.is_active).toBe(true);
        expect(branch.created_at).toBe('2025-01-01T00:00:00Z');
        expect(branch.updated_at).toBe('2025-01-02T00:00:00Z');
        expect(branch.task_count).toBe(10);
        expect(branch.completed_tasks).toBe(7);
      });
    });

    describe('Rule Type', () => {
      it('should have required properties', () => {
        const rule: Rule = {
          id: 'rule-123',
          name: 'Test Rule'
        };

        expect(rule.id).toBe('rule-123');
        expect(rule.name).toBe('Test Rule');
      });

      it('should allow optional properties', () => {
        const rule: Rule = {
          id: 'rule-123',
          name: 'Test Rule',
          description: 'Rule description',
          category: 'security',
          content: 'Rule content here',
          enabled: true,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-02T00:00:00Z'
        };

        expect(rule.description).toBe('Rule description');
        expect(rule.category).toBe('security');
        expect(rule.content).toBe('Rule content here');
        expect(rule.enabled).toBe(true);
        expect(rule.created_at).toBe('2025-01-01T00:00:00Z');
        expect(rule.updated_at).toBe('2025-01-02T00:00:00Z');
      });
    });
  });

  describe('API Response Types', () => {
    describe('ApiResponse Generic Type', () => {
      it('should support success response', () => {
        const response: ApiResponse<string> = {
          success: true,
          data: 'Success data',
          timestamp: '2025-01-01T00:00:00Z'
        };

        expect(response.success).toBe(true);
        expect(response.data).toBe('Success data');
        expect(response.timestamp).toBe('2025-01-01T00:00:00Z');
      });

      it('should support error response', () => {
        const response: ApiResponse = {
          success: false,
          error: 'Something went wrong',
          message: 'Error occurred during operation'
        };

        expect(response.success).toBe(false);
        expect(response.error).toBe('Something went wrong');
        expect(response.message).toBe('Error occurred during operation');
      });

      it('should support generic data types', () => {
        interface CustomData {
          id: string;
          value: number;
        }

        const response: ApiResponse<CustomData> = {
          success: true,
          data: {
            id: 'custom-123',
            value: 42
          }
        };

        expect(response.data?.id).toBe('custom-123');
        expect(response.data?.value).toBe(42);
      });
    });

    describe('TaskResponse Type', () => {
      it('should have task property', () => {
        const response: TaskResponse = {
          success: true,
          task: {
            id: 'task-123',
            title: 'Test Task',
            status: 'todo',
            priority: 'medium',
            assignees: [],
            subtasks: [],
            has_dependencies: false,
            has_context: false,
            git_branch_id: 'branch-123',
            project_id: 'project-123'
          }
        };

        expect(response.success).toBe(true);
        expect(response.task).toBeDefined();
        expect(response.task.id).toBe('task-123');
        expect(response.task.title).toBe('Test Task');
      });
    });

    describe('TasksResponse Type', () => {
      it('should have tasks array with pagination', () => {
        const response: TasksResponse = {
          success: true,
          tasks: [
            {
              id: 'task-1',
              title: 'Task 1',
              status: 'todo',
              priority: 'high',
              assignees: ['user1'],
              subtasks: [],
              has_dependencies: false,
              has_context: false,
              git_branch_id: 'branch-123',
              project_id: 'project-123'
            },
            {
              id: 'task-2',
              title: 'Task 2',
              status: 'done',
              priority: 'low',
              assignees: ['user1', 'user2'],
              subtasks: ['sub-1'],
              has_dependencies: true,
              has_context: true,
              git_branch_id: 'branch-123',
              project_id: 'project-123'
            }
          ],
          total: 2,
          page: 1,
          limit: 10
        };

        expect(response.success).toBe(true);
        expect(response.tasks).toHaveLength(2);
        expect(response.tasks[0].id).toBe('task-1');
        expect(response.tasks[1].id).toBe('task-2');
        expect(response.total).toBe(2);
        expect(response.page).toBe(1);
        expect(response.limit).toBe(10);
      });
    });

    describe('Other Response Types', () => {
      it('should support SubtaskResponse', () => {
        const response: SubtaskResponse = {
          success: true,
          subtask: {
            id: 'sub-123',
            task_id: 'task-123',
            title: 'Subtask',
            status: 'todo',
            priority: 'medium',
            assignees: ['user1']
          }
        };

        expect(response.subtask).toBeDefined();
        expect(response.subtask.id).toBe('sub-123');
      });

      it('should support ProjectResponse', () => {
        const response: ProjectResponse = {
          success: true,
          project: {
            id: 'project-123',
            name: 'Test Project'
          }
        };

        expect(response.project).toBeDefined();
        expect(response.project.id).toBe('project-123');
      });

      it('should support ContextResponse', () => {
        const response: ContextResponse = {
          success: true,
          context: {
            task_data: { key: 'value' },
            metadata: { created_at: '2025-01-01T00:00:00Z' }
          },
          level: 'task',
          inherited: {
            branch_context: { key: 'branch_value' }
          }
        };

        expect(response.context).toBeDefined();
        expect(response.context.task_data).toEqual({ key: 'value' });
        expect(response.level).toBe('task');
        expect(response.inherited).toBeDefined();
      });

      it('should support DeleteResponse', () => {
        const response: DeleteResponse = {
          success: true,
          deleted: true,
          id: 'task-123',
          message: 'Task deleted successfully'
        };

        expect(response.deleted).toBe(true);
        expect(response.id).toBe('task-123');
        expect(response.message).toBe('Task deleted successfully');
      });

      it('should support HealthResponse', () => {
        const response: HealthResponse = {
          success: true,
          status: 'healthy',
          version: '1.0.0',
          timestamp: '2025-01-01T00:00:00Z'
        };

        expect(response.status).toBe('healthy');
        expect(response.version).toBe('1.0.0');
        expect(response.timestamp).toBe('2025-01-01T00:00:00Z');
      });

      it('should support AgentsResponse', () => {
        const response: AgentsResponse = {
          success: true,
          agents: [
            { id: 'agent-1', name: 'Agent 1' },
            { id: 'agent-2', name: 'Agent 2' }
          ],
          total: 2
        };

        expect(response.agents).toHaveLength(2);
        expect(response.total).toBe(2);
      });
    });
  });

  describe('Bulk Summary Types', () => {
    describe('BulkSummaryRequest Type', () => {
      it('should allow all optional properties', () => {
        const request: BulkSummaryRequest = {};
        expect(request).toBeDefined();
      });

      it('should support all properties', () => {
        const request: BulkSummaryRequest = {
          projectIds: ['project-1', 'project-2'],
          userId: 'user-123',
          includeArchived: true
        };

        expect(request.projectIds).toEqual(['project-1', 'project-2']);
        expect(request.userId).toBe('user-123');
        expect(request.includeArchived).toBe(true);
      });
    });

    describe('BranchSummary Type', () => {
      it('should have required properties', () => {
        const summary: BranchSummary = {
          id: 'branch-123',
          project_id: 'project-123',
          name: 'Feature Branch',
          task_count: 10,
          completed_tasks: 5,
          in_progress_tasks: 3,
          blocked_tasks: 1,
          todo_tasks: 1,
          progress_percentage: 50
        };

        expect(summary.id).toBe('branch-123');
        expect(summary.project_id).toBe('project-123');
        expect(summary.name).toBe('Feature Branch');
        expect(summary.task_count).toBe(10);
        expect(summary.completed_tasks).toBe(5);
        expect(summary.in_progress_tasks).toBe(3);
        expect(summary.blocked_tasks).toBe(1);
        expect(summary.todo_tasks).toBe(1);
        expect(summary.progress_percentage).toBe(50);
      });

      it('should allow optional properties', () => {
        const summary: BranchSummary = {
          id: 'branch-123',
          project_id: 'project-123',
          name: 'Feature Branch',
          git_branch_name: 'feature/test',
          status: 'active',
          priority: 'high',
          task_count: 10,
          completed_tasks: 5,
          in_progress_tasks: 3,
          blocked_tasks: 1,
          todo_tasks: 1,
          progress_percentage: 50,
          last_activity: '2025-01-02T00:00:00Z',
          has_urgent_tasks: true,
          is_completed: false,
          task_counts: {
            total: 10,
            by_status: {
              done: 5,
              in_progress: 3,
              blocked: 1,
              todo: 1
            }
          }
        };

        expect(summary.git_branch_name).toBe('feature/test');
        expect(summary.status).toBe('active');
        expect(summary.priority).toBe('high');
        expect(summary.last_activity).toBe('2025-01-02T00:00:00Z');
        expect(summary.has_urgent_tasks).toBe(true);
        expect(summary.is_completed).toBe(false);
        expect(summary.task_counts?.total).toBe(10);
        expect(summary.task_counts?.by_status).toBeDefined();
      });
    });

    describe('ProjectSummary Type', () => {
      it('should have required properties', () => {
        const summary: ProjectSummary = {
          id: 'project-123',
          name: 'Test Project',
          branchCount: 5,
          totalTasks: 50,
          completedTasks: 30
        };

        expect(summary.id).toBe('project-123');
        expect(summary.name).toBe('Test Project');
        expect(summary.branchCount).toBe(5);
        expect(summary.totalTasks).toBe(50);
        expect(summary.completedTasks).toBe(30);
      });

      it('should allow optional description', () => {
        const summary: ProjectSummary = {
          id: 'project-123',
          name: 'Test Project',
          description: 'Project description',
          branchCount: 5,
          totalTasks: 50,
          completedTasks: 30
        };

        expect(summary.description).toBe('Project description');
      });
    });

    describe('BulkSummaryResponse Type', () => {
      it('should have all required properties', () => {
        const response: BulkSummaryResponse = {
          success: true,
          summaries: {
            'branch-1': {
              id: 'branch-1',
              project_id: 'project-1',
              name: 'Branch 1',
              task_count: 10,
              completed_tasks: 5,
              in_progress_tasks: 3,
              blocked_tasks: 1,
              todo_tasks: 1,
              progress_percentage: 50
            }
          },
          projects: {
            'project-1': {
              id: 'project-1',
              name: 'Project 1',
              branchCount: 1,
              totalTasks: 10,
              completedTasks: 5
            }
          },
          metadata: {
            count: 1,
            queryTimeMs: 100,
            fromCache: false
          },
          timestamp: '2025-01-01T00:00:00Z'
        };

        expect(response.success).toBe(true);
        expect(response.summaries['branch-1']).toBeDefined();
        expect(response.projects['project-1']).toBeDefined();
        expect(response.metadata.count).toBe(1);
        expect(response.metadata.queryTimeMs).toBe(100);
        expect(response.metadata.fromCache).toBe(false);
        expect(response.timestamp).toBe('2025-01-01T00:00:00Z');
      });

      it('should allow optional message', () => {
        const response: BulkSummaryResponse = {
          success: false,
          summaries: {},
          projects: {},
          metadata: {
            count: 0,
            queryTimeMs: 0,
            fromCache: false
          },
          timestamp: '2025-01-01T00:00:00Z',
          message: 'No projects found'
        };

        expect(response.message).toBe('No projects found');
      });
    });

    describe('LegacyBranchResponse Type', () => {
      it('should support legacy format', () => {
        const response: LegacyBranchResponse = {
          branches: [
            {
              id: 'branch-1',
              project_id: 'project-1',
              name: 'Branch 1',
              task_count: 10,
              completed_tasks: 5,
              in_progress_tasks: 3,
              blocked_tasks: 1,
              todo_tasks: 1,
              progress_percentage: 50
            }
          ],
          project_summary: {
            id: 'project-1',
            name: 'Project 1',
            branchCount: 1,
            totalTasks: 10,
            completedTasks: 5
          },
          total_branches: 1
        };

        expect(response.branches).toHaveLength(1);
        expect(response.project_summary?.id).toBe('project-1');
        expect(response.total_branches).toBe(1);
      });
    });
  });

  describe('Type Guards and Utilities', () => {
    it('should distinguish between subtask objects and IDs', () => {
      const task1: Task = {
        id: 'task-1',
        title: 'Task 1',
        status: 'todo',
        priority: 'high',
        assignees: ['user1'],
        subtasks: ['sub-1', 'sub-2'],
        has_dependencies: false,
        has_context: false,
        git_branch_id: 'branch-123',
        project_id: 'project-123'
      };

      const task2: Task = {
        id: 'task-2',
        title: 'Task 2',
        status: 'todo',
        priority: 'high',
        assignees: ['user1'],
        subtasks: [
          {
            id: 'sub-1',
            task_id: 'task-2',
            title: 'Subtask',
            status: 'todo',
            priority: 'medium',
            assignees: ['user1']
          }
        ],
        has_dependencies: false,
        has_context: false,
        git_branch_id: 'branch-123',
        project_id: 'project-123'
      };

      // Type guard function
      const isSubtaskArray = (subtasks: Task['subtasks']): subtasks is Subtask[] => {
        return Array.isArray(subtasks) && 
          subtasks.length > 0 && 
          typeof subtasks[0] === 'object' && 
          'task_id' in subtasks[0];
      };

      const isStringArray = (subtasks: Task['subtasks']): subtasks is string[] => {
        return Array.isArray(subtasks) && 
          subtasks.length > 0 && 
          typeof subtasks[0] === 'string';
      };

      expect(isStringArray(task1.subtasks)).toBe(true);
      expect(isSubtaskArray(task1.subtasks)).toBe(false);

      expect(isStringArray(task2.subtasks)).toBe(false);
      expect(isSubtaskArray(task2.subtasks)).toBe(true);
    });

    it('should handle API response success/error states', () => {
      const isSuccessResponse = <T>(response: ApiResponse<T>): response is ApiResponse<T> & { data: T } => {
        return response.success && response.data !== undefined;
      };

      const isErrorResponse = (response: ApiResponse): response is ApiResponse & { error: string } => {
        return !response.success && response.error !== undefined;
      };

      const successResponse: ApiResponse<string> = {
        success: true,
        data: 'Success'
      };

      const errorResponse: ApiResponse = {
        success: false,
        error: 'Error occurred'
      };

      expect(isSuccessResponse(successResponse)).toBe(true);
      expect(isErrorResponse(successResponse)).toBe(false);

      expect(isSuccessResponse(errorResponse)).toBe(false);
      expect(isErrorResponse(errorResponse)).toBe(true);
    });
  });
});