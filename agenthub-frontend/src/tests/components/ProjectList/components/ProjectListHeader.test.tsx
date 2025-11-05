import React from 'react';
import { render, screen, fireEvent } from './../../../test-utils';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { ProjectListHeader } from '../../../../components/ProjectList/components/ProjectListHeader';
import type { ProjectListHeaderProps } from '../../../../types/componentTypes';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Globe: vi.fn(({ className }) => <div data-testid="globe-icon" className={className} />),
  Plus: vi.fn(({ className }) => <div data-testid="plus-icon" className={className} />),
  Wifi: vi.fn(({ className }) => <div data-testid="wifi-icon" className={className} />),
  WifiOff: vi.fn(({ className }) => <div data-testid="wifi-off-icon" className={className} />),
}));

// Mock UI components
vi.mock('../../../../components/ui/refresh-button', () => ({
  RefreshButton: vi.fn(({ onClick, loading, className, size, title, children }) => (
    <button
      onClick={onClick}
      data-testid="refresh-button"
      data-loading={loading}
      className={className}
      data-size={size}
      title={title}
    >
      {children || 'Refresh'}
    </button>
  ))
}));

vi.mock('../../../../components/ui/shimmer-button', () => ({
  ShimmerButton: vi.fn(({ onClick, className, children, title, variant, size, ...props }) => (
    <button
      onClick={onClick}
      data-testid="shimmer-button"
      className={className}
      title={title}
      data-variant={variant}
      data-size={size}
      {...props}
    >
      {children}
    </button>
  ))
}));

