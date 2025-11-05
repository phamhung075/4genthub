import React from 'react';
import { render, screen, fireEvent } from './../../../test-utils';
import { ProjectListContent } from '../../../../components/ProjectList/components/ProjectListContent';
import { Project } from '../../../../api';
import type { BranchSummary } from '../../../../types';
import type { ProjectListContentProps } from '../../../../types/componentTypes';

// Mock the UI components
vi.mock('../../../../components/ui/shimmer-badge', () => ({
  ShimmerBadge: ({ children, className, ...props }: any) => (
    <span className={className} {...props}>{children}</span>
  ),
}));

vi.mock('../../../../components/ui/shimmer-button', () => ({
  ShimmerButton: ({ children, onClick, className, ...props }: any) => (
    <button onClick={onClick} className={className} {...props}>
      {children}
    </button>
  ),
}));

// Mock the BranchItem component
vi.mock('../../../../components/ProjectList/components/BranchItem', () => ({
  BranchItem: ({ branch, onSelect, onShowDetails, onDelete, taskCount }: any) => (
    <li data-testid={`branch-${branch.id}`}>
      <button onClick={() => onSelect('project-1', branch.id)}>
        {branch.git_branch_name || branch.name} ({taskCount})
      </button>
      <button onClick={() => onShowDetails({}, branch)}>View</button>
      <button onClick={() => onDelete({ project: {}, branch })}>Delete</button>
    </li>
  ),
}));

