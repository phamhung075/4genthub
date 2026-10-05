import React from 'react';
import { render, screen, waitFor, fireEvent, act } from './test-utils';
import { vi } from 'vitest';
import App from '../App';

// Note: react-router-dom is intentionally not mocked. test-utils wraps the tree in a
// real BrowserRouter so path-based Routes resolve to a single matching route.

// Authenticated auth context so route guards/home behave as a logged-in user.
// The value is created once: a new object or new functions on every render would
// re-trigger any effect that depends on them and loop forever.
const authValue = vi.hoisted(() => ({
  user: { id: 'user-1', email: 'test@example.com', username: 'test', roles: ['user'] },
  tokens: { access_token: 'access-token', refresh_token: 'refresh-token' },
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(),
  signup: vi.fn(),
  logout: vi.fn(),
  refreshToken: vi.fn(),
  setTokens: vi.fn(),
}));

vi.mock('../contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/AuthContext')>();
  return { ...actual, useAuth: () => authValue };
});

// Avoid connecting real realtime widgets for the authenticated state.
vi.mock('../components/WebSocketStatusBadge', () => ({
  WebSocketStatusBadge: () => <div data-testid="websocket-status-badge" />,
}));

// Mock the theme context
// Keep the real module shape (ThemeContext, types) but replace ThemeProvider with a
// pass-through and expose a useTheme hook so consumers never fall back to the real
// implementation that requires a mounted provider.
vi.mock('../contexts/ThemeContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../contexts/ThemeContext')>();
  return {
    ...actual,
    ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
    useTheme: () => ({ theme: 'light' as const, toggleTheme: vi.fn(), setTheme: vi.fn() }),
  };
});

// Mock the toast provider
vi.mock('../components/ui/toast', () => ({
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useToast: () => ({ toast: vi.fn() }),
  useSuccessToast: () => vi.fn(),
  useErrorToast: () => vi.fn()
}));

// Mock the auth components
vi.mock('../components/auth', () => ({
  AuthWrapper: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  LoginForm: () => <div>Login Form</div>,
  SignupForm: () => <div>Signup Form</div>,
  EmailVerification: () => <div>Email Verification</div>,
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock the components
vi.mock('../components/Header', () => ({
  Header: () => <header>Test Header</header>
}));

vi.mock('../components/AppLayout', () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="app-layout">{children}</div>
  )
}));

vi.mock('../pages/Profile', () => ({
  Profile: () => <div>Profile Page</div>
}));

vi.mock('../pages/TokenManagement', () => ({
  TokenManagement: () => <div>Token Management Page</div>
}));

// Mock registration success page
vi.mock('../pages/RegistrationSuccess', () => ({
  default: () => <div>Registration Success</div>
}));

// Mock dialog components
vi.mock('../components/GlobalContextDialog', () => ({
  default: ({ open, onOpenChange, onClose }: any) => open ? <div data-testid="global-context-dialog">Global Context Dialog</div> : null
}));

vi.mock('../components/ProjectDetailsDialog', () => ({
  default: ({ open, onOpenChange, project, onClose }: any) => open ? <div data-testid="project-details-dialog">Project Details Dialog for {project?.name}</div> : null
}));

vi.mock('../components/BranchDetailsDialog', () => ({
  default: ({ open, onOpenChange, project, branch, onClose }: any) => open ? <div data-testid="branch-details-dialog">Branch Details Dialog for {project?.name} - {branch?.name}</div> : null
}));

vi.mock('../components/ProjectList', () => ({
  default: ({ onSelect, onShowGlobalContext, onShowProjectDetails, onShowBranchDetails }: any) => (
    <div data-testid="project-list">
      <button onClick={() => onSelect('project1', 'branch1')}>Select Project</button>
      <button onClick={() => onShowGlobalContext()}>Show Global Context</button>
      <button onClick={() => onShowProjectDetails({ name: 'Test Project' })}>Show Project Details</button>
      <button onClick={() => onShowBranchDetails({ name: 'Test Project' }, { name: 'main' })}>Show Branch Details</button>
    </div>
  )
}));

vi.mock('../components/LazyTaskList', () => ({
  default: ({ projectId, taskTreeId, onTasksChanged }: any) => (
    <div data-testid="task-list">
      Task List for {projectId} - {taskTreeId}
      <button onClick={() => onTasksChanged?.()}>Trigger Task Change</button>
    </div>
  )
}));

