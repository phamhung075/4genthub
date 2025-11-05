/**
 * Unit tests for TaskRow animation callbacks and mount-time detection.
 * Tests animation registration, callback firing, and mount-time animation detection.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from './../test-utils';
import { BrowserRouter } from 'react-router-dom';
import TaskRow from '../../components/TaskRow';
import animationFactory from '../../services/AnimationFactory';
import { TaskSummary } from '../../types/taskTypes';

// Mock the animation factory
vi.mock('../../services/AnimationFactory', () => {
  const mockFactory = {
    registerElement: vi.fn(),
    unregisterElement: vi.fn(),
    animate: vi.fn().mockReturnValue(true)
  };
  return {
    default: mockFactory,
    animationFactory: mockFactory
  };
});

// Mock logger
vi.mock('../../utils/logger', () => ({
  default: {
    info: vi.fn(),
    debug: vi.fn(),
    error: vi.fn(),
    warn: vi.fn()
  }
}));

// Mock UI components that might be causing issues
vi.mock('../../components/ClickableAssignees', () => ({
  default: () => <div>ClickableAssignees</div>
}));

vi.mock('../../components/ui/ProgressDisplay', () => ({
  ProgressDisplayEnhanced: () => <div>ProgressDisplay</div>
}));

vi.mock('../../components/LazySubtaskList', () => ({
  default: () => <div>LazySubtaskList</div>
}));

// Mock react-router-dom hook
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: vi.fn(() => vi.fn())
  };
});

// Test wrapper component with proper table structure
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  return (
    <BrowserRouter>
      <table>
        <tbody>
          {children}
        </tbody>
      </table>
    </BrowserRouter>
  );
};

const mockTaskSummary: TaskSummary = {
  id: 'test-task-123',
  title: 'Test Task',
  status: 'todo',
  priority: 'medium',
  assignees: ['coding-agent'],
  has_dependencies: false,
  created_at: new Date().toISOString()
};

const mockTaskRowProps = {
  summary: mockTaskSummary,
  isExpanded: false,
  isLoading: false,
  fullTask: null,
  isHighlighted: false,
  isHovered: false,
  projectId: 'test-project',
  taskTreeId: 'test-tree',
  isMobile: false,
  onToggleExpansion: vi.fn(),
  onOpenDialog: vi.fn(),
  onHover: vi.fn()
};

describe('TaskRow Animation System', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe('Mount-Time Animation Detection', () => {
    it('should trigger CREATE animation for recently created tasks (within 10 seconds)', async () => {
      const recentTime = new Date();
      const recentTaskSummary = {
        ...mockTaskSummary,
        created_at: recentTime.toISOString()
      };

      render(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} summary={recentTaskSummary} />
        </TestWrapper>
      );

      // Component renders immediately
      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Fast forward the 100ms delay for mount-time animation
      vi.advanceTimersByTime(100);

      // Should have called animationFactory.animate with 'create' and 'mount' source
      await waitFor(() => {
        expect(animationFactory.animate).toHaveBeenCalledWith(
          expect.any(String),
          'create',
          'mount'
        );
      });
    });

    it('should NOT trigger CREATE animation for old tasks (more than 10 seconds old)', async () => {
      const oldTime = new Date(Date.now() - 15000); // 15 seconds ago
      const oldTaskSummary = {
        ...mockTaskSummary,
        created_at: oldTime.toISOString()
      };

      render(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} summary={oldTaskSummary} />
        </TestWrapper>
      );

      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Fast forward past the mount-time check
      vi.advanceTimersByTime(200);

      // Should NOT have called animate for mount-time detection
      expect(animationFactory.animate).not.toHaveBeenCalledWith(
        expect.any(String),
        'create',
        'mount'
      );
    });

    it('should handle missing created_at gracefully', async () => {
      const taskWithoutCreatedAt = {
        ...mockTaskSummary,
        created_at: undefined
      };

      render(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} summary={taskWithoutCreatedAt} />
        </TestWrapper>
      );

      // Text is already in DOM, no need for waitFor
      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      vi.advanceTimersByTime(200);

      // Should not trigger any animation without created_at
      expect(animationFactory.animate).not.toHaveBeenCalled();
    });
  });

  describe('Animation Callback Registration', () => {
    it('should register element with AnimationFactory on mount', async () => {
      render(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} />
        </TestWrapper>
      );

      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Should register element with animation factory
      expect(animationFactory.registerElement).toHaveBeenCalledWith(
        mockTaskSummary.id,
        expect.any(Object), // DOM element
        expect.objectContaining({
          onAnimationStart: expect.any(Function),
          onAnimationEnd: expect.any(Function)
        })
      );
    });

    it('should register callbacks with parent component', async () => {
      const mockRegisterCallbacks = vi.fn();

      render(
        <TestWrapper>
          <TaskRow
            {...mockTaskRowProps}
            onRegisterCallbacks={mockRegisterCallbacks}
          />
        </TestWrapper>
      );

      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Should register callbacks with parent
      expect(mockRegisterCallbacks).toHaveBeenCalledWith(
        mockTaskSummary.id,
        expect.objectContaining({
          playCreateAnimation: expect.any(Function),
          playDeleteAnimation: expect.any(Function),
          playUpdateAnimation: expect.any(Function)
        })
      );
    });

    it('should unregister callbacks on unmount', async () => {
      const mockUnregisterCallbacks = vi.fn();

      const { unmount } = render(
        <TestWrapper>
          <TaskRow
            {...mockTaskRowProps}
            onUnregisterCallbacks={mockUnregisterCallbacks}
          />
        </TestWrapper>
      );

      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Unmount component
      unmount();

      // Should unregister from animation factory
      expect(animationFactory.unregisterElement).toHaveBeenCalledWith(mockTaskSummary.id);

      // Should unregister callbacks from parent
      expect(mockUnregisterCallbacks).toHaveBeenCalledWith(mockTaskSummary.id);
    });
  });

  describe('Animation Callback Execution', () => {
    it('should execute CREATE animation when callback is called', async () => {
      let registeredCallbacks: any = null;

      const captureCallbacks = vi.fn((_taskId, callbacks) => {
        registeredCallbacks = callbacks;
      });

      render(
        <TestWrapper>
          <TaskRow
            {...mockTaskRowProps}
            onRegisterCallbacks={captureCallbacks}
          />
        </TestWrapper>
      );

      // Component text is immediately available
      expect(screen.getByText('Test Task')).toBeInTheDocument();

      // Wait only for callback registration
      await waitFor(() => {
        expect(registeredCallbacks).not.toBeNull();
      });

      // Call the CREATE animation callback
      registeredCallbacks.playCreateAnimation();

      // Should trigger animation factory with CREATE type
      expect(animationFactory.animate).toHaveBeenCalledWith(
        mockTaskSummary.id,
        'create',
        expect.any(String)
      );
    });

    it('should execute UPDATE animation when callback is called', async () => {
      let registeredCallbacks: any = null;

      const captureCallbacks = vi.fn((_taskId, callbacks) => {
        registeredCallbacks = callbacks;
      });

      render(
        <TestWrapper>
          <TaskRow
            {...mockTaskRowProps}
            onRegisterCallbacks={captureCallbacks}
          />
        </TestWrapper>
      );

      // Component text is immediately available
      expect(screen.getByText('Test Task')).toBeInTheDocument();

      // Wait only for callback registration
      await waitFor(() => {
        expect(registeredCallbacks).not.toBeNull();
      });

      // Call the UPDATE animation callback
      registeredCallbacks.playUpdateAnimation();

      // Should trigger animation factory with UPDATE type
      expect(animationFactory.animate).toHaveBeenCalledWith(
        mockTaskSummary.id,
        'update',
        expect.any(String)
      );
    });

    it('should execute DELETE animation when callback is called', async () => {
      let registeredCallbacks: any = null;

      const captureCallbacks = vi.fn((_taskId, callbacks) => {
        registeredCallbacks = callbacks;
      });

      render(
        <TestWrapper>
          <TaskRow
            {...mockTaskRowProps}
            onRegisterCallbacks={captureCallbacks}
          />
        </TestWrapper>
      );

      // Component text is immediately available
      expect(screen.getByText('Test Task')).toBeInTheDocument();

      // Wait only for callback registration
      await waitFor(() => {
        expect(registeredCallbacks).not.toBeNull();
      });

      // Call the DELETE animation callback
      registeredCallbacks.playDeleteAnimation();

      // Should trigger animation factory with DELETE type
      expect(animationFactory.animate).toHaveBeenCalledWith(
        mockTaskSummary.id,
        'delete',
        expect.any(String)
      );
    });

    it('should handle animation source parameter correctly', async () => {
      let registeredCallbacks: any = null;

      const captureCallbacks = vi.fn((_taskId, callbacks) => {
        registeredCallbacks = callbacks;
      });

      render(
        <TestWrapper>
          <TaskRow
            {...mockTaskRowProps}
            onRegisterCallbacks={captureCallbacks}
          />
        </TestWrapper>
      );

      // Component text is immediately available
      expect(screen.getByText('Test Task')).toBeInTheDocument();

      // Wait only for callback registration
      await waitFor(() => {
        expect(registeredCallbacks).not.toBeNull();
      });

      // Call animation with different sources
      registeredCallbacks.playCreateAnimation('mount');
      registeredCallbacks.playUpdateAnimation('websocket');
      registeredCallbacks.playDeleteAnimation('callback');

      // Should pass the source parameter correctly
      expect(animationFactory.animate).toHaveBeenCalledWith(
        mockTaskSummary.id,
        'create',
        'mount'
      );
      expect(animationFactory.animate).toHaveBeenCalledWith(
        mockTaskSummary.id,
        'update',
        'websocket'
      );
      expect(animationFactory.animate).toHaveBeenCalledWith(
        mockTaskSummary.id,
        'delete',
        'callback'
      );
    });
  });

  describe('Mobile vs Desktop Rendering', () => {
    it('should register animations correctly in mobile mode', async () => {
      render(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} isMobile={true} />
        </TestWrapper>
      );

      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Should still register with animation factory in mobile mode
      expect(animationFactory.registerElement).toHaveBeenCalledWith(
        mockTaskSummary.id,
        expect.any(Object),
        expect.any(Object)
      );
    });

    it('should register animations correctly in desktop mode', async () => {
      render(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} isMobile={false} />
        </TestWrapper>
      );

      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Should register with animation factory in desktop mode
      expect(animationFactory.registerElement).toHaveBeenCalledWith(
        mockTaskSummary.id,
        expect.any(Object),
        expect.any(Object)
      );
    });
  });

  describe('Error Handling', () => {
    it('should handle AnimationFactory registration failure gracefully', async () => {
      // Mock animation factory to throw error
      vi.mocked(animationFactory.registerElement).mockImplementationOnce(() => {
        throw new Error('Registration failed');
      });

      // Should not crash the component
      expect(() => {
        render(
          <TestWrapper>
            <TaskRow {...mockTaskRowProps} />
          </TestWrapper>
        );
      }).not.toThrow();
    });

    it('should handle missing callback registration gracefully', async () => {
      render(
        <TestWrapper>
          <TaskRow
            {...mockTaskRowProps}
            onRegisterCallbacks={undefined}
            onUnregisterCallbacks={undefined}
          />
        </TestWrapper>
      );

      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Component should still function without callback registration
      expect(screen.getByText('Test Task')).toBeInTheDocument();
    });

    it('should handle animation callback execution failure gracefully', async () => {
      // Mock animate to throw error
      vi.mocked(animationFactory.animate).mockImplementationOnce(() => {
        throw new Error('Animation failed');
      });

      let registeredCallbacks: any = null;

      const captureCallbacks = vi.fn((_taskId, callbacks) => {
        registeredCallbacks = callbacks;
      });

      render(
        <TestWrapper>
          <TaskRow
            {...mockTaskRowProps}
            onRegisterCallbacks={captureCallbacks}
          />
        </TestWrapper>
      );

      // Component text is immediately available
      expect(screen.getByText('Test Task')).toBeInTheDocument();

      // Wait only for callback registration
      await waitFor(() => {
        expect(registeredCallbacks).not.toBeNull();
      });

      // Should not throw when animation fails
      expect(() => {
        registeredCallbacks.playCreateAnimation();
      }).not.toThrow();
    });
  });

  describe('Component Lifecycle', () => {
    it('should maintain animation registration across re-renders', async () => {
      const { rerender } = render(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} />
        </TestWrapper>
      );

      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Clear mock calls
      vi.clearAllMocks();

      // Re-render with updated props
      rerender(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} isHighlighted={true} />
        </TestWrapper>
      );

      // Should not re-register element on re-render (only on mount)
      expect(animationFactory.registerElement).not.toHaveBeenCalled();
    });

    it('should handle task ID changes correctly', async () => {
      const { rerender } = render(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} />
        </TestWrapper>
      );

      const element = screen.getByText('Test Task');
      expect(element).toBeInTheDocument();

      // Change task ID
      const newTaskSummary = {
        ...mockTaskSummary,
        id: 'new-task-id',
        title: 'New Task'
      };

      rerender(
        <TestWrapper>
          <TaskRow {...mockTaskRowProps} summary={newTaskSummary} />
        </TestWrapper>
      );

      // After rerender, new text should be immediately available
      expect(screen.getByText('New Task')).toBeInTheDocument();

      // Should unregister old task and register new one
      expect(animationFactory.unregisterElement).toHaveBeenCalledWith('test-task-123');
      expect(animationFactory.registerElement).toHaveBeenCalledWith(
        'new-task-id',
        expect.any(Object),
        expect.any(Object)
      );
    });
  });
});
