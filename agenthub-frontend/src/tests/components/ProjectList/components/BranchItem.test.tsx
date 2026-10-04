import React from 'react';
import { render, screen, fireEvent, act } from './../../../test-utils';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { BranchItem } from '../../../../components/ProjectList/components/BranchItem';
import { animationFactory } from '../../../../services/AnimationFactory';
import { branchDeletionTracker } from '../../../../services/branchDeletionTracker';
import type { BranchSummary } from '../../../../types';

// Mock the animation factory
vi.mock('../../../../services/AnimationFactory', () => ({
  animationFactory: {
    registerElement: vi.fn(),
    unregisterElement: vi.fn(),
    animate: vi.fn().mockReturnValue(true),
  },
  AnimationType: {
    TASK_COMPLETE: 'TASK_COMPLETE',
  },
}));

// Mock logger
vi.mock('../../../../utils/logger', () => ({
  default: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  }
}));

// Mock the UI components
vi.mock('../../../../components/ui/shimmer-badge', () => ({
  ShimmerBadge: ({ children, className, ...props }: any) => (
    <span className={className} {...props}>{children}</span>
  ),
}));

vi.mock('../../../../components/ui/shimmer-button', () => ({
  ShimmerButton: ({ children, onClick, disabled, className, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} className={className} {...props}>
      {children}
    </button>
  ),
}));