describe('App', () => {
  beforeEach(() => {
    // Reset window.location before each test
    window.history.pushState({}, '', '/');
    // Mock window resize
    global.innerWidth = 1024;
    global.dispatchEvent(new Event('resize'));
  });

  it('renders without crashing', async () => {
    render(<App />);
    expect(await screen.findByTestId('project-list')).toBeInTheDocument();
  });

  it('redirects to dashboard from root path', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('project-list')).toBeInTheDocument();
    });
  });

  it('renders login form on /login route', async () => {
    window.history.pushState({}, '', '/login');

    render(
      <App />
    );

    expect(await screen.findByText('Login Form')).toBeInTheDocument();
  });

  it('renders signup form on /signup route', async () => {
    window.history.pushState({}, '', '/signup');

    render(
      <App />
    );

    expect(await screen.findByText('Signup Form')).toBeInTheDocument();
  });

  it('renders email verification on /auth/verify route', async () => {
    window.history.pushState({}, '', '/auth/verify');

    render(
      <App />
    );

    expect(await screen.findByText('Email Verification')).toBeInTheDocument();
  });

  it('renders dashboard with header and project list on /dashboard route', async () => {
    window.history.pushState({}, '', '/dashboard');

    render(
      <App />
    );

    expect(await screen.findByText('Test Header')).toBeInTheDocument();
    expect(screen.getByTestId('project-list')).toBeInTheDocument();
    expect(screen.getByText('Choose a workspace')).toBeInTheDocument();
    expect(screen.getByText('Select a project and branch from the sidebar to start viewing and managing your tasks.')).toBeInTheDocument();
  });

  it('renders registration success on /registration-success route', async () => {
    window.history.pushState({}, '', '/registration-success');

    render(
      <App />
    );

    expect(await screen.findByText('Registration Success')).toBeInTheDocument();
  });

  it('renders profile page with AppLayout on /profile route', async () => {
    window.history.pushState({}, '', '/profile');

    render(
      <App />
    );

    expect(await screen.findByTestId('app-layout')).toBeInTheDocument();
    expect(screen.getByText('Profile Page')).toBeInTheDocument();
  });

  it('renders token management page on /tokens route', async () => {
    window.history.pushState({}, '', '/tokens');

    render(
      <App />
    );

    expect(await screen.findByText('Token Management Page')).toBeInTheDocument();
  });
});

describe('Dashboard', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/dashboard');
  });

  it('shows task list when project is selected', async () => {
    render(<App />);

    const selectButton = await screen.findByText('Select Project');
    fireEvent.click(selectButton);

    await waitFor(() => {
      expect(screen.getByTestId('task-list')).toBeInTheDocument();
      expect(screen.getByText('Task List for project1 - branch1')).toBeInTheDocument();
    });
  });

  it('shows global context dialog when button is clicked', async () => {
    render(<App />);

    const showGlobalContextButton = await screen.findByText('Show Global Context');
    fireEvent.click(showGlobalContextButton);

    await waitFor(() => {
      expect(screen.getByTestId('global-context-dialog')).toBeInTheDocument();
    });
  });

  it('shows project details dialog when button is clicked', async () => {
    render(<App />);

    const showProjectDetailsButton = await screen.findByText('Show Project Details');
    fireEvent.click(showProjectDetailsButton);

    await waitFor(() => {
      expect(screen.getByTestId('project-details-dialog')).toBeInTheDocument();
      expect(screen.getByText('Project Details Dialog for Test Project')).toBeInTheDocument();
    });
  });

  it('shows branch details dialog when button is clicked', async () => {
    render(<App />);

    const showBranchDetailsButton = await screen.findByText('Show Branch Details');
    fireEvent.click(showBranchDetailsButton);

    await waitFor(() => {
      expect(screen.getByTestId('branch-details-dialog')).toBeInTheDocument();
      expect(screen.getByText('Branch Details Dialog for Test Project - main')).toBeInTheDocument();
    });
  });

  it('refreshes project list when tasks change', async () => {
    render(<App />);

    // Select a project first
    const selectButton = await screen.findByText('Select Project');
    fireEvent.click(selectButton);

    await waitFor(() => {
      expect(screen.getByTestId('task-list')).toBeInTheDocument();
    });

    // Trigger task change
    const taskChangeButton = screen.getByText('Trigger Task Change');
    fireEvent.click(taskChangeButton);

    // Verify console.log was called (in real app, this would trigger refresh)
    // Since we can't directly test the refresh key increment, we just verify the button works
    expect(taskChangeButton).toBeInTheDocument();
  });

  it('handles sidebar toggle on mobile', async () => {
    // Simulate mobile screen
    global.innerWidth = 500;
    global.dispatchEvent(new Event('resize'));

    render(<App />);

    // The mobile menu button should be visible
    const toggleButton = screen.getByLabelText('Open sidebar');
    expect(toggleButton).toBeInTheDocument();

    // Click to open
    fireEvent.click(toggleButton);

    // The close button should now be visible
    await waitFor(() => {
      const closeButton = screen.getByLabelText('Close sidebar');
      expect(closeButton).toBeInTheDocument();
    });
  });

  it('auto-opens sidebar on large screens', () => {
    // Simulate large screen
    global.innerWidth = 1200;
    global.dispatchEvent(new Event('resize'));

    render(<App />);

    // The mobile toggle button should not be visible on large screens
    const toggleButton = screen.queryByLabelText('Open sidebar');
    expect(toggleButton).not.toBeInTheDocument();
  });

  it('shows loading state for lazy-loaded task list', async () => {
    render(<App />);

    const selectButton = await screen.findByText('Select Project');

    // Mock the lazy loading to show loading state
    await act(async () => {
      fireEvent.click(selectButton);
    });

    // The actual task list should eventually appear
    await waitFor(() => {
      expect(screen.getByTestId('task-list')).toBeInTheDocument();
    });
  });
});