describe('ProjectListHeader Component', () => {
  const mockOnRefresh = vi.fn();
  const mockOnShowGlobalContext = vi.fn();
  const mockOnCreateProject = vi.fn();

  const defaultProps: ProjectListHeaderProps = {
    loading: false,
    loadingBulkSummaries: false,
    isConnected: true,
    onRefresh: mockOnRefresh,
    onShowGlobalContext: mockOnShowGlobalContext,
    onCreateProject: mockOnCreateProject,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (props: Partial<ProjectListHeaderProps> = {}) => {
    return render(<ProjectListHeader {...defaultProps} {...props} />);
  };

  describe('Title Section', () => {
    it('should render the Projects title', () => {
      renderComponent();
      expect(screen.getByText('Projects')).toBeInTheDocument();
    });
  });

  describe('WebSocket Connection Status', () => {
    it('should show connected status when isConnected is true', () => {
      renderComponent({ isConnected: true });
      
      expect(screen.getByTestId('wifi-icon')).toBeInTheDocument();
      expect(screen.getByText('Live')).toBeInTheDocument();
      expect(screen.queryByTestId('wifi-off-icon')).not.toBeInTheDocument();
    });

    it('should show disconnected status when isConnected is false', () => {
      renderComponent({ isConnected: false });
      
      expect(screen.getByTestId('wifi-off-icon')).toBeInTheDocument();
      expect(screen.getByText('Offline')).toBeInTheDocument();
      expect(screen.queryByTestId('wifi-icon')).not.toBeInTheDocument();
    });

    it('should apply correct styling for connected state', () => {
      renderComponent({ isConnected: true });
      
      const statusContainer = screen.getByText('Live').closest('div');
      expect(statusContainer).toHaveClass('bg-green-100', 'text-green-700');
    });

    it('should apply correct styling for disconnected state', () => {
      renderComponent({ isConnected: false });
      
      const statusContainer = screen.getByText('Offline').closest('div');
      expect(statusContainer).toHaveClass('bg-red-100', 'text-red-700');
    });
  });

  describe('Refresh Button', () => {
    it('should render refresh buttons with correct props', () => {
      renderComponent();
      
      const refreshButtons = screen.getAllByTestId('refresh-button');
      expect(refreshButtons.length).toBeGreaterThan(0);
      
      // All refresh buttons should have the same title
      refreshButtons.forEach(button => {
        expect(button).toHaveAttribute('title', 'Refresh projects and branch summaries');
      });
    });

    it('should pass loading state to refresh buttons', () => {
      renderComponent({ loading: true });
      
      const refreshButtons = screen.getAllByTestId('refresh-button');
      refreshButtons.forEach(button => {
        expect(button).toHaveAttribute('data-loading', 'true');
      });
    });

    it('should pass loadingBulkSummaries state to refresh buttons', () => {
      renderComponent({ loadingBulkSummaries: true });
      
      const refreshButtons = screen.getAllByTestId('refresh-button');
      refreshButtons.forEach(button => {
        expect(button).toHaveAttribute('data-loading', 'true');
      });
    });

    it('should call onRefresh when refresh button is clicked', () => {
      renderComponent();
      
      const refreshButton = screen.getAllByTestId('refresh-button')[0];
      fireEvent.click(refreshButton);
      
      expect(mockOnRefresh).toHaveBeenCalledTimes(1);
    });

    it('should have different visibility classes for responsive design', () => {
      renderComponent();
      
      const refreshButtons = screen.getAllByTestId('refresh-button');
      const classes = refreshButtons.map(button => button.className);
      
      // Should have different responsive classes
      expect(classes.some(cls => cls.includes('sm:hidden'))).toBe(true);
      expect(classes.some(cls => cls.includes('hidden sm:flex'))).toBe(true);
      expect(classes.some(cls => cls.includes('hidden lg:flex'))).toBe(true);
    });
  });

  describe('Global Context Button', () => {
    it('should render global context button with correct props', () => {
      renderComponent();
      
      const globalButton = screen.getByRole('button', { name: 'View/Edit Global Context' });
      expect(globalButton).toBeInTheDocument();
      expect(globalButton).toHaveAttribute('title', 'View and Edit Global Context');
    });

    it('should show globe icon', () => {
      renderComponent();
      
      const globeIcon = screen.getByTestId('globe-icon');
      expect(globeIcon).toBeInTheDocument();
      expect(globeIcon).toHaveClass('w-4', 'h-4');
    });

    it('should show "Global" text on large screens', () => {
      renderComponent();
      
      const globalText = screen.getByText('Global');
      expect(globalText).toHaveClass('hidden', 'lg:inline');
    });

    it('should call onShowGlobalContext when clicked', () => {
      renderComponent();
      
      const globalButton = screen.getByRole('button', { name: 'View/Edit Global Context' });
      fireEvent.click(globalButton);
      
      expect(mockOnShowGlobalContext).toHaveBeenCalledTimes(1);
    });

    it('should handle undefined onShowGlobalContext gracefully', () => {
      renderComponent({ onShowGlobalContext: undefined });
      
      const globalButton = screen.getByRole('button', { name: 'View/Edit Global Context' });
      
      // Should not throw when clicked
      expect(() => fireEvent.click(globalButton)).not.toThrow();
    });

    it('should have correct styling', () => {
      renderComponent();
      
      const globalButton = screen.getByRole('button', { name: 'View/Edit Global Context' });
      expect(globalButton).toHaveAttribute('data-variant', 'outline');
      expect(globalButton).toHaveAttribute('data-size', 'sm');
    });
  });

  describe('Create Project Button', () => {
    it('should render create project button with correct props', () => {
      renderComponent();
      
      const createButton = screen.getByRole('button', { name: /New Project/i });
      expect(createButton).toBeInTheDocument();
      expect(createButton).toHaveAttribute('title', 'Create New Project');
    });

    it('should show plus icon', () => {
      renderComponent();
      
      const plusIcon = screen.getByTestId('plus-icon');
      expect(plusIcon).toBeInTheDocument();
      expect(plusIcon).toHaveClass('w-4', 'h-4');
    });

    it('should show "New Project" text on large screens', () => {
      renderComponent();
      
      const projectText = screen.getByText('New Project');
      expect(projectText).toHaveClass('hidden', 'lg:inline');
    });

    it('should call onCreateProject when clicked', () => {
      renderComponent();
      
      const createButton = screen.getByRole('button', { name: /New Project/i });
      fireEvent.click(createButton);
      
      expect(mockOnCreateProject).toHaveBeenCalledTimes(1);
    });

    it('should have correct styling', () => {
      renderComponent();
      
      const createButton = screen.getByRole('button', { name: /New Project/i });
      expect(createButton).toHaveAttribute('data-variant', 'default');
      expect(createButton).toHaveAttribute('data-size', 'sm');
    });
  });

  describe('Responsive Layout', () => {
    it('should render with responsive flex layout', () => {
      const { container } = renderComponent();
      
      const mainContainer = container.firstChild as HTMLElement;
      expect(mainContainer).toHaveClass('flex', 'flex-col', 'sm:flex-row');
    });

    it('should have responsive gap and margin classes', () => {
      const { container } = renderComponent();
      
      const mainContainer = container.firstChild as HTMLElement;
      expect(mainContainer).toHaveClass('gap-3', 'mb-2');
    });

    it('should have responsive button container', () => {
      renderComponent();
      
      const buttonContainers = screen.getAllByRole('button').map(btn => btn.parentElement);
      const actionContainer = buttonContainers.find(container => 
        container?.className.includes('flex gap-2 justify-end')
      );
      
      expect(actionContainer).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      renderComponent();
      
      expect(screen.getByRole('button', { name: 'View/Edit Global Context' })).toBeInTheDocument();
      // Create button has title but text content serves as accessible name
      expect(screen.getByRole('button', { name: /New Project/i })).toBeInTheDocument();
    });

    it('should have proper title attributes for tooltips', () => {
      renderComponent();
      
      const buttons = screen.getAllByRole('button');
      
      // Check that all interactive elements have titles
      const titledButtons = buttons.filter(btn => btn.hasAttribute('title'));
      expect(titledButtons.length).toBeGreaterThan(0);
    });
  });
});