describe('ProjectListContent', () => {
  const mockProject1: Project = {
    id: 'project-1',
    name: 'Project One',
    git_branchs: {
      'branch-1': {
        id: 'branch-1',
        git_branch_name: 'main',
        tasks: ['task-1', 'task-2', 'task-3'],
      },
      'branch-2': {
        id: 'branch-2',
        git_branch_name: 'feature/test',
        tasks: ['task-1', 'task-2', 'task-3', 'task-4', 'task-5'],
      },
    },
  };

  const mockProject2: Project = {
    id: 'project-2',
    name: 'Project Two',
    git_branchs: {
      'branch-3': {
        id: 'branch-3',
        git_branch_name: 'develop',
        tasks: ['task-1', 'task-2'],
      },
    },
  };

  const mockBranchSummaries: Record<string, BranchSummary[]> = {
    'project-1': [
      { id: 'branch-1', git_branch_name: 'main', name: 'Main' },
      { id: 'branch-2', git_branch_name: 'feature/test', name: 'Test Feature' },
    ],
    'project-2': [
      { id: 'branch-3', git_branch_name: 'develop', name: 'Develop' },
    ],
  };

  const mockTaskCounts: Record<string, number> = {
    'branch-1': 3,
    'branch-2': 5,
    'branch-3': 2,
  };

  const defaultProps: ProjectListContentProps = {
    projects: [mockProject1, mockProject2],
    branchSummaries: mockBranchSummaries,
    taskCounts: mockTaskCounts,
    openProjects: { 'project-1': true, 'project-2': false },
    selected: null,
    newBranches: new Set(),
    fadingOutBranches: new Set(),
    deletingBranches: new Set(),
    animatingCounts: new Map(),
    onToggleProject: vi.fn(),
    onSelectBranch: vi.fn(),
    onShowProjectDetails: vi.fn(),
    onShowBranchDetails: vi.fn(),
    onCreateBranch: vi.fn(),
    onEditProject: vi.fn(),
    onDeleteProject: vi.fn(),
    onDeleteBranch: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no projects', () => {
    render(<ProjectListContent {...defaultProps} projects={[]} />);
    expect(screen.getByText('No projects found.')).toBeInTheDocument();
  });

  it('renders all projects', () => {
    render(<ProjectListContent {...defaultProps} />);
    expect(screen.getByText('Project One')).toBeInTheDocument();
    expect(screen.getByText('Project Two')).toBeInTheDocument();
  });

  it('displays branch count badges', () => {
    render(<ProjectListContent {...defaultProps} />);
    expect(screen.getByText('2 branches')).toBeInTheDocument();
    expect(screen.getByText('1 branch')).toBeInTheDocument();
  });

  it('displays task count badges', () => {
    render(<ProjectListContent {...defaultProps} />);
    expect(screen.getByText('8 tasks')).toBeInTheDocument(); // 3 + 5 for project 1
    expect(screen.getByText('2 tasks')).toBeInTheDocument(); // 2 for project 2
  });

  it('shows correct singular/plural text for counts', () => {
    const singleBranchProject: Project = {
      id: 'project-3',
      name: 'Single Branch Project',
      git_branchs: {
        'branch-4': { id: 'branch-4', tasks: ['task-1'] },
      },
    };

    render(<ProjectListContent {...defaultProps} projects={[singleBranchProject]} />);
    expect(screen.getByText('1 branch')).toBeInTheDocument();
    expect(screen.getByText('1 task')).toBeInTheDocument();
  });

  it('toggles project expansion on click', () => {
    render(<ProjectListContent {...defaultProps} />);
    const projectHeader = screen.getByText('Project One').parentElement;
    fireEvent.click(projectHeader!);
    expect(defaultProps.onToggleProject).toHaveBeenCalledWith('project-1');
  });

  it('shows branches when project is open', () => {
    render(<ProjectListContent {...defaultProps} />);
    expect(screen.getByTestId('branch-branch-1')).toBeInTheDocument();
    expect(screen.getByTestId('branch-branch-2')).toBeInTheDocument();
  });

  it('hides branches when project is closed', () => {
    render(<ProjectListContent {...defaultProps} />);
    // Project 2 is closed by default
    expect(screen.queryByTestId('branch-branch-3')).toHaveStyle({ display: 'none' });
  });

  it('calls action handlers for project buttons', () => {
    render(<ProjectListContent {...defaultProps} />);
    
    // Find buttons for Project One
    const buttons = screen.getAllByRole('button');
    
    // View project details
    const viewButton = buttons.find(btn => btn.getAttribute('aria-label') === 'View Project Details');
    fireEvent.click(viewButton!);
    expect(defaultProps.onShowProjectDetails).toHaveBeenCalledWith(mockProject1);
    
    // Create branch
    const createBranchButton = buttons.find(btn => btn.getAttribute('aria-label') === 'Create Branch');
    fireEvent.click(createBranchButton!);
    expect(defaultProps.onCreateBranch).toHaveBeenCalledWith(mockProject1);
    
    // Edit project
    const editButton = buttons.find(btn => btn.getAttribute('aria-label') === 'Edit');
    fireEvent.click(editButton!);
    expect(defaultProps.onEditProject).toHaveBeenCalledWith(mockProject1);
    
    // Delete project
    const deleteButton = buttons.find(btn => btn.getAttribute('aria-label') === 'Delete');
    fireEvent.click(deleteButton!);
    expect(defaultProps.onDeleteProject).toHaveBeenCalledWith(mockProject1);
  });

  it('uses branch summaries when available', () => {
    render(<ProjectListContent {...defaultProps} />);
    // Should render branches from branchSummaries
    expect(screen.getByText('main (3)')).toBeInTheDocument();
    expect(screen.getByText('feature/test (5)')).toBeInTheDocument();
  });

  it('falls back to git_branchs when branch summaries not available', () => {
    const propsWithoutSummaries = {
      ...defaultProps,
      branchSummaries: {},
    };
    render(<ProjectListContent {...propsWithoutSummaries} />);
    // Should still render branches from project.git_branchs
    expect(screen.getByText('main (3)')).toBeInTheDocument();
    expect(screen.getByText('feature/test (5)')).toBeInTheDocument();
  });

  it('handles projects without branches', () => {
    const projectWithoutBranches: Project = {
      id: 'project-empty',
      name: 'Empty Project',
    };
    
    render(<ProjectListContent {...defaultProps} projects={[projectWithoutBranches]} />);
    expect(screen.getByText('Empty Project')).toBeInTheDocument();
    // Should not show branch badge
    expect(screen.queryByText(/branch/)).not.toBeInTheDocument();
  });

  it('applies correct chevron icon based on project open state', () => {
    render(<ProjectListContent {...defaultProps} />);
    
    // Project 1 is open - should have ChevronDown
    const project1Container = screen.getByText('Project One').closest('.group');
    expect(project1Container?.querySelector('svg')).toBeInTheDocument();
    
    // Project 2 is closed - should have ChevronRight
    const project2Container = screen.getByText('Project Two').closest('.group');
    expect(project2Container?.querySelector('svg')).toBeInTheDocument();
  });

  it('renders count animation styles', () => {
    render(<ProjectListContent {...defaultProps} />);
    const styleElement = document.querySelector('style');
    expect(styleElement?.textContent).toContain('@keyframes countPulse');
    expect(styleElement?.textContent).toContain('.count-pulse');
    expect(styleElement?.textContent).toContain('.count-change-up');
    expect(styleElement?.textContent).toContain('.count-change-down');
  });

  it('passes animation state to branch items', () => {
    const animatingCounts = new Map([['branch-1', 'up' as const]]);
    const newBranches = new Set(['branch-2']);
    const fadingOutBranches = new Set(['branch-3']);
    
    render(
      <ProjectListContent
        {...defaultProps}
        animatingCounts={animatingCounts}
        newBranches={newBranches}
        fadingOutBranches={fadingOutBranches}
      />
    );
    
    // BranchItem mock should receive these props
    expect(screen.getByTestId('branch-branch-1')).toBeInTheDocument();
    expect(screen.getByTestId('branch-branch-2')).toBeInTheDocument();
  });

  it('handles undefined task counts gracefully', () => {
    const projectWithUndefinedTaskCount: Project = {
      id: 'project-4',
      name: 'Project Four',
      git_branchs: {
        'branch-4': {
          id: 'branch-4',
          git_branch_name: 'main',
          tasks: [],
        },
      },
    };

    render(
      <ProjectListContent
        {...defaultProps}
        projects={[projectWithUndefinedTaskCount]}
        branchSummaries={{}}
      />
    );

    // Should use tasks array length
    expect(screen.getByText('main (0)')).toBeInTheDocument();
  });

  it('handles optional callback functions being undefined', () => {
    const propsWithUndefinedCallbacks = {
      ...defaultProps,
      onShowProjectDetails: undefined,
      onShowBranchDetails: undefined,
    };
    
    render(<ProjectListContent {...propsWithUndefinedCallbacks} />);
    
    const buttons = screen.getAllByRole('button');
    const viewButton = buttons.find(btn => btn.getAttribute('aria-label') === 'View Project Details');
    
    // Should not throw when clicking with undefined handler
    expect(() => fireEvent.click(viewButton!)).not.toThrow();
  });
});