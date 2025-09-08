import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, beforeEach, expect } from 'vitest';
import '@testing-library/jest-dom';
import ProjectList from '../../components/ProjectList';
import * as api from '../../api';
import * as apiLazy from '../../api-lazy';

// Mock the api modules
vi.mock('../../api');
vi.mock('../../api-lazy');

// Mock dialog components
vi.mock('../../components/BranchDetailsDialog', () => ({
  __esModule: true,
  default: ({ open, onOpenChange, project, branch }: any) => open ? (
    <div data-testid="branch-details-dialog">
      <div>Branch Details: {branch?.name}</div>
      <button onClick={() => onOpenChange(false)}>Close</button>
    </div>
  ) : null
}));

vi.mock('../../components/ProjectDetailsDialog', () => ({
  __esModule: true,
  default: ({ open, onOpenChange, project }: any) => open ? (
    <div data-testid="project-details-dialog">
      <div>Project Details: {project?.name}</div>
      <button onClick={() => onOpenChange(false)}>Close</button>
    </div>
  ) : null
}));

vi.mock('../../components/GlobalContextDialog', () => ({
  __esModule: true,
  default: ({ open, onOpenChange }: any) => open ? (
    <div data-testid="global-context-dialog">
      <div>Global Context</div>
      <button onClick={() => onOpenChange(false)}>Close</button>
    </div>
  ) : null
}));