describe('BranchItem', () => {
  const mockBranch: BranchSummary = {
    id: 'branch-1',
    git_branch_name: 'feature/test-branch',
    name: 'Test Branch',
  };

  const mockProject = {
    id: 'project-1',
    name: 'Test Project',
  };

  const defaultProps = {
    branch: mockBranch,
    projectId: 'project-1',
    selected: null,
    taskCount: 5,
    isAnimatingCount: null as 'up' | 'down' | null,
    onSelect: vi.fn(),
    onShowDetails: vi.fn(),
    onDelete: vi.fn(),
    project: mockProject,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders branch name correctly', () => {
    render(<BranchItem {...defaultProps} />);
    expect(screen.getByText('feature/test-branch')).toBeInTheDocument();
  });

  it('displays task count badge', () => {
    render(<BranchItem {...defaultProps} />);
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('falls back to name when git_branch_name is not available', () => {
    const branchWithoutGitName = { ...mockBranch, git_branch_name: undefined };
    render(<BranchItem {...defaultProps} branch={branchWithoutGitName} />);
    expect(screen.getByText('Test Branch')).toBeInTheDocument();
  });

  it('applies selected styles when branch is selected', () => {
    render(<BranchItem {...defaultProps} selected={`project-1:branch-1`} />);
    const button = screen.getByRole('button', { name: /feature\/test-branch/ });
    expect(button).toHaveClass('bg-blue-50', 'dark:bg-blue-900/20', 'border-2', 'border-blue-300');
  });

  it('calls onSelect when clicked', () => {
    render(<BranchItem {...defaultProps} />);
    const button = screen.getByRole('button', { name: /feature\/test-branch/ });
    fireEvent.click(button);
    expect(defaultProps.onSelect).toHaveBeenCalledWith('project-1', 'branch-1');
  });

  it('shows view details button that calls onShowDetails', () => {
    render(<BranchItem {...defaultProps} />);
    const viewButton = screen.getByRole('button', { name: 'View Branch Details' });
    fireEvent.click(viewButton);
    expect(defaultProps.onShowDetails).toHaveBeenCalledWith(mockProject, mockBranch);
  });

  it('shows delete button for non-main branches', () => {
    render(<BranchItem {...defaultProps} />);
    const deleteButton = screen.getByRole('button', { name: 'Delete Branch' });
    expect(deleteButton).toBeInTheDocument();
    fireEvent.click(deleteButton);
    expect(defaultProps.onDelete).toHaveBeenCalledWith({ project: mockProject, branch: mockBranch });
  });

  it('hides delete button for main branch', () => {
    const mainBranch = { ...mockBranch, git_branch_name: 'main' };
    render(<BranchItem {...defaultProps} branch={mainBranch} />);
    expect(screen.queryByRole('button', { name: 'Delete Branch' })).not.toBeInTheDocument();
  });

  describe('animations (useBranchAnimation)', () => {
    const container = () => screen.getByRole('button', { name: /feature\/test-branch/ }).closest('div') as HTMLElement;

    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.mocked(branchDeletionTracker.isMarkedForDeletion).mockReset();
      vi.useRealTimers();
      vi.mocked(animationFactory.animate).mockReturnValue(true);
    });

    it('plays the create animation for a branch created within the last 2 seconds', () => {
      render(<BranchItem {...defaultProps} branch={{ ...mockBranch, created_at: new Date().toISOString() } as BranchSummary} />);
      expect(animationFactory.animate).not.toHaveBeenCalled();

      act(() => { vi.advanceTimersByTime(50); });

      expect(animationFactory.animate).toHaveBeenCalledWith('branch-1', 'create', 'mount');
    });

    it('does not animate a branch that was created earlier', () => {
      const old = new Date(Date.now() - 60_000).toISOString();
      render(<BranchItem {...defaultProps} branch={{ ...mockBranch, created_at: old } as BranchSummary} />);

      act(() => { vi.advanceTimersByTime(100); });

      expect(animationFactory.animate).not.toHaveBeenCalled();
    });

    it('applies the CSS create class when the factory cannot animate', () => {
      vi.mocked(animationFactory.animate).mockReturnValue(false);
      render(<BranchItem {...defaultProps} branch={{ ...mockBranch, created_at: new Date().toISOString() } as BranchSummary} />);

      act(() => { vi.advanceTimersByTime(50); });

      expect(container()).toHaveClass('branchRowCreateAnimation');
    });

    it('plays the delete animation for a branch marked for deletion and then removes it', () => {
      render(<BranchItem {...defaultProps} />);
      // src/setupTests.ts auto-mocks the tracker, so state is set through the mock
      vi.mocked(branchDeletionTracker.isMarkedForDeletion).mockReturnValue(true);

      act(() => { vi.advanceTimersByTime(50); });
      expect(animationFactory.animate).toHaveBeenCalledWith('branch-1', 'delete', 'websocket');
      expect(container()).toBeInTheDocument();

      act(() => { vi.advanceTimersByTime(800); });
      expect(screen.queryByRole('button', { name: /feature\/test-branch/ })).not.toBeInTheDocument();
    });

    it('applies the CSS delete class while a branch is being removed without the factory', () => {
      vi.mocked(animationFactory.animate).mockReturnValue(false);
      render(<BranchItem {...defaultProps} />);
      // src/setupTests.ts auto-mocks the tracker, so state is set through the mock
      vi.mocked(branchDeletionTracker.isMarkedForDeletion).mockReturnValue(true);

      act(() => { vi.advanceTimersByTime(50); });

      expect(container()).toHaveClass('branchRowDeleteAnimation');
    });
  });

  it('applies count animation classes', () => {
    const { rerender } = render(<BranchItem {...defaultProps} />);

    // Test up animation
    rerender(<BranchItem {...defaultProps} isAnimatingCount="up" />);
    expect(screen.getByText('5')).toHaveClass('count-change-up', 'count-pulse');

    // Test down animation
    rerender(<BranchItem {...defaultProps} isAnimatingCount="down" />);
    expect(screen.getByText('5')).toHaveClass('count-change-down', 'count-pulse');
  });

  it('registers and unregisters element with AnimationFactory', () => {
    const { unmount } = render(<BranchItem {...defaultProps} />);

    // Check registration
    expect(animationFactory.registerElement).toHaveBeenCalledWith(
      'branch-1',
      expect.any(HTMLElement),
      'branch',
      expect.objectContaining({
        onAnimationStart: expect.any(Function),
        onAnimationEnd: expect.any(Function),
      })
    );

    // Check unregistration on unmount
    unmount();
    expect(animationFactory.unregisterElement).toHaveBeenCalledWith('branch-1');
  });

  it('handles onSelect being undefined gracefully', () => {
    const propsWithoutOnSelect = { ...defaultProps, onSelect: undefined };
    render(<BranchItem {...propsWithoutOnSelect} />);
    const button = screen.getByRole('button', { name: /feature\/test-branch/ });
    expect(() => fireEvent.click(button)).not.toThrow();
  });

  it('handles onShowDetails being undefined gracefully', () => {
    const propsWithoutOnShowDetails = { ...defaultProps, onShowDetails: undefined };
    render(<BranchItem {...propsWithoutOnShowDetails} />);
    const viewButton = screen.getByRole('button', { name: 'View Branch Details' });
    expect(() => fireEvent.click(viewButton)).not.toThrow();
  });

  it('sets correct data attribute for branch id', () => {
    render(<BranchItem {...defaultProps} />);
    const element = screen.getByRole('button', { name: /feature\/test-branch/ }).closest('div');
    expect(element).toHaveAttribute('data-branch-id', 'branch-1');
  });

  it('displays correct aria labels and titles', () => {
    render(<BranchItem {...defaultProps} />);

    const viewButton = screen.getByRole('button', { name: 'View Branch Details' });
    expect(viewButton).toHaveAttribute('title', 'View Branch Details');

    const deleteButton = screen.getByRole('button', { name: 'Delete Branch' });
    expect(deleteButton).toHaveAttribute('aria-label', 'Delete Branch');
  });
});
