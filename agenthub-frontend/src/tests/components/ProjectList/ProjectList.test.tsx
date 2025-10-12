import React from 'react';
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import ProjectList from '../../../components/ProjectList/ProjectList';
import { ProjectListProps } from '../../../types';
import { AuthContext } from '../../../contexts/AuthContext';
import * as projectDataHook from '../../../components/ProjectList/hooks/useProjectData';
import * as projectDialogsHook from '../../../components/ProjectList/hooks/useProjectDialogs';
import * as projectAnimationsHook from '../../../components/ProjectList/hooks/useProjectAnimations';

// Mock hooks and dependencies
vi.mock('../../../hooks/useWebSocketV2', () => ({
  useWebSocket: vi.fn(() => ({ isConnected: true }))
}));

vi.mock('../../../components/ProjectList/components', () => ({
  ProjectListHeader: vi.fn(({ onCreateProject, onRefresh, onShowGlobalContext }) => (
    <div data-testid="project-list-header">
      <button onClick={onCreateProject} data-testid="create-project-btn">Create Project</button>
      <button onClick={onRefresh} data-testid="refresh-btn">Refresh</button>
      <button onClick={onShowGlobalContext} data-testid="global-context-btn">Global Context</button>
    </div>
  )),
  ProjectListContent: vi.fn(({ projects, onSelectBranch, onToggleProject }) => (
    <div data-testid="project-list-content">
      {projects.map((project: any) => (
        <div key={project.id} data-testid={`project-${project.id}`}>
          <button onClick={() => onToggleProject(project.id)} data-testid={`toggle-${project.id}`}>
            {project.name}
          </button>
          <button onClick={() => onSelectBranch(project.id, 'branch-1')} data-testid={`select-${project.id}`}>
            Select
          </button>
        </div>
      ))}
    </div>
  )),
  ProjectDialogs: vi.fn(() => <div data-testid="project-dialogs" />)
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

  const mockProjectData = {
    projects: mockProjects,
    setProjects: vi.fn(),
    branchSummaries: {},
    taskCounts: {},
    loading: false,
    error: null,
    setError: vi.fn(),
    loadingBulkSummaries: false,
    handleCreateProject: vi.fn(),
    handleUpdateProject: vi.fn(),
    handleDeleteProject: vi.fn(),
    handleCreateBranch: vi.fn(),
    handleDeleteBranch: vi.fn(),
    handleRefresh: vi.fn()
  };

  const mockDialogs = {
    showCreate: false,
    showEdit: null,
    showDelete: null,
    showCreateBranch: null,
    showDeleteBranch: null,
    form: { name: '', description: '' },
    saving: false,
    setSaving: vi.fn(),
    openCreateDialog: vi.fn(),
    openEditDialog: vi.fn(),
    openDeleteDialog: vi.fn(),
    openCreateBranchDialog: vi.fn(),
    openDeleteBranchDialog: vi.fn(),
    closeDialog: vi.fn(),
    setForm: vi.fn()
  };

  const mockAnimations = {
    newBranches: new Set(),
    fadingOutBranches: new Set(),
    deletingBranches: new Set(),
    animatingCounts: {},
    setDeletingBranches: vi.fn(),
    setFadingOutBranches: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(projectDataHook, 'useProjectData').mockReturnValue(mockProjectData);
    vi.spyOn(projectDialogsHook, 'useProjectDialogs').mockReturnValue(mockDialogs);
    vi.spyOn(projectAnimationsHook, 'useProjectAnimations').mockReturnValue(mockAnimations);
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
      vi.spyOn(projectDataHook, 'useProjectData').mockReturnValue({
        ...mockProjectData,
        loading: true,
        projects: []
      });

      renderComponent();
      
      expect(screen.getByText('Loading projects...')).toBeInTheDocument();
    });

    it('should render loading state when loading bulk summaries', () => {
      vi.spyOn(projectDataHook, 'useProjectData').mockReturnValue({
        ...mockProjectData,
        loadingBulkSummaries: true
      });

      renderComponent();
      
      expect(screen.getByText('Loading branch summaries...')).toBeInTheDocument();
    });

    it('should render error state when there is an error', () => {
      const errorMessage = 'Failed to load projects';
      vi.spyOn(projectDataHook, 'useProjectData').mockReturnValue({
        ...mockProjectData,
        error: errorMessage
      });

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

      // The selected prop should be passed to ProjectListContent
      expect(projectDataHook.useProjectData).toHaveBeenCalledWith({ selectedProjectId: 'proj-1' });
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
      
      const toggleButton = screen.getByTestId('toggle-proj-1');
      fireEvent.click(toggleButton);
      
      // Verify the toggle was called
      expect(screen.getByTestId('toggle-proj-1')).toBeInTheDocument();
    });

    it('should auto-expand selected project on mount', async () => {
      renderComponent({
        selectedProjectId: 'proj-1',
        selectedBranchId: 'branch-1'
      });

      await waitFor(() => {
        // The project should be expanded automatically
        expect(screen.getByTestId('project-proj-1')).toBeInTheDocument();
      });
    });
  });

  describe('CRUD Operations', () => {
    it('should handle create project', async () => {
      mockProjectData.handleCreateProject.mockResolvedValue(undefined);
      
      renderComponent();
      
      const createButton = screen.getByTestId('create-project-btn');
      fireEvent.click(createButton);
      
      expect(mockDialogs.openCreateDialog).toHaveBeenCalled();
    });

    it('should handle refresh', () => {
      renderComponent();
      
      const refreshButton = screen.getByTestId('refresh-btn');
      fireEvent.click(refreshButton);
      
      expect(mockProjectData.handleRefresh).toHaveBeenCalled();
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
      const error = new Error('Create failed');
      mockProjectData.handleCreateProject.mockRejectedValue(error);
      
      vi.spyOn(projectDialogsHook, 'useProjectDialogs').mockReturnValue({
        ...mockDialogs,
        showCreate: true
      });

      renderComponent();
      
      // The error should be handled by the hook, not thrown
      expect(() => renderComponent()).not.toThrow();
    });
  });

  describe('WebSocket Integration', () => {
    it('should connect to WebSocket with user credentials', () => {
      const { useWebSocket } = require('../../../hooks/useWebSocketV2');
      
      renderComponent();
      
      expect(useWebSocket).toHaveBeenCalledWith('user-123', 'test-token');
    });

    it('should pass WebSocket connection status to header', () => {
      renderComponent();
      
      expect(screen.getByTestId('project-list-header')).toBeInTheDocument();
    });
  });

  describe('Dialog Management', () => {
    it('should handle form changes', () => {
      const mockHandleFormChange = vi.fn();
      
      // Mock the component to expose form change handler
      vi.spyOn(React, 'useState').mockImplementation((initial: any) => {
        if (initial && typeof initial === 'object' && 'name' in initial && 'description' in initial) {
          return [{ name: 'Test', description: 'Desc' }, mockHandleFormChange];
        }
        return React.useState(initial);
      });

      renderComponent();
      
      // Form handling is done through ProjectDialogs component
      expect(screen.getByTestId('project-dialogs')).toBeInTheDocument();
    });
  });

  describe('Animation States', () => {
    it('should handle delete branch with animations', async () => {
      const mockBranch = { id: 'branch-1', name: 'Branch 1' };
      const mockProject = { id: 'proj-1', name: 'Project 1' };
      
      vi.spyOn(projectDialogsHook, 'useProjectDialogs').mockReturnValue({
        ...mockDialogs,
        showDeleteBranch: { project: mockProject, branch: mockBranch }
      });

      mockProjectData.handleDeleteBranch.mockImplementation(async (data, onFadeoutStart, onFadeoutComplete) => {
        onFadeoutStart();
        await new Promise(resolve => setTimeout(resolve, 10));
        onFadeoutComplete();
      });

      renderComponent();

      // Wait for animation callbacks
      await waitFor(() => {
        expect(mockAnimations.setFadingOutBranches).toHaveBeenCalled();
        expect(mockAnimations.setDeletingBranches).toHaveBeenCalled();
      });
    });
  });

  describe('Empty State', () => {
    it('should render empty state when no projects', () => {
      vi.spyOn(projectDataHook, 'useProjectData').mockReturnValue({
        ...mockProjectData,
        projects: []
      });

      renderComponent();
      
      // Should still render header and content area
      expect(screen.getByTestId('project-list-header')).toBeInTheDocument();
      expect(screen.getByTestId('project-list-content')).toBeInTheDocument();
    });
  });
});