describe('ProjectList', () => {
  const mockOnSelect = vi.fn();
  const refreshKey = 0;

  const mockProjects = [
    {
      id: 'proj-1',
      name: 'Project Alpha',
      description: 'First project',
      git_branchs: {
        'branch-1': { id: 'branch-1', name: 'main', task_count: 5 },
        'branch-2': { id: 'branch-2', name: 'feature-auth', task_count: 3 }
      }
    },
    {
      id: 'proj-2',
      name: 'Project Beta',
      description: 'Second project',
      git_branchs: {
        'branch-3': { id: 'branch-3', name: 'main', task_count: 0 }
      }
    },
    {
      id: 'proj-3',
      name: 'Empty Project',
      description: 'No branches',
      git_branchs: {}
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial Loading', () => {
    it('should show loading state initially', () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}));

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      expect(screen.getByText('Loading projects...')).toBeInTheDocument();
    });

    it('should load and display projects', async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
        expect(screen.getByText('Project Beta')).toBeInTheDocument();
        expect(screen.getByText('Empty Project')).toBeInTheDocument();
      });

      expect(api.listProjects).toHaveBeenCalled();
    });

    it('should display error state', async () => {
      const errorMessage = 'Failed to load projects';
      (api.listProjects as ReturnType<typeof vi.fn>).mockRejectedValue(new Error(errorMessage));

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
      });
    });

    it('should handle empty project list', async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('No projects found.')).toBeInTheDocument();
      });
    });
  });

  describe('Project Display', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
    });

    it('should display project information with badges', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        // Check project names
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
        
        // Check branch count badges
        expect(screen.getByText('2 branches')).toBeInTheDocument();
        expect(screen.getByText('1 branch')).toBeInTheDocument();
        
        // Check task count badges
        expect(screen.getByText('8 tasks')).toBeInTheDocument(); // 5 + 3 tasks
        // Project Beta has 0 tasks - when 0 it still shows the badge
        const zeroTasksBadges = screen.getAllByText('0 tasks');
        expect(zeroTasksBadges.length).toBeGreaterThan(0);
      });
    });

    it('should show project action buttons on hover', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Get first project element
      const projectElement = screen.getByText('Project Alpha').closest('.group');
      expect(projectElement).toBeInTheDocument();

      // Check for action buttons - Updated to match actual aria-labels
      const viewButton = screen.getAllByLabelText('View Project Details')[0];
      const branchButton = screen.getAllByLabelText('Create Branch')[0];
      const editButton = screen.getAllByLabelText('Edit')[0];
      const deleteButton = screen.getAllByLabelText('Delete')[0];

      expect(viewButton).toBeInTheDocument();
      expect(branchButton).toBeInTheDocument();
      expect(editButton).toBeInTheDocument();
      expect(deleteButton).toBeInTheDocument();
    });
  });

  describe('Project Expansion', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
    });

    it('should expand project to show branches', async () => {
      const mockBranchSummaries: apiLazy.BranchSummary[] = [
        {
          id: 'branch-1',
          name: 'main',
          description: 'Main branch',
          task_counts: {
            total: 5,
            by_status: { todo: 2, in_progress: 1, done: 2, blocked: 0 },
            by_priority: { urgent: 1, high: 1 },
            completion_percentage: 40
          },
          has_tasks: true,
          has_urgent_tasks: true,
          is_active: true,
          is_completed: false
        },
        {
          id: 'branch-2',
          name: 'feature-auth',
          description: 'Auth feature',
          task_counts: {
            total: 3,
            by_status: { todo: 1, in_progress: 1, done: 1, blocked: 0 },
            by_priority: { urgent: 0, high: 1 },
            completion_percentage: 33
          },
          has_tasks: true,
          has_urgent_tasks: false,
          is_active: true,
          is_completed: false
        }
      ];

      (apiLazy.getBranchSummaries as ReturnType<typeof vi.fn>).mockResolvedValue({
        branches: mockBranchSummaries,
        project_summary: {
          branches: { total: 2, active: 2, inactive: 0 },
          tasks: { total: 8, todo: 3, in_progress: 2, done: 3, urgent: 1 },
          completion_percentage: 37
        },
        total_branches: 2,
        cache_status: 'cached'
      });

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Click to expand project
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(screen.getByText('main')).toBeInTheDocument();
        expect(screen.getByText('feature-auth')).toBeInTheDocument();
        
        // Check task counts for branches
        const taskBadges = screen.getAllByText('5');
        expect(taskBadges.length).toBeGreaterThan(0);
        
        // Check urgent task indicator
        const urgentBadges = screen.getAllByText('!');
        expect(urgentBadges).toHaveLength(1);
      });

      expect(apiLazy.getBranchSummaries).toHaveBeenCalledWith('proj-1');
    });

    it('should show loading state when expanding project', async () => {
      let resolvePromise: any;
      const delayedPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      (apiLazy.getBranchSummaries as ReturnType<typeof vi.fn>).mockReturnValue(delayedPromise);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Click to expand
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText('Loading branches...')).toBeInTheDocument();
      });

      // Resolve the promise
      resolvePromise({
        branches: [],
        project_summary: {},
        total_branches: 0,
        cache_status: 'cached'
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading branches...')).not.toBeInTheDocument();
      });
    });

    it('should handle branch summary loading error', async () => {
      (apiLazy.getBranchSummaries as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load branches'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation();

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Click to expand
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith('Error loading branch summaries:', expect.any(Error));
      });

      consoleSpy.mockRestore();
    });

    it('should toggle project expansion', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');

      // Expand
      fireEvent.click(projectDiv!);
      await waitFor(() => {
        expect(screen.getByText('main')).toBeInTheDocument();
      });

      // Collapse
      fireEvent.click(projectDiv!);
      await waitFor(() => {
        expect(screen.queryByText('main')).not.toBeInTheDocument();
      });
    });
  });

  describe('Branch Selection', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
    });

    it('should call onSelect when branch is clicked', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Expand project
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(screen.getByText('main')).toBeInTheDocument();
      });

      // Click branch
      const branchButton = screen.getByText('main').closest('button');
      fireEvent.click(branchButton!);

      expect(mockOnSelect).toHaveBeenCalledWith('proj-1', 'branch-1');
    });

    it('should highlight selected branch', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Expand project
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(screen.getByText('main')).toBeInTheDocument();
      });

      // Click branch
      const branchButton = screen.getByText('main').closest('button');
      fireEvent.click(branchButton!);

      // Check if branch has secondary variant (selected state)
      expect(branchButton).toHaveClass('secondary');
    });
  });

  describe('Create Project', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
    });

    it('should open create project dialog', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('New')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('New'));

      await waitFor(() => {
        expect(screen.getByText('New Project')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Project name')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Description (optional)')).toBeInTheDocument();
      });
    });

    it('should create new project', async () => {
      (api.createProject as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true });

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('New')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('New'));

      const nameInput = screen.getByPlaceholderText('Project name');
      const descriptionInput = screen.getByPlaceholderText('Description (optional)');

      fireEvent.change(nameInput, { target: { value: 'New Project' } });
      fireEvent.change(descriptionInput, { target: { value: 'Project description' } });

      fireEvent.click(screen.getByText('Create'));

      await waitFor(() => {
        expect(api.createProject).toHaveBeenCalledWith({
          name: 'New Project',
          description: 'Project description'
        });
        expect(screen.queryByText('New Project')).not.toBeInTheDocument(); // Dialog closed
      });
    });

    it('should disable create button when name is empty', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('New')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('New'));

      const createButton = screen.getByText('Create');
      expect(createButton).toBeDisabled();

      const nameInput = screen.getByPlaceholderText('Project name');
      fireEvent.change(nameInput, { target: { value: 'Valid Name' } });

      expect(createButton).not.toBeDisabled();
    });
  });

  describe('Edit Project', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
    });

    it('should open edit dialog with existing values', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByLabelText('Edit');
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Edit Project')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Project Alpha')).toBeInTheDocument();
        expect(screen.getByDisplayValue('First project')).toBeInTheDocument();
      });
    });

    it('should update project', async () => {
      (api.updateProject as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true });

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByLabelText('Edit');
      fireEvent.click(editButtons[0]);

      const nameInput = screen.getByDisplayValue('Project Alpha');
      fireEvent.change(nameInput, { target: { value: 'Updated Project' } });

      fireEvent.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(api.updateProject).toHaveBeenCalledWith('proj-1', {
          name: 'Updated Project',
          description: 'First project'
        });
      });
    });
  });

  describe('Delete Project', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
    });

    it('should open delete confirmation dialog', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByLabelText('Delete');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Delete Project')).toBeInTheDocument();
        expect(screen.getByText(/Are you sure you want to delete the project/)).toBeInTheDocument();
      });
    });

    it('should delete project successfully', async () => {
      (api.deleteProject as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: true,
        message: 'Project deleted'
      });

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByLabelText('Delete');
      fireEvent.click(deleteButtons[0]);

      const confirmButton = screen.getByText('Delete');
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(api.deleteProject).toHaveBeenCalledWith('proj-1');
        expect(api.listProjects).toHaveBeenCalledTimes(2); // Initial + refresh
      });
    });

    it('should show error when delete fails', async () => {
      (api.deleteProject as ReturnType<typeof vi.fn>).mockResolvedValue({
        success: false,
        error: 'Project has active tasks'
      });

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByLabelText('Delete');
      fireEvent.click(deleteButtons[0]);

      fireEvent.click(screen.getByText('Delete'));

      await waitFor(() => {
        expect(screen.getByText('Error: Project has active tasks')).toBeInTheDocument();
      });
    });
  });

  describe('Create Branch', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
    });

    it('should open create branch dialog', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const createBranchButtons = screen.getAllByLabelText('Create Branch');
      fireEvent.click(createBranchButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('New Branch in Project Alpha')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Branch name')).toBeInTheDocument();
      });
    });

    it('should create new branch', async () => {
      (api.createBranch as ReturnType<typeof vi.fn>).mockResolvedValue({ success: true });

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const createBranchButtons = screen.getAllByLabelText('Create Branch');
      fireEvent.click(createBranchButtons[0]);

      const nameInput = screen.getByPlaceholderText('Branch name');
      const descriptionInput = screen.getByPlaceholderText('Description (optional)');

      fireEvent.change(nameInput, { target: { value: 'feature-new' } });
      fireEvent.change(descriptionInput, { target: { value: 'New feature branch' } });

      fireEvent.click(screen.getByText('Create'));

      await waitFor(() => {
        expect(api.createBranch).toHaveBeenCalledWith('proj-1', 'feature-new', 'New feature branch');
      });
    });
  });

  describe('Delete Branch', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
      (apiLazy.getBranchSummaries as ReturnType<typeof vi.fn>).mockResolvedValue({
        branches: [
          {
            id: 'branch-2',
            name: 'feature-auth',
            task_counts: { total: 3, by_status: {}, by_priority: {}, completion_percentage: 0 },
            has_tasks: true,
            has_urgent_tasks: false,
            is_active: true,
            is_completed: false
          }
        ],
        project_summary: {},
        total_branches: 1,
        cache_status: 'cached'
      });
    });

    it('should not show delete button for main branch', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Expand project
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(screen.getByText('main')).toBeInTheDocument();
      });

      // Check that main branch doesn't have delete button
      const mainBranchElement = screen.getByText('main').closest('.group');
      const deleteButtons = mainBranchElement?.querySelectorAll('[aria-label="Delete Branch"]');
      expect(deleteButtons).toHaveLength(0);
    });

    it('should show delete confirmation for non-main branches', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Expand project
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(screen.getByText('feature-auth')).toBeInTheDocument();
      });

      // Find delete button for feature branch
      const featureBranchRow = screen.getByText('feature-auth').closest('.group');
      const deleteButton = featureBranchRow?.querySelector('[aria-label="Delete Branch"]');
      fireEvent.click(deleteButton!);

      await waitFor(() => {
        expect(screen.getByText('Delete Branch')).toBeInTheDocument();
        expect(screen.getByText(/Are you sure you want to delete the branch/)).toBeInTheDocument();
        expect(screen.getByText(/Warning: This branch contains 3 task\(s\)/)).toBeInTheDocument();
      });
    });

    it('should delete branch successfully', async () => {
      (api.deleteBranch as ReturnType<typeof vi.fn>).mockResolvedValue(true);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Expand project
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(screen.getByText('feature-auth')).toBeInTheDocument();
      });

      // Delete branch
      const featureBranchRow = screen.getByText('feature-auth').closest('.group');
      const deleteButton = featureBranchRow?.querySelector('[aria-label="Delete Branch"]');
      fireEvent.click(deleteButton!);

      fireEvent.click(screen.getByText('Delete Branch'));

      await waitFor(() => {
        expect(api.deleteBranch).toHaveBeenCalledWith('proj-1', 'branch-2');
        expect(api.listProjects).toHaveBeenCalledTimes(2); // Initial + refresh
      });
    });

    it('should handle delete branch failure', async () => {
      (api.deleteBranch as ReturnType<typeof vi.fn>).mockResolvedValue(false);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Expand project
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(screen.getByText('feature-auth')).toBeInTheDocument();
      });

      // Delete branch
      const featureBranchRow = screen.getByText('feature-auth').closest('.group');
      const deleteButton = featureBranchRow?.querySelector('[aria-label="Delete Branch"]');
      fireEvent.click(deleteButton!);

      fireEvent.click(screen.getByText('Delete Branch'));

      await waitFor(() => {
        expect(screen.getByText('Error: Failed to delete branch')).toBeInTheDocument();
      });
    });
  });

  describe('Dialog Operations', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
    });

    it('should open project details dialog', async () => {
      const mockOnShowProjectDetails = vi.fn();
      render(
        <ProjectList 
          onSelect={mockOnSelect} 
          refreshKey={refreshKey} 
          onShowProjectDetails={mockOnShowProjectDetails}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const viewButtons = screen.getAllByLabelText('View Project Details');
      fireEvent.click(viewButtons[0]);

      expect(mockOnShowProjectDetails).toHaveBeenCalledWith(mockProjects[0]);
    });

    it('should open branch details dialog', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Expand project
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(screen.getByText('main')).toBeInTheDocument();
      });

      // Click branch details button
      const branchRow = screen.getByText('main').closest('.group');
      const viewButton = branchRow?.querySelector('[aria-label="View Branch Details"]');
      fireEvent.click(viewButton!);

      await waitFor(() => {
        expect(screen.getByTestId('branch-details-dialog')).toBeInTheDocument();
        expect(screen.getByText('Branch Details: main')).toBeInTheDocument();
      });
    });

    it('should open global context dialog', async () => {
      const mockOnShowGlobalContext = vi.fn();
      render(
        <ProjectList 
          onSelect={mockOnSelect} 
          refreshKey={refreshKey} 
          onShowGlobalContext={mockOnShowGlobalContext}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Global')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Global'));

      expect(mockOnShowGlobalContext).toHaveBeenCalled();
    });
  });

  describe('Refresh Functionality', () => {
    it('should refresh when refreshKey changes', async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);

      const { rerender } = render(
        <ProjectList onSelect={mockOnSelect} refreshKey={0} />
      );

      await waitFor(() => {
        expect(api.listProjects).toHaveBeenCalledTimes(1);
      });

      // Change refresh key
      rerender(
        <ProjectList onSelect={mockOnSelect} refreshKey={1} />
      );

      await waitFor(() => {
        expect(api.listProjects).toHaveBeenCalledTimes(2);
      });
    });

    it('should refresh when refresh button is clicked', async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      const refreshButton = screen.getByRole('button', { name: /refresh/i });
      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(api.listProjects).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Task Count Extraction', () => {
    it('should extract task counts correctly', async () => {
      const projectsWithTaskCounts = [
        {
          id: 'proj-test',
          name: 'Test Project',
          description: 'Test',
          git_branchs: {
            'branch-test': { 
              id: 'branch-test', 
              name: 'test-branch',
              task_count: 10
            }
          }
        }
      ];

      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(projectsWithTaskCounts);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('10 tasks')).toBeInTheDocument();
      });
    });

    it('should handle missing task_count property', async () => {
      const projectsWithoutTaskCount = [
        {
          id: 'proj-test',
          name: 'Test Project',
          description: 'Test',
          git_branchs: {
            'branch-test': { 
              id: 'branch-test', 
              name: 'test-branch'
              // No task_count property
            }
          }
        }
      ];

      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(projectsWithoutTaskCount);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('0 tasks')).toBeInTheDocument();
      });
    });
  });

  describe('Branch Summary Features', () => {
    beforeEach(async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);
    });

    it('should display branch completion indicator', async () => {
      const completedBranch: apiLazy.BranchSummary = {
        id: 'branch-complete',
        name: 'completed-feature',
        task_counts: {
          total: 5,
          by_status: { todo: 0, in_progress: 0, done: 5, blocked: 0 },
          by_priority: { urgent: 0, high: 0 },
          completion_percentage: 100
        },
        has_tasks: true,
        has_urgent_tasks: false,
        is_active: false,
        is_completed: true
      };

      (apiLazy.getBranchSummaries as ReturnType<typeof vi.fn>).mockResolvedValue({
        branches: [completedBranch],
        project_summary: {},
        total_branches: 1,
        cache_status: 'cached'
      });

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Expand project
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        expect(screen.getByText('completed-feature')).toBeInTheDocument();
        expect(screen.getByText('✓')).toBeInTheDocument(); // Completion indicator
      });
    });

    it('should fallback to original branch data when summaries not loaded', async () => {
      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });

      // Don't mock getBranchSummaries, so it won't be loaded
      const projectDiv = screen.getByText('Project Alpha').closest('.flex.items-center.gap-2');
      fireEvent.click(projectDiv!);

      await waitFor(() => {
        // Should show original branch data
        expect(screen.getByText('main')).toBeInTheDocument();
        expect(screen.getByText('feature-auth')).toBeInTheDocument();
        expect(screen.getByText('5')).toBeInTheDocument(); // task count from original data
        expect(screen.getByText('3')).toBeInTheDocument();
      });
    });
  });

  describe('Header and Layout', () => {
    it('should display header with correct title', async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByText('DhafnckMCP Projects')).toBeInTheDocument();
      });
    });

    it('should display all header buttons', async () => {
      (api.listProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockProjects);

      render(
        <ProjectList onSelect={mockOnSelect} refreshKey={refreshKey} />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
        expect(screen.getByText('Global')).toBeInTheDocument();
        expect(screen.getByText('New')).toBeInTheDocument();
      });
    });
  });
});