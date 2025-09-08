import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import App from '../App';

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  ...vi.importActual('react-router-dom'),
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Routes: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Route: ({ element }: { element: React.ReactNode }) => <>{element}</>,
  Navigate: ({ to }: { to: string }) => <div>Navigate to {to}</div>,
  useNavigate: () => vi.fn(),
  useLocation: () => ({ pathname: '/' }),
  useParams: () => ({})
}));

// Mock the theme context
vi.mock('../contexts/ThemeContext', () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>
}));

// Mock the toast provider
vi.mock('../components/ui/toast', () => ({
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>
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
  default: ({ open, onOpenChange }: any) => open ? <div data-testid="global-context-dialog">Global Context Dialog</div> : null
}));

vi.mock('../components/ProjectDetailsDialog', () => ({
  default: ({ open, onOpenChange }: any) => open ? <div data-testid="project-details-dialog">Project Details Dialog</div> : null
}));

vi.mock('../components/BranchDetailsDialog', () => ({
  default: ({ open, onOpenChange }: any) => open ? <div data-testid="branch-details-dialog">Branch Details Dialog</div> : null
}));

vi.mock('../components/ProjectList', () => ({
  default: ({ onSelect }: any) => (
    <div data-testid="project-list">
      <button onClick={() => onSelect('project1', 'branch1')}>Select Project</button>
    </div>
  )
}));

vi.mock('../components/LazyTaskList', () => ({
  default: ({ projectId, taskTreeId }: any) => (
    <div data-testid="task-list">
      Task List for {projectId} - {taskTreeId}
    </div>
  )
}));

describe('App', () => {
  beforeEach(() => {
    // Reset window.location before each test
    window.history.pushState({}, '', '/');
  });

  it('renders without crashing', () => {
    render(<App />);
  });

  it('redirects to dashboard from root path', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Navigate to /dashboard')).toBeInTheDocument();
    });
  });

  it('renders login form on /login route', () => {
    window.history.pushState({}, '', '/login');
    
    render(
      <App />
    );

    expect(screen.getByText('Login Form')).toBeInTheDocument();
  });

  it('renders signup form on /signup route', () => {
    window.history.pushState({}, '', '/signup');
    
    render(
      <App />
    );

    expect(screen.getByText('Signup Form')).toBeInTheDocument();
  });

  it('renders email verification on /auth/verify route', () => {
    window.history.pushState({}, '', '/auth/verify');
    
    render(
      <App />
    );

    expect(screen.getByText('Email Verification')).toBeInTheDocument();
  });

  it('renders dashboard with header and project list on /dashboard route', () => {
    window.history.pushState({}, '', '/dashboard');
    
    render(
      <App />
    );

    expect(screen.getByText('Test Header')).toBeInTheDocument();
    expect(screen.getByTestId('project-list')).toBeInTheDocument();
    expect(screen.getByText('Choose a workspace')).toBeInTheDocument();
    expect(screen.getByText('Select a project and branch from the sidebar to start viewing and managing your tasks.')).toBeInTheDocument();
  });

  it('renders registration success on /registration-success route', () => {
    window.history.pushState({}, '', '/registration-success');
    
    render(
      <App />
    );

    expect(screen.getByText('Registration Success')).toBeInTheDocument();
  });

  it('renders profile page with AppLayout on /profile route', () => {
    window.history.pushState({}, '', '/profile');
    
    render(
      <App />
    );

    expect(screen.getByTestId('app-layout')).toBeInTheDocument();
    expect(screen.getByText('Profile Page')).toBeInTheDocument();
  });

  it('renders token management page on /tokens route', () => {
    window.history.pushState({}, '', '/tokens');
    
    render(
      <App />
    );

    expect(screen.getByText('Token Management Page')).toBeInTheDocument();
  });
});