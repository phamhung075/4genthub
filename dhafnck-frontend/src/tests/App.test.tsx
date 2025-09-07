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

// Mock the auth context
vi.mock('../contexts/AuthContext', () => ({
  AuthContext: {
    Provider: ({ children }: { children: React.ReactNode }) => children,
    Consumer: ({ children }: any) => children({
      user: { id: '123', username: 'testuser', email: 'test@example.com', roles: ['user'] },
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
    })
  }
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

vi.mock('../contexts/ThemeContext', () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>
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
      expect(window.location.pathname).toBe('/dashboard');
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
    expect(screen.getByText('Select a project and branch to see tasks.')).toBeInTheDocument();
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