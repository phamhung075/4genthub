import React from 'react';
import { render, screen, waitFor, fireEvent } from './../../test-utils';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import ProjectList from '../../../components/ProjectList/ProjectList';
import { ProjectListProps } from '../../../types';
import { AuthContext } from '../../../contexts/AuthContext';

/**
 * The container no longer uses a `useProjectData` hook. It is composed from
 * several focused hooks (React Query data hooks + dialog/animation hooks).
 * We expose their return values through a hoisted state object so each test
 * can control them without re-declaring the mocks per test.
 */
const hookState = vi.hoisted(() => ({
  projects: [] as Array<{ id: string; name: string; description?: string }>,
  projectsLoading: false,
  refetchProjects: vi.fn().mockResolvedValue(undefined),
  summaries: [] as Array<Record<string, unknown>>,
  summariesLoading: false,
  summariesError: null as string | null,
  refreshSummaries: vi.fn().mockResolvedValue(undefined),
  createProjectAsync: vi.fn().mockResolvedValue(undefined),
  updateProjectAsync: vi.fn().mockResolvedValue(undefined),
  deleteProjectAsync: vi.fn().mockResolvedValue(undefined),
  createBranchAsync: vi.fn().mockResolvedValue(undefined),
  deleteBranchAsync: vi.fn().mockResolvedValue(undefined),
  useWebSocket: vi.fn(() => ({ isConnected: true, client: null, disconnect: vi.fn() })),
  dialogs: {
    showCreate: false,
    showEdit: null as { id: string; name: string; description?: string } | null,
    showDelete: null as { id: string; name: string; description?: string } | null,
    showCreateBranch: null as { id: string; name: string } | null,
    showDeleteBranch: null as { project: { id: string; name: string }; branch: { id: string; name: string } } | null,
    form: { name: '', description: '' },
    saving: false,
    setSaving: vi.fn(),
    openCreateDialog: vi.fn(),
    openEditDialog: vi.fn(),
    openDeleteDialog: vi.fn(),
    openCreateBranchDialog: vi.fn(),
    openDeleteBranchDialog: vi.fn(),
    closeDialog: vi.fn(),
    setForm: vi.fn(),
  },
  animatingCounts: new Map<string, 'up' | 'down'>(),
}));

// The hooks the component actually consumes
vi.mock('../../../hooks/useWebSocketV2', () => ({
  useWebSocket: hookState.useWebSocket
}));

vi.mock('../../../hooks/useRealtimeSync', () => ({
  useRealtimeSync: vi.fn()
}));

vi.mock('../../../components/ProjectList/hooks', () => ({
  useProjectDialogs: () => hookState.dialogs,
  useProjectAnimations: () => ({ animatingCounts: hookState.animatingCounts })
}));

vi.mock('../../../hooks/useProjects', () => ({
  useProjects: () => ({
    data: hookState.projects,
    isLoading: hookState.projectsLoading,
    refetch: hookState.refetchProjects
  }),
  useProjectMutations: () => ({
    createProjectAsync: hookState.createProjectAsync,
    updateProjectAsync: hookState.updateProjectAsync,
    deleteProjectAsync: hookState.deleteProjectAsync
  })
}));

vi.mock('../../../hooks/useBranchSummaries', () => ({
  useBranchSummaries: () => ({
    summaries: hookState.summaries,
    projects: [],
    loading: hookState.summariesLoading,
    error: hookState.summariesError,
    refresh: hookState.refreshSummaries,
    forceRefresh: hookState.refreshSummaries,
    refreshing: false,
    removeBranchOptimistically: vi.fn(),
    addBranchOptimistically: vi.fn()
  })
}));

vi.mock('../../../hooks/useBranches', () => ({
  useBranchMutations: () => ({
    createBranchAsync: hookState.createBranchAsync,
    deleteBranchAsync: hookState.deleteBranchAsync
  })
}));

