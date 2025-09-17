import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { vi } from 'vitest';
import * as api from '../../api';
import { Task } from '../../api';
import TaskDetailsDialog from '../../components/TaskDetailsDialog';

// Mock the api module
vi.mock('../../api');

// Mock the context helpers
vi.mock('../../utils/contextHelpers', () => ({
  formatContextDisplay: vi.fn((contextData) => ({
    hasInfo: !!contextData,
    completionSummary: contextData?.completion_summary || null,
    completionPercentage: contextData?.completion_percentage || null,
    taskStatus: contextData?.status || null,
    testingNotes: contextData?.testing_notes || [],
    isLegacy: false
  }))
}));

// Mock ClickableAssignees component
vi.mock('../../components/ClickableAssignees', () => ({
  __esModule: true,
  default: ({ assignees, onAgentClick, variant }: any) => (
    <div data-testid="clickable-assignees">
      {assignees.map((assignee: string, index: number) => (
        <button
          key={index}
          onClick={() => onAgentClick(assignee, {})}
          className={`assignee-${variant}`}
        >
          {assignee}
        </button>
      ))}
    </div>
  )
}));

describe('TaskDetailsDialog', () => {
  const mockTask: Task = {
    id: 'task-123',
    title: 'Test Task',
    description: 'Test task description',
    status: 'in_progress',
    priority: 'high',
    git_branch_id: 'branch-123',
    context_id: 'context-123',
    created_at: '2025-08-27T10:00:00Z',
    updated_at: '2025-08-27T11:00:00Z',
    due_date: '2025-08-30T23:59:59Z',
    estimated_effort: '2 days',
    assignees: ['user1', 'user2'],
    labels: ['frontend', 'urgent'],
    dependencies: ['dep-1', 'dep-2'],
    subtasks: ['sub-1', 'sub-2'],
    details: 'Additional task details',
    context_data: {
      completion_summary: 'Task completed successfully',
      completion_percentage: 85,
      status: 'completed',
      testing_notes: ['Unit tests passed', 'Integration tests verified']
    }
  };

  const mockTaskContext = {
    data: {
      resolved_context: {
        task_data: {
          implementation_notes: 'Implementation details',
          technical_decisions: ['Used React hooks', 'Implemented lazy loading']
        },
        execution_context: {
          environment: 'development',
          tools_used: ['vite', 'vitest']
        },
        discovered_patterns: {
          performance_optimizations: ['Memoized callbacks', 'Optimized renders']
        },
        local_decisions: {
          architecture: 'component-based',
          state_management: 'hooks'
        },
        implementation_notes: {
          challenges: ['Complex state management', 'Performance optimization'],
          solutions: ['Used useCallback', 'Implemented virtual scrolling']
        },
        metadata: {
          created_at: '2025-08-27T09:00:00Z',
          updated_at: '2025-08-27T12:00:00Z',
          agent_id: 'coding-agent'
        },
        _inheritance: {
          chain: ['global', 'project', 'branch', 'task'],
          inheritance_depth: 4
        },
        inheritance_disabled: false
      }
    }
  };

  const mockOnClose = vi.fn();
  const mockOnAgentClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Dialog Rendering', () => {
    it('should not render when closed', () => {
      render(
        <TaskDetailsDialog
          open={false}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      expect(screen.queryByText('Test Task')).not.toBeInTheDocument();
    });

    it('should render dialog when open', async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });
    });

    it('should show loading state initially', () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}));
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}));

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      expect(screen.getByText('Details')).toBeInTheDocument();
      expect(screen.getByText('(Loading...)')).toBeInTheDocument();
    });
  });

  describe('Details Tab', () => {
    beforeEach(async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);
    });

    it('should display basic task information', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
        expect(screen.getByText('Test task description')).toBeInTheDocument();
        expect(screen.getByText(/Status: in progress/i)).toBeInTheDocument();
        expect(screen.getByText(/Priority: high/i)).toBeInTheDocument();
      });
    });

    it('should display task IDs and references', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('IDs and References')).toBeInTheDocument();
        expect(screen.getByText('task-123')).toBeInTheDocument();
        expect(screen.getByText('branch-123')).toBeInTheDocument();
        expect(screen.getByText('context-123')).toBeInTheDocument();
      });
    });

    it('should display time information', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Time Information')).toBeInTheDocument();
        expect(screen.getByText('2 days')).toBeInTheDocument();
        expect(screen.getByText(/8\/27\/2025/)).toBeInTheDocument(); // Created date
      });
    });

    it('should display assignees with clickable functionality', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('clickable-assignees')).toBeInTheDocument();
        expect(screen.getByText('user1')).toBeInTheDocument();
        expect(screen.getByText('user2')).toBeInTheDocument();
      });

      // Test assignee click
      fireEvent.click(screen.getByText('user1'));
      expect(mockOnAgentClick).toHaveBeenCalledWith('user1', {});
    });

    it('should display labels and dependencies', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('frontend')).toBeInTheDocument();
        expect(screen.getByText('urgent')).toBeInTheDocument();
        expect(screen.getByText('Dependencies (2)')).toBeInTheDocument();
        expect(screen.getByText('dep-1')).toBeInTheDocument();
        expect(screen.getByText('dep-2')).toBeInTheDocument();
      });
    });

    it('should display subtasks summary', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Subtasks Summary')).toBeInTheDocument();
        expect(screen.getByText('Total subtasks: 2')).toBeInTheDocument();
        expect(screen.getByText('sub-1')).toBeInTheDocument();
        expect(screen.getByText('sub-2')).toBeInTheDocument();
      });
    });

    it('should display context data completion details', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Task Completion Details')).toBeInTheDocument();
        expect(screen.getByText('Task completed successfully')).toBeInTheDocument();
        expect(screen.getByText('Completion: 85%')).toBeInTheDocument();
      });
    });

    it('should show raw task data in collapsed section', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        const details = screen.getByText('View Complete Raw Task Data (JSON)');
        expect(details).toBeInTheDocument();
        
        // Click to expand
        fireEvent.click(details);
        
        // Check for JSON content
        expect(screen.getByText(/"id": "task-123"/)).toBeInTheDocument();
      });
    });
  });

  describe('Context Tab', () => {
    beforeEach(() => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);
    });

    it('should switch to context tab', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Context')).toBeInTheDocument();
      });

      // Click context tab
      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        expect(screen.getByText('Task Context - Complete Hierarchical View')).toBeInTheDocument();
      });
    });

    it('should display task execution details', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      // Switch to context tab
      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        expect(screen.getByText('🎯 Task Execution Details')).toBeInTheDocument();
        expect(screen.getByText('📋 Task Data')).toBeInTheDocument();
        expect(screen.getByText('⚡ Execution Context')).toBeInTheDocument();
        expect(screen.getByText('🔍 Discovered Patterns')).toBeInTheDocument();
      });
    });

    it('should display implementation notes', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        expect(screen.getByText('📝 Implementation Notes')).toBeInTheDocument();
      });
    });

    it('should display metadata and system information', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        expect(screen.getByText('📊 Metadata & System Information')).toBeInTheDocument();
        expect(screen.getByText('Created')).toBeInTheDocument();
        expect(screen.getByText('Last Updated')).toBeInTheDocument();
      });
    });

    it('should display inheritance information', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        expect(screen.getByText('🔗 Context Inheritance')).toBeInTheDocument();
        expect(screen.getByText('global → project → branch → task')).toBeInTheDocument();
        expect(screen.getByText('Inheritance Depth:')).toBeInTheDocument();
        expect(screen.getByText('4')).toBeInTheDocument();
      });
    });

    it('should provide copy JSON functionality', async () => {
      // Mock clipboard API
      const mockWriteText = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText
        }
      });

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        const copyButton = screen.getByText('Copy JSON');
        expect(copyButton).toBeInTheDocument();
        
        fireEvent.click(copyButton);
        
        expect(mockWriteText).toHaveBeenCalled();
      });

      // Check for copied state
      await waitFor(() => {
        expect(screen.getByText('Copied!')).toBeInTheDocument();
      });
    });

    it('should provide expand/collapse all functionality', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        expect(screen.getByText('Expand All')).toBeInTheDocument();
        expect(screen.getByText('Collapse All')).toBeInTheDocument();
      });

      // Test expand all
      fireEvent.click(screen.getByText('Expand All'));
      
      // Test collapse all
      fireEvent.click(screen.getByText('Collapse All'));
    });

    it('should show no context message when context is empty', async () => {
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(null);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        expect(screen.getByText('No Context Available')).toBeInTheDocument();
        expect(screen.getByText("This task doesn't have any context data yet.")).toBeInTheDocument();
      });
    });

    it('should show context loading state', () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}));

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      expect(screen.getByText('Loading context...')).toBeInTheDocument();
    });
  });

  describe('Dialog Interactions', () => {
    beforeEach(() => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);
    });

    it('should call onClose when close button is clicked', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        const closeButton = screen.getByText('Close');
        fireEvent.click(closeButton);
        
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it('should clean up data when dialog closes', async () => {
      const { rerender } = render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      // Close dialog
      rerender(
        <TaskDetailsDialog
          open={false}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      expect(screen.queryByText('Test Task')).not.toBeInTheDocument();
    });

    it('should handle tab switching correctly', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Details')).toHaveClass('text-blue-600');
        expect(screen.getByText('Context')).not.toHaveClass('text-blue-600');
      });

      // Switch to context tab
      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        expect(screen.getByText('Context')).toHaveClass('text-blue-600');
        expect(screen.getByText('Details')).not.toHaveClass('text-blue-600');
      });

      // Switch back to details tab
      fireEvent.click(screen.getByText('Details'));

      await waitFor(() => {
        expect(screen.getByText('Details')).toHaveClass('text-blue-600');
        expect(screen.getByText('Context')).not.toHaveClass('text-blue-600');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle getTask API failure gracefully', async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Task fetch failed'));
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        // Should fall back to original task
        expect(screen.getByText('Test Task')).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });

    it('should handle getTaskContext API failure gracefully', async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Context fetch failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        expect(screen.getByText('No Context Available')).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });

    it('should handle clipboard API failure gracefully', async () => {
      // Mock clipboard API failure
      const mockWriteText = vi.fn().mockRejectedValue(new Error('Clipboard failed'));
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText
        }
      });

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        const copyButton = screen.getByText('Copy JSON');
        fireEvent.click(copyButton);
        
        expect(mockWriteText).toHaveBeenCalled();
        // Should not show "Copied!" on failure
        expect(screen.queryByText('Copied!')).not.toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Nested JSON Rendering', () => {
    it('should render nested objects correctly', async () => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        // Check for expandable sections
        const taskDataSection = screen.getByText('📋 Task Data');
        fireEvent.click(taskDataSection);
        
        // Should show nested content
        expect(screen.getByText('implementation_notes')).toBeInTheDocument();
        expect(screen.getByText('technical_decisions')).toBeInTheDocument();
      });
    });

    it('should handle different data types in nested JSON', async () => {
      const contextWithDifferentTypes = {
        data: {
          resolved_context: {
            string_value: 'test string',
            number_value: 42,
            boolean_value: true,
            null_value: null,
            array_value: ['item1', 'item2'],
            date_value: '2025-08-27T10:00:00Z',
            uuid_value: '550e8400-e29b-41d4-a716-446655440000',
            metadata: {
              created_at: '2025-08-27T09:00:00Z',
              updated_at: '2025-08-27T12:00:00Z'
            }
          }
        }
      };

      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(contextWithDifferentTypes);

      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      fireEvent.click(screen.getByText('Context'));

      await waitFor(() => {
        // Check for different data types
        expect(screen.getByText('test string')).toBeInTheDocument();
        expect(screen.getByText('42')).toBeInTheDocument();
        expect(screen.getByText('true')).toBeInTheDocument();
        expect(screen.getByText('null')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      (api.getTask as ReturnType<typeof vi.fn>).mockResolvedValue(mockTask);
      (api.getTaskContext as ReturnType<typeof vi.fn>).mockResolvedValue(mockTaskContext);
    });

    it('should have proper ARIA attributes', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        // Dialog should have role="dialog"
        const dialog = screen.getByRole('dialog');
        expect(dialog).toBeInTheDocument();
        
        // Tab buttons should be properly labeled
        const detailsTab = screen.getByRole('button', { name: /details/i });
        const contextTab = screen.getByRole('button', { name: /context/i });
        
        expect(detailsTab).toBeInTheDocument();
        expect(contextTab).toBeInTheDocument();
      });
    });

    it('should support keyboard navigation', async () => {
      render(
        <TaskDetailsDialog
          open={true}
          onOpenChange={() => {}}
          task={mockTask}
          onClose={mockOnClose}
          onAgentClick={mockOnAgentClick}
        />
      );

      await waitFor(() => {
        const contextTab = screen.getByText('Context');
        
        // Simulate keyboard navigation
        contextTab.focus();
        fireEvent.keyDown(contextTab, { key: 'Enter' });
        
        expect(screen.getByText('Task Context - Complete Hierarchical View')).toBeInTheDocument();
      });
    });
  });
});