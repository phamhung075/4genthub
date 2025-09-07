import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { Header } from '../../components/Header';
import { AuthContext } from '../../contexts/AuthContext';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  ...vi.importActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Mock ThemeToggle component
vi.mock('../../components/ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle">Theme Toggle</div>
}));

describe('Header', () => {
  const mockUser = {
    id: '123',
    username: 'John Doe',
    email: 'john@example.com',
    roles: ['user']
  };

  const mockLogout = vi.fn();

  const renderWithAuth = (user = mockUser) => {
    return render(
      <BrowserRouter>
        <AuthContext.Provider value={{
          user,
          isAuthenticated: !!user,
          login: vi.fn(),
          logout: mockLogout,
          loading: false,
          refreshUser: vi.fn(),
        }}>
          <Header />
        </AuthContext.Provider>
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing when authenticated', () => {
    renderWithAuth();
    expect(screen.getByText('DhafnckMCP')).toBeInTheDocument();
  });

  it('returns null when AuthContext is not available', () => {
    const { container } = render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
    expect(container.firstChild).toBeNull();
  });

  it('displays the application title and tagline', () => {
    renderWithAuth();
    expect(screen.getByText('DhafnckMCP')).toBeInTheDocument();
    expect(screen.getByText('Multi-Project AI Orchestration Platform')).toBeInTheDocument();
  });

  it('displays user initials correctly', () => {
    renderWithAuth();
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('displays user initials for single name', () => {
    renderWithAuth({ ...mockUser, username: 'Alice' });
    expect(screen.getByText('AL')).toBeInTheDocument();
  });

  it('displays username on larger screens', () => {
    renderWithAuth();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('toggles dropdown menu when clicked', () => {
    renderWithAuth();
    
    // Dropdown should not be visible initially
    expect(screen.queryByText('john@example.com')).not.toBeInTheDocument();
    
    // Click user button to open dropdown
    const userButton = screen.getByRole('button', { name: /JD/i });
    fireEvent.click(userButton);
    
    // Dropdown should now be visible
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByText('API Tokens')).toBeInTheDocument();
    expect(screen.getByText('Sign Out')).toBeInTheDocument();
  });

  it('closes dropdown when clicking outside', () => {
    renderWithAuth();
    
    // Open dropdown
    const userButton = screen.getByRole('button', { name: /JD/i });
    fireEvent.click(userButton);
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    
    // Click outside (on the overlay)
    const overlay = document.querySelector('.fixed.inset-0');
    fireEvent.click(overlay!);
    
    // Dropdown should be closed
    expect(screen.queryByText('john@example.com')).not.toBeInTheDocument();
  });

  it('navigates to profile when profile link is clicked', () => {
    renderWithAuth();
    
    // Open dropdown
    const userButton = screen.getByRole('button', { name: /JD/i });
    fireEvent.click(userButton);
    
    // Click profile link
    const profileLink = screen.getByRole('link', { name: /Profile/i });
    fireEvent.click(profileLink);
    
    // Dropdown should close
    expect(screen.queryByText('john@example.com')).not.toBeInTheDocument();
  });

  it('handles logout correctly', async () => {
    renderWithAuth();
    
    // Open dropdown
    const userButton = screen.getByRole('button', { name: /JD/i });
    fireEvent.click(userButton);
    
    // Click sign out
    const signOutButton = screen.getByRole('button', { name: /Sign Out/i });
    fireEvent.click(signOutButton);
    
    // Should call logout and navigate
    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('renders navigation icons on desktop', () => {
    renderWithAuth();
    
    // Should have home, tokens, and settings icons
    const navLinks = screen.getAllByRole('link');
    const homeLink = navLinks.find(link => link.getAttribute('href') === '/dashboard');
    const tokensLink = navLinks.find(link => link.getAttribute('href') === '/tokens');
    const profileLink = navLinks.find(link => link.getAttribute('href') === '/profile');
    
    expect(homeLink).toBeInTheDocument();
    expect(tokensLink).toBeInTheDocument();
    expect(profileLink).toBeInTheDocument();
  });

  it('shows mobile dashboard link in dropdown on small screens', () => {
    renderWithAuth();
    
    // Open dropdown
    const userButton = screen.getByRole('button', { name: /JD/i });
    fireEvent.click(userButton);
    
    // Should have dashboard link in dropdown (for mobile)
    const dashboardLinks = screen.getAllByText('Dashboard');
    expect(dashboardLinks.length).toBeGreaterThan(0);
  });

  it('does not render user section when user is null', () => {
    render(
      <BrowserRouter>
        <AuthContext.Provider value={{
          user: null,
          isAuthenticated: false,
          login: vi.fn(),
          logout: mockLogout,
          loading: false,
          refreshUser: vi.fn(),
        }}>
          <Header />
        </AuthContext.Provider>
      </BrowserRouter>
    );

    // Should still show title but no user section
    expect(screen.getByText('DhafnckMCP')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /JD/i })).not.toBeInTheDocument();
  });

  it('renders theme toggle for authenticated users', () => {
    renderWithAuth();
    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
  });

  it('renders theme toggle for non-authenticated users', () => {
    render(
      <BrowserRouter>
        <AuthContext.Provider value={{
          user: null,
          isAuthenticated: false,
          login: vi.fn(),
          logout: mockLogout,
          loading: false,
          refreshUser: vi.fn(),
        }}>
          <Header />
        </AuthContext.Provider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
  });
});