// Mock the presentational children so we test the container in isolation
vi.mock('../../../components/ProjectList/components', () => ({
  ProjectListHeader: ({ onCreateProject, onRefresh, onShowGlobalContext, loadingBulkSummaries, isConnected }) => (
    <div data-testid="project-list-header" data-connected={String(isConnected)}>
      <button onClick={onCreateProject} data-testid="create-project-btn">Create Project</button>
      <button onClick={onRefresh} data-testid="refresh-btn">Refresh</button>
      <button onClick={onShowGlobalContext} data-testid="global-context-btn">Global Context</button>
      {loadingBulkSummaries && <span data-testid="bulk-summaries-loading">Loading branch summaries...</span>}
    </div>
  ),
  ProjectListContent: ({ projects, selected, openProjects, onSelectBranch, onToggleProject }) => (
    <div data-testid="project-list-content" data-selected={selected ?? ''}>
      {projects.map((project: { id: string; name: string }) => (
        <div
          key={project.id}
          data-testid={`project-${project.id}`}
          data-open={String(Boolean(openProjects && openProjects[project.id]))}
        >
          <button onClick={() => onToggleProject(project.id)} data-testid={`toggle-${project.id}`}>
            {project.name}
          </button>
          <button onClick={() => onSelectBranch(project.id, 'branch-1')} data-testid={`select-${project.id}`}>
            Select
          </button>
        </div>
      ))}
    </div>
  ),
  ProjectDialogs: ({ onDeleteBranch, onFormChange, onCreateProject }) => (
    <div data-testid="project-dialogs">
      <button data-testid="delete-branch-submit" onClick={() => onDeleteBranch && onDeleteBranch()}>Delete Branch</button>
      <button
        data-testid="form-change-submit"
        onClick={() => onFormChange && onFormChange({ target: { value: 'New' } }, 'name')}
      >
        Change Form
      </button>
      <button data-testid="create-project-submit" onClick={() => onCreateProject && onCreateProject()}>Submit Create</button>
    </div>
  )
}));

// Mock auth context
const mockAuthContext = {
  user: { id: 'user-123' },
  tokens: { access_token: 'test-token' },
  login: vi.fn(),
  logout: vi.fn(),
  refreshTokens: vi.fn(),
  isAuthenticated: true
};

