import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { SubtaskList } from '../../components/SubtaskList';
import * as api from '../../api';

// Mock API functions
vi.mock('../../api');

// Mock UI components
vi.mock('../../components/ui/badge', () => ({
  Badge: ({ children, variant, className }: any) => 
    <span className={`badge ${variant} ${className}`}>{children}</span>
}));

vi.mock('../../components/ui/button', () => ({
  Button: ({ children, onClick, disabled, size, variant, className, title }: any) => (
    <button 
      onClick={onClick} 
      disabled={disabled} 
      className={`button ${size} ${variant} ${className}`}
      title={title}
    >
      {children}
    </button>
  )
}));

vi.mock('../../components/ui/dialog', () => ({
  Dialog: ({ children, open }: any) => open ? <div className="dialog">{children}</div> : null,
  DialogContent: ({ children }: any) => <div className="dialog-content">{children}</div>,
  DialogHeader: ({ children }: any) => <div className="dialog-header">{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
  DialogFooter: ({ children }: any) => <div className="dialog-footer">{children}</div>
}));

vi.mock('../../components/ui/input', () => ({
  Input: ({ placeholder, value, onChange, disabled, autoFocus }: any) => (
    <input
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      disabled={disabled}
      autoFocus={autoFocus}
    />
  )
}));

vi.mock('../../components/ui/separator', () => ({
  Separator: () => <hr />
}));

vi.mock('../../components/ui/table', () => ({
  Table: ({ children }: any) => <table>{children}</table>,
  TableHeader: ({ children }: any) => <thead>{children}</thead>,
  TableBody: ({ children }: any) => <tbody>{children}</tbody>,
  TableRow: ({ children }: any) => <tr>{children}</tr>,
  TableHead: ({ children }: any) => <th>{children}</th>,
  TableCell: ({ children, colSpan }: any) => <td colSpan={colSpan}>{children}</td>
}));

vi.mock('../../components/ui/checkbox', () => ({
  Checkbox: ({ checked, onCheckedChange, id }: any) => (
    <input
      type="checkbox"
      id={id}
      checked={checked}
      onChange={() => onCheckedChange(!checked)}
    />
  )
}));

vi.mock('../../components/ui/refresh-button', () => ({
  RefreshButton: ({ onClick, loading, size }: any) => (
    <button onClick={onClick} disabled={loading} className={`refresh-button ${size}`}>
      {loading ? 'Loading...' : 'Refresh'}
    </button>
  )
}));

vi.mock('../../components/ClickableAssignees', () => ({
  __esModule: true,
  default: ({ assignees, onAgentClick }: any) => (
    <div className="clickable-assignees">
      {assignees.map((agent: string) => (
        <button key={agent} onClick={() => onAgentClick(agent, {})}>
          {agent}
        </button>
      ))}
    </div>
  )
}));

vi.mock('../../components/AgentResponseDialog', () => ({
  __esModule: true,
  default: ({ open, agentResponse }: any) => 
    open ? <div className="agent-response-dialog">{JSON.stringify(agentResponse)}</div> : null
}));

vi.mock('../../components/SubtaskCompleteDialog', () => ({
  __esModule: true,
  default: ({ open, subtask, onComplete }: any) => 
    open ? (
      <div className="subtask-complete-dialog">
        <button onClick={() => onComplete({ ...subtask, status: 'done' })}>
          Complete {subtask?.title}
        </button>
      </div>
    ) : null
}));

const mockSubtasks = [
  {
    id: '1',
    title: 'Test Subtask 1',
    description: 'Description 1',
    status: 'todo',
    priority: 'high',
    assignees: ['agent1', 'agent2'],
    due_date: '2025-12-31',
    created_at: '2025-08-01T10:00:00Z',
    updated_at: '2025-08-20T15:00:00Z',
    parent_task_id: 'parent-123',
    progress_percentage: 50
  },
  {
    id: '2',
    title: 'Test Subtask 2',
    description: 'Description 2',
    status: 'in_progress',
    priority: 'medium',
    assignees: [],
    due_date: null,
    created_at: '2025-08-02T10:00:00Z',
    updated_at: '2025-08-21T15:00:00Z',
    parent_task_id: 'parent-123',
    progress_percentage: 25
  }
];

const mockAgents = [
  { id: 'agent1', name: 'Test Agent 1' },
  { id: 'agent2', name: 'Test Agent 2' }
];

const mockAvailableAgents = ['@coding_agent', '@testing_agent', '@debug_agent'];

describe('SubtaskList', () => {
  const defaultProps = {
    projectId: 'project-123',
    taskTreeId: 'tree-456',
    parentTaskId: 'parent-123'
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue(mockSubtasks);
    (api.listAgents as ReturnType<typeof vi.fn>).mockResolvedValue(mockAgents);
    (api.getAvailableAgents as ReturnType<typeof vi.fn>).mockResolvedValue(mockAvailableAgents);
  });

  describe('Rendering', () => {
    it('renders loading state initially', () => {
      render(<SubtaskList {...defaultProps} />);
      expect(screen.getByText('Loading subtasks...')).toBeInTheDocument();
    });

    it('renders subtasks table after loading', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
        expect(screen.getByText('Test Subtask 2')).toBeInTheDocument();
      });
    });

    it('renders empty state when no subtasks', async () => {
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('No subtasks found.')).toBeInTheDocument();
      });
    });

    it('renders error state when API fails', async () => {
      const errorMessage = 'Failed to load subtasks';
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockRejectedValue(new Error(errorMessage));
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
      });
    });

    it('displays all subtask fields correctly', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        // Check status badges
        expect(screen.getByText('todo')).toBeInTheDocument();
        expect(screen.getByText('in progress')).toBeInTheDocument();
        
        // Check priority badges
        expect(screen.getByText('high')).toBeInTheDocument();
        expect(screen.getByText('medium')).toBeInTheDocument();
        
        // Check due date
        expect(screen.getByText('2025-12-31')).toBeInTheDocument();
        expect(screen.getByText('—')).toBeInTheDocument(); // Empty due date
      });
    });
  });

  describe('Create Subtask', () => {
    it('opens create dialog when clicking New Subtask button', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('New Subtask'));
      
      expect(screen.getByText('New Subtask')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Subtask title')).toBeInTheDocument();
    });

    it('creates new subtask with form data', async () => {
      const user = userEvent.setup();
      (api.createSubtask as ReturnType<typeof vi.fn>).mockResolvedValue({ id: '3', title: 'New Subtask' });
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('New Subtask'));
      
      const titleInput = screen.getByPlaceholderText('Subtask title');
      const descInput = screen.getByPlaceholderText('Subtask description');
      
      await user.type(titleInput, 'New Test Subtask');
      await user.type(descInput, 'New Description');
      
      const createButton = screen.getAllByText('Create')[1]; // Second one is in dialog
      fireEvent.click(createButton);
      
      await waitFor(() => {
        expect(api.createSubtask).toHaveBeenCalledWith('parent-123', {
          title: 'New Test Subtask',
          description: 'New Description',
          priority: 'medium',
          status: 'pending'
        });
      });
    });

    it('disables create button when title is empty', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText('New Subtask'));
      
      const createButton = screen.getAllByText('Create')[1];
      expect(createButton).toBeDisabled();
    });
  });

  describe('Edit Subtask', () => {
    it('opens edit dialog with subtask data', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const editButtons = screen.getAllByTitle('Edit subtask');
      fireEvent.click(editButtons[0]);
      
      const titleInput = screen.getByDisplayValue('Test Subtask 1');
      const descInput = screen.getByDisplayValue('Description 1');
      
      expect(titleInput).toBeInTheDocument();
      expect(descInput).toBeInTheDocument();
    });

    it('updates subtask with new data', async () => {
      const user = userEvent.setup();
      (api.updateSubtask as ReturnType<typeof vi.fn>).mockResolvedValue({ ...mockSubtasks[0], title: 'Updated Title' });
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const editButtons = screen.getAllByTitle('Edit subtask');
      fireEvent.click(editButtons[0]);
      
      const titleInput = screen.getByDisplayValue('Test Subtask 1');
      await user.clear(titleInput);
      await user.type(titleInput, 'Updated Title');
      
      const saveButton = screen.getByText('Save');
      fireEvent.click(saveButton);
      
      await waitFor(() => {
        expect(api.updateSubtask).toHaveBeenCalledWith('parent-123', '1', {
          title: 'Updated Title',
          description: 'Description 1',
          priority: 'high',
          status: 'todo'
        });
      });
    });
  });

  describe('Delete Subtask', () => {
    it('shows delete confirmation dialog', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const deleteButtons = screen.getAllByTitle('Delete subtask');
      fireEvent.click(deleteButtons[0]);
      
      expect(screen.getByText(/Are you sure you want to delete this subtask/)).toBeInTheDocument();
      expect(screen.getByText('Test Subtask 1', { selector: 'strong' })).toBeInTheDocument();
    });

    it('deletes subtask when confirmed', async () => {
      (api.deleteSubtask as ReturnType<typeof vi.fn>).mockResolvedValue({});
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const deleteButtons = screen.getAllByTitle('Delete subtask');
      fireEvent.click(deleteButtons[0]);
      
      const confirmButton = screen.getByText('Delete');
      fireEvent.click(confirmButton);
      
      await waitFor(() => {
        expect(api.deleteSubtask).toHaveBeenCalledWith('parent-123', '1');
      });
    });
  });

  describe('Agent Assignment', () => {
    it('opens agent assignment dialog', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const assignButtons = screen.getAllByTitle('Assign agents');
      fireEvent.click(assignButtons[0]);
      
      await waitFor(() => {
        expect(screen.getByText('Assign Agents to Subtask')).toBeInTheDocument();
        expect(screen.getByText('Subtask: Test Subtask 1')).toBeInTheDocument();
      });
    });

    it('shows existing assignees', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const assignButtons = screen.getAllByTitle('Assign agents');
      fireEvent.click(assignButtons[0]);
      
      await waitFor(() => {
        expect(screen.getByText('Currently assigned: agent1, agent2')).toBeInTheDocument();
      });
    });

    it('assigns selected agents', async () => {
      (api.updateSubtask as ReturnType<typeof vi.fn>).mockResolvedValue({ 
        ...mockSubtasks[0], 
        assignees: ['agent1', '@coding_agent'] 
      });
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const assignButtons = screen.getAllByTitle('Assign agents');
      fireEvent.click(assignButtons[0]);
      
      await waitFor(() => {
        expect(screen.getByText('Available Agents from Library')).toBeInTheDocument();
      });
      
      // Toggle selection of @coding_agent
      const codingAgentCheckbox = screen.getByLabelText('@coding_agent');
      fireEvent.click(codingAgentCheckbox);
      
      const assignButton = screen.getByText('Assign Agents');
      fireEvent.click(assignButton);
      
      await waitFor(() => {
        expect(api.updateSubtask).toHaveBeenCalledWith('parent-123', '1', {
          assignees: ['agent1', 'agent2', '@coding_agent']
        });
      });
    });

    it('filters invalid assignee data', async () => {
      const subtaskWithInvalidAssignees = {
        ...mockSubtasks[0],
        assignees: ['agent1', '[]', '', '  ', '[', ']']
      };
      
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue([subtaskWithInvalidAssignees]);
      (api.updateSubtask as ReturnType<typeof vi.fn>).mockResolvedValue({ 
        ...subtaskWithInvalidAssignees, 
        assignees: ['agent1'] 
      });
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const assignButtons = screen.getAllByTitle('Assign agents');
      fireEvent.click(assignButtons[0]);
      
      await waitFor(() => {
        const assignButton = screen.getByText('Assign Agents');
        fireEvent.click(assignButton);
      });
      
      await waitFor(() => {
        expect(api.updateSubtask).toHaveBeenCalledWith('parent-123', '1', {
          assignees: ['agent1'] // Only valid assignee
        });
      });
    });
  });

  describe('Complete Subtask', () => {
    it('shows complete button for non-completed subtasks', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getAllByTitle('Complete subtask')).toHaveLength(2);
      });
    });

    it('opens complete dialog when clicking complete button', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        const completeButtons = screen.getAllByTitle('Complete subtask');
        fireEvent.click(completeButtons[0]);
      });
      
      expect(screen.getByText('Complete Test Subtask 1')).toBeInTheDocument();
    });

    it('updates subtask status to done when completed', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        const completeButtons = screen.getAllByTitle('Complete subtask');
        fireEvent.click(completeButtons[0]);
      });
      
      const completeButton = screen.getByText('Complete Test Subtask 1');
      fireEvent.click(completeButton);
      
      await waitFor(() => {
        expect(api.listSubtasks).toHaveBeenCalledTimes(2); // Initial load + refresh
      });
    });
  });

  describe('View Details', () => {
    it('shows detailed subtask information', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const viewButtons = screen.getAllByTitle('View details');
      fireEvent.click(viewButtons[0]);
      
      expect(screen.getByText('Subtask Details - Complete Information')).toBeInTheDocument();
      expect(screen.getByText('IDs and References')).toBeInTheDocument();
      expect(screen.getByText('Time Information')).toBeInTheDocument();
      expect(screen.getByText('Progress & Assignment')).toBeInTheDocument();
    });

    it('displays progress bar correctly', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const viewButtons = screen.getAllByTitle('View details');
      fireEvent.click(viewButtons[0]);
      
      const progressText = screen.getByText('50%');
      expect(progressText).toBeInTheDocument();
    });
  });

  describe('Refresh Functionality', () => {
    it('refreshes subtask list when clicking refresh button', async () => {
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const refreshButton = screen.getByText('Refresh');
      fireEvent.click(refreshButton);
      
      await waitFor(() => {
        expect(api.listSubtasks).toHaveBeenCalledTimes(2);
      });
    });

    it('shows loading state during refresh', async () => {
      let resolvePromise: any;
      const promise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      
      (api.listSubtasks as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(mockSubtasks)
        .mockReturnValueOnce(promise);
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const refreshButton = screen.getByText('Refresh');
      fireEvent.click(refreshButton);
      
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      
      resolvePromise(mockSubtasks);
      
      await waitFor(() => {
        expect(screen.getByText('Refresh')).toBeInTheDocument();
      });
    });
  });

  describe('String Conversion Safety', () => {
    it('safely converts all displayed values to strings', async () => {
      const subtaskWithObjectValues = {
        id: '3',
        title: { value: 'Object Title' },
        description: null,
        status: undefined,
        priority: { value: 'high' },
        assignees: [],
        due_date: { value: '2025-12-31' },
        created_at: '2025-08-01T10:00:00Z',
        updated_at: '2025-08-20T15:00:00Z',
        parent_task_id: 'parent-123'
      };
      
      (api.listSubtasks as ReturnType<typeof vi.fn>).mockResolvedValue([subtaskWithObjectValues]);
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        // Should safely convert object to string
        expect(screen.getByText('[object Object]')).toBeInTheDocument();
        // Should handle undefined/null values
        expect(screen.getByText('pending')).toBeInTheDocument(); // Default status
        expect(screen.getByText('medium')).toBeInTheDocument(); // Default priority
      });
    });
  });

  describe('Error Handling', () => {
    it('handles API errors gracefully', async () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation();
      (api.listAgents as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const assignButtons = screen.getAllByTitle('Assign agents');
      fireEvent.click(assignButtons[0]);
      
      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith('Error fetching agents:', expect.any(Error));
      });
      
      consoleError.mockRestore();
    });

    it('shows error alert when agent assignment fails', async () => {
      window.alert = vi.fn();
      (api.updateSubtask as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Assignment failed'));
      
      render(<SubtaskList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Test Subtask 1')).toBeInTheDocument();
      });
      
      const assignButtons = screen.getAllByTitle('Assign agents');
      fireEvent.click(assignButtons[0]);
      
      await waitFor(() => {
        const assignButton = screen.getByText('Assign Agents');
        fireEvent.click(assignButton);
      });
      
      await waitFor(() => {
        expect(window.alert).toHaveBeenCalledWith('Failed to assign agents: Assignment failed');
      });
    });
  });
});