import {
  TaskStatus,
  TaskPriority,
  TaskSummary,
  SubtaskSummary,
  TaskListBranchSummary,
  TASKS_PER_PAGE,
  LazyTaskListProps,
  DialogType,
  ActiveDialog,
  DialogManagerState,
  TaskRowProps,
  TaskRowMobileProps,
  TaskRowDesktopProps,
  TaskRowActionsProps
} from '../../types/taskTypes';

describe('taskTypes', () => {
  describe('Type Constants and Literals', () => {
    describe('TaskStatus', () => {
      it('should accept valid task status values', () => {
        const validStatuses: TaskStatus[] = [
          'todo',
          'in_progress',
          'blocked',
          'review',
          'testing',
          'done',
          'cancelled'
        ];
        
        validStatuses.forEach(status => {
          const testStatus: TaskStatus = status;
          expect(testStatus).toBe(status);
        });
      });

      it('should enforce type safety for TaskStatus', () => {
        // @ts-expect-error - Testing invalid status
        const invalidStatus: TaskStatus = 'invalid';
        expect(() => invalidStatus).toBeDefined();
      });
    });

    describe('TaskPriority', () => {
      it('should accept valid task priority values', () => {
        const validPriorities: TaskPriority[] = [
          'low',
          'medium',
          'high',
          'urgent',
          'critical'
        ];
        
        validPriorities.forEach(priority => {
          const testPriority: TaskPriority = priority;
          expect(testPriority).toBe(priority);
        });
      });

      it('should enforce type safety for TaskPriority', () => {
        // @ts-expect-error - Testing invalid priority
        const invalidPriority: TaskPriority = 'very-high';
        expect(() => invalidPriority).toBeDefined();
      });
    });

    describe('DialogType', () => {
      it('should accept valid dialog type values', () => {
        const validDialogTypes: DialogType[] = [
          'details',
          'edit',
          'delete',
          'complete',
          'context',
          'assign',
          'agent-info',
          'subtask-details',
          'subtask-edit',
          'subtask-complete'
        ];
        
        validDialogTypes.forEach(dialogType => {
          const testDialogType: DialogType = dialogType;
          expect(testDialogType).toBe(dialogType);
        });
      });

      it('should enforce type safety for DialogType', () => {
        // @ts-expect-error - Testing invalid dialog type
        const invalidDialogType: DialogType = 'invalid-dialog';
        expect(() => invalidDialogType).toBeDefined();
      });
    });
  });

  describe('Constants', () => {
    it('should export TASKS_PER_PAGE with correct value', () => {
      expect(TASKS_PER_PAGE).toBe(20);
      expect(typeof TASKS_PER_PAGE).toBe('number');
    });
  });

  describe('Interface Structures', () => {
    describe('TaskSummary', () => {
      it('should create valid TaskSummary object with required properties', () => {
        const taskSummary: TaskSummary = {
          id: 'task-123',
          title: 'Test Task',
          status: 'in_progress',
          priority: 'high',
          subtasks: ['sub-1', 'sub-2', 'sub-3', 'sub-4', 'sub-5'],
          assignees: ['user1', 'user2'],
          has_dependencies: true,
          has_context: false
        };

        expect(taskSummary.id).toBe('task-123');
        expect(taskSummary.title).toBe('Test Task');
        expect(taskSummary.status).toBe('in_progress');
        expect(taskSummary.priority).toBe('high');
        expect(taskSummary.subtasks).toHaveLength(5);
        expect(taskSummary.assignees).toHaveLength(2);
        expect(taskSummary.has_dependencies).toBe(true);
        expect(taskSummary.has_context).toBe(false);
      });

      it('should create valid TaskSummary with all optional properties', () => {
        const taskSummary: TaskSummary = {
          id: 'task-456',
          title: 'Complete Task',
          status: 'done',
          priority: 'medium',
          subtasks: [],
          assignees: ['user1', 'user2', 'user3'],
          has_dependencies: false,
          dependencies: [],
          has_context: true,
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-02T00:00:00Z'
        };

        expect(taskSummary.assignees).toEqual(['user1', 'user2', 'user3']);
        expect(taskSummary.dependencies).toEqual([]);
        expect(taskSummary.created_at).toBe('2023-01-01T00:00:00Z');
        expect(taskSummary.updated_at).toBe('2023-01-02T00:00:00Z');
      });

      it('should enforce required properties', () => {
        // @ts-expect-error - Missing required properties
        const invalidTaskSummary: TaskSummary = {
          id: 'task-789',
          title: 'Incomplete Task'
        };
        expect(() => invalidTaskSummary).toBeDefined();
      });
    });

    describe('SubtaskSummary', () => {
      it('should create valid SubtaskSummary object with required properties', () => {
        const subtaskSummary: SubtaskSummary = {
          id: 'subtask-123',
          title: 'Test Subtask',
          status: 'todo',
          priority: 'low',
          assignees: ['user1']
        };

        expect(subtaskSummary.id).toBe('subtask-123');
        expect(subtaskSummary.title).toBe('Test Subtask');
        expect(subtaskSummary.status).toBe('todo');
        expect(subtaskSummary.priority).toBe('low');
        expect(subtaskSummary.assignees).toEqual(['user1']);
      });

      it('should create valid SubtaskSummary with all optional properties', () => {
        const subtaskSummary: SubtaskSummary = {
          id: 'subtask-456',
          title: 'Complete Subtask',
          status: 'done',
          priority: 'urgent',
          assignees: ['user1', 'user2'],
          progress_percentage: 75,
          created_at: '2023-01-01T10:00:00Z',
          updated_at: '2023-01-01T15:00:00Z'
        };

        expect(subtaskSummary.assignees).toEqual(['user1', 'user2']);
        expect(subtaskSummary.progress_percentage).toBe(75);
        expect(subtaskSummary.created_at).toBe('2023-01-01T10:00:00Z');
        expect(subtaskSummary.updated_at).toBe('2023-01-01T15:00:00Z');
      });
    });

    describe('TaskListBranchSummary', () => {
      it('should create valid TaskListBranchSummary with task_count', () => {
        const branchSummary: TaskListBranchSummary = {
          task_count: 10
        };

        expect(branchSummary.task_count).toBe(10);
      });

      it('should create valid TaskListBranchSummary with task_counts', () => {
        const branchSummary: TaskListBranchSummary = {
          task_counts: {
            total: 20,
            completed: 5,
            in_progress: 8,
            pending: 7
          }
        };

        expect(branchSummary.task_counts?.total).toBe(20);
        expect(branchSummary.task_counts?.completed).toBe(5);
        expect(branchSummary.task_counts?.in_progress).toBe(8);
        expect(branchSummary.task_counts?.pending).toBe(7);
      });

      it('should accept additional properties due to index signature', () => {
        const branchSummary: TaskListBranchSummary = {
          task_count: 15,
          custom_field: 'custom value',
          another_metric: 42
        };

        expect(branchSummary.custom_field).toBe('custom value');
        expect(branchSummary.another_metric).toBe(42);
      });

      it('should allow custom keys in task_counts due to index signature', () => {
        const branchSummary: TaskListBranchSummary = {
          task_counts: {
            total: 30,
            completed: 10,
            in_progress: 15,
            pending: 5,
            blocked: 2,
            cancelled: 3
          }
        };

        expect(branchSummary.task_counts?.blocked).toBe(2);
        expect(branchSummary.task_counts?.cancelled).toBe(3);
      });
    });

    describe('LazyTaskListProps', () => {
      it('should create valid LazyTaskListProps object', () => {
        const props: LazyTaskListProps = {
          projectId: 'proj-123',
          taskTreeId: 'tree-456'
        };

        expect(props.projectId).toBe('proj-123');
        expect(props.taskTreeId).toBe('tree-456');
        expect(props.onTasksChanged).toBeUndefined();
      });

      it('should create valid LazyTaskListProps with optional callback', () => {
        const mockCallback = jest.fn();
        const props: LazyTaskListProps = {
          projectId: 'proj-789',
          taskTreeId: 'tree-012',
          onTasksChanged: mockCallback
        };

        expect(props.onTasksChanged).toBe(mockCallback);
        
        // Test callback functionality
        props.onTasksChanged!();
        expect(mockCallback).toHaveBeenCalledTimes(1);
      });
    });

    describe('ActiveDialog', () => {
      it('should create valid ActiveDialog with null type', () => {
        const dialog: ActiveDialog = {
          type: null
        };

        expect(dialog.type).toBeNull();
        expect(dialog.taskId).toBeUndefined();
        expect(dialog.data).toBeUndefined();
      });

      it('should create valid ActiveDialog with type and optional properties', () => {
        const dialog: ActiveDialog = {
          type: 'edit',
          taskId: 'task-123',
          data: { title: 'Updated Title', priority: 'high' }
        };

        expect(dialog.type).toBe('edit');
        expect(dialog.taskId).toBe('task-123');
        expect(dialog.data).toEqual({ title: 'Updated Title', priority: 'high' });
      });

      it('should accept any data type for data property', () => {
        const stringData: ActiveDialog = {
          type: 'details',
          data: 'simple string data'
        };

        const arrayData: ActiveDialog = {
          type: 'assign',
          data: ['user1', 'user2', 'user3']
        };

        const numberData: ActiveDialog = {
          type: 'delete',
          data: 42
        };

        expect(stringData.data).toBe('simple string data');
        expect(arrayData.data).toEqual(['user1', 'user2', 'user3']);
        expect(numberData.data).toBe(42);
      });
    });

    describe('DialogManagerState', () => {
      it('should create valid DialogManagerState object', () => {
        const mockRef = { current: false };
        const state: DialogManagerState = {
          activeDialog: { type: null },
          saving: false,
          isClosingRef: mockRef
        };

        expect(state.activeDialog.type).toBeNull();
        expect(state.saving).toBe(false);
        expect(state.isClosingRef).toBe(mockRef);
        expect(state.isClosingRef.current).toBe(false);
      });

      it('should handle ref mutations correctly', () => {
        const mockRef = { current: false };
        const state: DialogManagerState = {
          activeDialog: { type: 'complete', taskId: 'task-999' },
          saving: true,
          isClosingRef: mockRef
        };

        // Simulate ref mutation
        state.isClosingRef.current = true;
        expect(state.isClosingRef.current).toBe(true);
      });
    });

    describe('TaskRowProps', () => {
      it('should create valid TaskRowProps object', () => {
        const mockToggle = jest.fn();
        const mockOpenDialog = jest.fn();
        const mockHover = jest.fn();

        const props: TaskRowProps = {
          summary: {
            id: 'task-001',
            title: 'Test Task',
            status: 'todo',
            priority: 'medium',
            subtasks: [],
            assignees: ['user1'],
            has_dependencies: false,
            has_context: true
          },
          isExpanded: false,
          isLoading: false,
          fullTask: { id: 'task-001', details: 'Full task data' },
          isHighlighted: true,
          isHovered: false,
          projectId: 'proj-001',
          taskTreeId: 'tree-001',
          isMobile: false,
          onToggleExpansion: mockToggle,
          onOpenDialog: mockOpenDialog,
          onHover: mockHover
        };

        expect(props.summary.id).toBe('task-001');
        expect(props.isExpanded).toBe(false);
        expect(props.isLoading).toBe(false);
        expect(props.fullTask).toEqual({ id: 'task-001', details: 'Full task data' });
        expect(props.isHighlighted).toBe(true);
        expect(props.isHovered).toBe(false);
        expect(props.projectId).toBe('proj-001');
        expect(props.taskTreeId).toBe('tree-001');
        expect(props.isMobile).toBe(false);

        // Test callbacks
        props.onToggleExpansion();
        expect(mockToggle).toHaveBeenCalledTimes(1);

        props.onOpenDialog('edit', 'task-001', { extra: 'data' });
        expect(mockOpenDialog).toHaveBeenCalledWith('edit', 'task-001', { extra: 'data' });

        props.onHover('task-001');
        expect(mockHover).toHaveBeenCalledWith('task-001');
        
        props.onHover(null);
        expect(mockHover).toHaveBeenCalledWith(null);
      });

      it('should accept any type for fullTask property', () => {
        const props: TaskRowProps = {
          summary: {
            id: 'task-002',
            title: 'Another Task',
            status: 'done',
            priority: 'low',
            subtasks: ['sub-1', 'sub-2'],
            assignees: [],
            has_dependencies: true,
            has_context: false
          },
          isExpanded: true,
          isLoading: true,
          fullTask: null, // Can be null
          isHighlighted: false,
          isHovered: true,
          projectId: 'proj-002',
          taskTreeId: 'tree-002',
          isMobile: true,
          onToggleExpansion: () => {},
          onOpenDialog: () => {},
          onHover: () => {}
        };

        expect(props.fullTask).toBeNull();

        // Can also be complex object
        const complexProps: TaskRowProps = {
          ...props,
          fullTask: {
            id: 'task-002',
            title: 'Another Task',
            description: 'Detailed description',
            subtasks: [{ id: 'sub-1' }, { id: 'sub-2' }],
            metadata: { created_by: 'user123', tags: ['urgent', 'backend'] }
          }
        };

        expect(complexProps.fullTask.subtasks).toHaveLength(2);
        expect(complexProps.fullTask.metadata.tags).toContain('urgent');
      });
    });

    describe('TaskRowMobileProps', () => {
      it('should create valid TaskRowMobileProps object', () => {
        const mockRef = { current: null };
        const props: TaskRowMobileProps = {
          summary: {
            id: 'task-mob-001',
            title: 'Mobile Task',
            status: 'in_progress',
            priority: 'high',
            subtasks: ['sub-1', 'sub-2', 'sub-3'],
            assignees: ['user1', 'user2'],
            has_dependencies: false,
            has_context: true
          },
          fullTask: { mobile: true, data: 'mobile specific' },
          isHighlighted: false,
          isHovered: true,
          isExpanded: true,
          isLoading: false,
          projectId: 'proj-mob-001',
          taskTreeId: 'tree-mob-001',
          onToggleExpansion: jest.fn(),
          onOpenDialog: jest.fn(),
          onHover: jest.fn(),
          elementRef: mockRef
        };

        expect(props.summary.id).toBe('task-mob-001');
        expect(props.fullTask).toEqual({ mobile: true, data: 'mobile specific' });
        expect(props.isExpanded).toBe(true);
        expect(props.elementRef).toBe(mockRef);
        expect(props.animationClass).toBeUndefined();
      });

      it('should create valid TaskRowMobileProps with animation class', () => {
        const mockRef = { current: document.createElement('div') };
        const props: TaskRowMobileProps = {
          summary: {
            id: 'task-mob-002',
            title: 'Animated Mobile Task',
            status: 'done',
            priority: 'critical',
            subtasks: [],
            assignees: ['user1'],
            has_dependencies: true,
            has_context: false
          },
          fullTask: {},
          isHighlighted: true,
          isHovered: false,
          isExpanded: false,
          isLoading: true,
          projectId: 'proj-mob-002',
          taskTreeId: 'tree-mob-002',
          onToggleExpansion: () => {},
          onOpenDialog: () => {},
          onHover: () => {},
          elementRef: mockRef,
          animationClass: 'fade-in-slide'
        };

        expect(props.animationClass).toBe('fade-in-slide');
        expect(props.elementRef.current).toBeInstanceOf(HTMLDivElement);
      });
    });

    describe('TaskRowDesktopProps', () => {
      it('should create valid TaskRowDesktopProps object', () => {
        const mockRef = { current: null };
        const props: TaskRowDesktopProps = {
          summary: {
            id: 'task-desk-001',
            title: 'Desktop Task',
            status: 'blocked',
            priority: 'medium',
            subtasks: ['sub-1', 'sub-2', 'sub-3', 'sub-4', 'sub-5'],
            assignees: ['user1', 'user2', 'user3'],
            has_dependencies: true,
            has_context: true
          },
          fullTask: { desktop: true, features: ['drag', 'drop'] },
          isHighlighted: true,
          isHovered: true,
          isExpanded: false,
          isLoading: false,
          projectId: 'proj-desk-001',
          taskTreeId: 'tree-desk-001',
          onToggleExpansion: jest.fn(),
          onOpenDialog: jest.fn(),
          onHover: jest.fn(),
          elementRef: mockRef
        };

        expect(props.summary.id).toBe('task-desk-001');
        expect(props.fullTask.desktop).toBe(true);
        expect(props.fullTask.features).toEqual(['drag', 'drop']);
        expect(props.elementRef).toBe(mockRef);
        expect(props.animationClass).toBeUndefined();
      });

      it('should create valid TaskRowDesktopProps with table row element', () => {
        const tableRow = document.createElement('tr');
        const mockRef = { current: tableRow };
        
        const props: TaskRowDesktopProps = {
          summary: {
            id: 'task-desk-002',
            title: 'Table Row Task',
            status: 'review',
            priority: 'urgent',
            subtasks: ['sub-1'],
            assignees: ['reviewer'],
            has_dependencies: false,
            has_context: true,
            created_at: '2023-01-01T00:00:00Z'
          },
          fullTask: null,
          isHighlighted: false,
          isHovered: false,
          isExpanded: true,
          isLoading: true,
          projectId: 'proj-desk-002',
          taskTreeId: 'tree-desk-002',
          onToggleExpansion: () => {},
          onOpenDialog: () => {},
          onHover: () => {},
          elementRef: mockRef,
          animationClass: 'slide-down'
        };

        expect(props.elementRef.current).toBeInstanceOf(HTMLTableRowElement);
        expect(props.animationClass).toBe('slide-down');
      });
    });

    describe('TaskRowActionsProps', () => {
      it('should create valid TaskRowActionsProps with default variant', () => {
        const mockOpenDialog = jest.fn();
        const props: TaskRowActionsProps = {
          taskId: 'task-action-001',
          projectId: 'proj-action-001',
          taskTreeId: 'tree-action-001',
          onOpenDialog: mockOpenDialog
        };

        expect(props.taskId).toBe('task-action-001');
        expect(props.projectId).toBe('proj-action-001');
        expect(props.taskTreeId).toBe('tree-action-001');
        expect(props.variant).toBeUndefined();
        expect(props.onOpenDialog).toBe(mockOpenDialog);
      });

      it('should create valid TaskRowActionsProps with mobile variant', () => {
        const mockOpenDialog = jest.fn();
        const props: TaskRowActionsProps = {
          taskId: 'task-action-002',
          projectId: 'proj-action-002',
          taskTreeId: 'tree-action-002',
          onOpenDialog: mockOpenDialog,
          variant: 'mobile'
        };

        expect(props.variant).toBe('mobile');
      });

      it('should create valid TaskRowActionsProps with desktop variant', () => {
        const mockOpenDialog = jest.fn();
        const props: TaskRowActionsProps = {
          taskId: 'task-action-003',
          projectId: 'proj-action-003',
          taskTreeId: 'tree-action-003',
          onOpenDialog: mockOpenDialog,
          variant: 'desktop'
        };

        expect(props.variant).toBe('desktop');
      });

      it('should enforce variant type safety', () => {
        const props: TaskRowActionsProps = {
          taskId: 'task-action-004',
          projectId: 'proj-action-004',
          taskTreeId: 'tree-action-004',
          onOpenDialog: () => {},
          // @ts-expect-error - Testing invalid variant
          variant: 'tablet'
        };

        expect(() => props).toBeDefined();
      });
    });
  });

  describe('Edge Cases and Type Safety', () => {
    it('should handle empty arrays for assignees', () => {
      const taskSummary: TaskSummary = {
        id: 'task-edge-001',
        title: 'No Assignees Task',
        status: 'todo',
        priority: 'low',
        subtasks: [],
        assignees: [],
        has_dependencies: false,
        has_context: false
      };

      expect(taskSummary.assignees).toEqual([]);
      expect(taskSummary.subtasks).toEqual([]);
    });

    it('should handle undefined optional properties correctly', () => {
      const subtask: SubtaskSummary = {
        id: 'subtask-edge-001',
        title: 'Minimal Subtask',
        status: 'todo',
        priority: 'low',
        assignees: []
      };

      expect(subtask.assignees).toBeUndefined();
      expect(subtask.progress_percentage).toBeUndefined();
      expect(subtask.created_at).toBeUndefined();
      expect(subtask.updated_at).toBeUndefined();
    });

    it('should handle mixed data types in dialog data property', () => {
      const dialogWithBoolean: ActiveDialog = {
        type: 'complete',
        data: true
      };

      const dialogWithNull: ActiveDialog = {
        type: 'delete',
        data: null
      };

      const dialogWithUndefined: ActiveDialog = {
        type: 'edit',
        data: undefined
      };

      const dialogWithComplexObject: ActiveDialog = {
        type: 'context',
        data: {
          nested: {
            deep: {
              value: 'deeply nested',
              array: [1, 2, 3]
            }
          }
        }
      };

      expect(dialogWithBoolean.data).toBe(true);
      expect(dialogWithNull.data).toBe(null);
      expect(dialogWithUndefined.data).toBe(undefined);
      expect(dialogWithComplexObject.data.nested.deep.value).toBe('deeply nested');
    });

    it('should handle boundary values for numeric properties', () => {
      const taskWithZeroCounts: TaskSummary = {
        id: 'task-boundary-001',
        title: 'Zero Counts Task',
        status: 'done',
        priority: 'low',
        subtasks: [],
        assignees: [],
        has_dependencies: false,
        dependencies: [],
        has_context: false
      };

      const taskWithLargeCounts: TaskSummary = {
        id: 'task-boundary-002',
        title: 'Large Counts Task',
        status: 'in_progress',
        priority: 'critical',
        subtasks: new Array(999999).fill('sub'),
        assignees: new Array(100).fill('user'),
        has_dependencies: true,
        dependencies: new Array(50).fill('dep'),
        has_context: true
      };

      expect(taskWithZeroCounts.subtasks).toHaveLength(0);
      expect(taskWithZeroCounts.dependencies).toHaveLength(0);
      expect(taskWithLargeCounts.subtasks).toHaveLength(999999);
      expect(taskWithLargeCounts.assignees).toHaveLength(100);
    });

    it('should handle progress percentage boundary values', () => {
      const subtaskAtStart: SubtaskSummary = {
        id: 'subtask-progress-001',
        title: 'Just Started',
        status: 'in_progress',
        priority: 'medium',
        assignees: ['user1'],
        progress_percentage: 0
      };

      const subtaskInProgress: SubtaskSummary = {
        id: 'subtask-progress-002',
        title: 'Half Done',
        status: 'in_progress',
        priority: 'medium',
        assignees: ['user1'],
        progress_percentage: 50
      };

      const subtaskComplete: SubtaskSummary = {
        id: 'subtask-progress-003',
        title: 'Fully Complete',
        status: 'done',
        priority: 'medium',
        assignees: ['user1'],
        progress_percentage: 100
      };

      expect(subtaskAtStart.progress_percentage).toBe(0);
      expect(subtaskInProgress.progress_percentage).toBe(50);
      expect(subtaskComplete.progress_percentage).toBe(100);
    });
  });
});