describe('ProjectList Component', () => {
  const mockOnSelect = vi.fn();
  const mockOnShowGlobalContext = vi.fn();
  const mockOnShowProjectDetails = vi.fn();
  const mockOnShowBranchDetails = vi.fn();

  const defaultProps: ProjectListProps = {
    onSelect: mockOnSelect,
    selectedProjectId: undefined,
    selectedBranchId: undefined,
    onShowGlobalContext: mockOnShowGlobalContext,
    onShowProjectDetails: mockOnShowProjectDetails,
    onShowBranchDetails: mockOnShowBranchDetails
  };

  const mockProjects = [
    { id: 'proj-1', name: 'Project 1', description: 'Description 1' },
    { id: 'proj-2', name: 'Project 2', description: 'Description 2' }
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    hookState.projects = [...mockProjects];
    hookState.projectsLoading = false;
    hookState.summaries = [];
    hookState.summariesLoading = false;
    hookState.summariesError = null;
    hookState.animatingCounts = new Map();

    hookState.dialogs.showCreate = false;
    hookState.dialogs.showEdit = null;
    hookState.dialogs.showDelete = null;
    hookState.dialogs.showCreateBranch = null;
    hookState.dialogs.showDeleteBranch = null;
    hookState.dialogs.form = { name: '', description: '' };
    hookState.dialogs.saving = false;
  });

  const renderComponent = (props = {}) => {
    return render(
      <AuthContext.Provider value={mockAuthContext}>
        <ProjectList {...defaultProps} {...props} />
      </AuthContext.Provider>
    );
  };

  describe('Rendering', () => {
    it('should render project list with header and content', () => {
      renderComponent();

      expect(screen.getByTestId('project-list-header')).toBeInTheDocument();
      expect(screen.getByTestId('project-list-content')).toBeInTheDocument();
      expect(screen.getByTestId('project-dialogs')).toBeInTheDocument();
    });

    it('should render loading state when loading projects', () => {
      hookState.projectsLoading = true;
      hookState.projects = [];

      renderComponent();

      expect(screen.getByText('Loading projects...')).toBeInTheDocument();
    });

    it('should render loading state when loading bulk summaries', () => {
      hookState.summariesLoading = true;

      renderComponent();

      expect(screen.getByTestId('bulk-summaries-loading')).toBeInTheDocument();
    });

    it('should render error state when there is an error', () => {
      const errorMessage = 'Failed to load projects';
      hookState.summariesError = errorMessage;

      renderComponent();

      expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
    });

    it('should render projects when data is loaded', () => {
      renderComponent();

      expect(screen.getByTestId('project-proj-1')).toBeInTheDocument();
      expect(screen.getByTestId('project-proj-2')).toBeInTheDocument();
    });
  });

  describe('Selection State', () => {
    it('should derive selected state from props', () => {
      renderComponent({
        selectedProjectId: 'proj-1',
        selectedBranchId: 'branch-1'
      });

      // The derived selection is passed down to ProjectListContent
      expect(screen.getByTestId('project-list-content')).toHaveAttribute('data-selected', 'proj-1:branch-1');
    });

    it('should handle onSelect callback when branch is selected', () => {
      renderComponent();

      const selectButton = screen.getByTestId('select-proj-1');
      fireEvent.click(selectButton);

      expect(mockOnSelect).toHaveBeenCalledWith('proj-1', 'branch-1');
    });
  });

  describe('Project Expansion', () => {
    it('should toggle project expansion when clicked', () => {
      renderComponent();

      expect(screen.getByTestId('project-proj-1')).toHaveAttribute('data-open', 'false');

      const toggleButton = screen.getByTestId('toggle-proj-1');
      fireEvent.click(toggleButton);

      // Verify the toggle was applied to the open state
      expect(screen.getByTestId('project-proj-1')).toHaveAttribute('data-open', 'true');
    });

    it('should auto-expand selected project on mount', async () => {
      renderComponent({
        selectedProjectId: 'proj-1',
        selectedBranchId: 'branch-1'
      });

      await waitFor(() => {
        // The project should be expanded automatically
        expect(screen.getByTestId('project-proj-1')).toHaveAttribute('data-open', 'true');
      });
    });
  });

  describe('CRUD Operations', () => {
    it('should handle create project', async () => {
      renderComponent();

      const createButton = screen.getByTestId('create-project-btn');
      fireEvent.click(createButton);

      expect(hookState.dialogs.openCreateDialog).toHaveBeenCalled();
    });

    it('should handle refresh', () => {
      renderComponent();

      const refreshButton = screen.getByTestId('refresh-btn');
      fireEvent.click(refreshButton);

      expect(hookState.refetchProjects).toHaveBeenCalled();
      expect(hookState.refreshSummaries).toHaveBeenCalled();
    });

    it('should handle show global context', () => {
      renderComponent();

      const globalContextButton = screen.getByTestId('global-context-btn');
      fireEvent.click(globalContextButton);

      expect(mockOnShowGlobalContext).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle create project error gracefully', async () => {
      hookState.createProjectAsync.mockRejectedValueOnce(new Error('Create failed'));

      renderComponent();

      fireEvent.click(screen.getByTestId('create-project-submit'));

      // The error is caught by the wrapper and surfaced through the error state
      await waitFor(() => {
        expect(screen.getByText('Error: Create failed')).toBeInTheDocument();
      });
    });
  });

  describe('WebSocket Integration', () => {
    it('should connect to WebSocket with user credentials', () => {
      renderComponent();

      expect(hookState.useWebSocket).toHaveBeenCalledWith('user-123', 'test-token');
    });

    it('should pass WebSocket connection status to header', () => {
      renderComponent();

      expect(screen.getByTestId('project-list-header')).toHaveAttribute('data-connected', 'true');
    });
  });

  describe('Dialog Management', () => {
    it('should handle form changes', () => {
      renderComponent();

      fireEvent.click(screen.getByTestId('form-change-submit'));

      // The container forwards form changes to the dialogs hook
      expect(hookState.dialogs.setForm).toHaveBeenCalled();
    });
  });

  describe('Animation States', () => {
    it('should handle delete branch with animations', async () => {
      hookState.dialogs.showDeleteBranch = {
        project: { id: 'proj-1', name: 'Project 1' },
        branch: { id: 'branch-1', name: 'Branch 1' }
      };

      renderComponent();

      fireEvent.click(screen.getByTestId('delete-branch-submit'));

      await waitFor(() => {
        expect(hookState.deleteBranchAsync).toHaveBeenCalledWith('branch-1');
        expect(hookState.dialogs.closeDialog).toHaveBeenCalledWith('deleteBranch');
      });
    });
  });

  describe('Empty State', () => {
    it('should render empty state when no projects', () => {
      hookState.projects = [];

      renderComponent();

      // Should still render header and content area
      expect(screen.getByTestId('project-list-header')).toBeInTheDocument();
      expect(screen.getByTestId('project-list-content')).toBeInTheDocument();
    });
  });
});
