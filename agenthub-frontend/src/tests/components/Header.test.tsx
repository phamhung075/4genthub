import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { Header } from '../../components/Header';
import { AuthContext } from '../../contexts/AuthContext';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useTheme hook
vi.mock('../../hooks/useTheme', () => ({
  useTheme: () => ({
    theme: 'light',
    toggleTheme: vi.fn(),
  }),
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
    expect(screen.getByText('4genthub')).toBeInTheDocument();
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
    expect(screen.getByText('4genthub')).toBeInTheDocument();
    expect(screen.getByText('AI Orchestration Platform')).toBeInTheDocument();
  });

  it('displays user initials correctly', () => {
    renderWithAuth();
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('displays user initials for single name', () => {
    renderWithAuth({ ...mockUser, username: 'Alice' });
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('displays username on larger screens', () => {
    renderWithAuth();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('toggles dropdown menu when clicked', () => {
    renderWithAuth();

    // Dropdown items should not be visible initially
    expect(screen.queryByText('Your Profile')).not.toBeInTheDocument();
    expect(screen.queryByText('API Tokens')).not.toBeInTheDocument();
    expect(screen.queryByText('Sign Out')).not.toBeInTheDocument();

    // Click user button to open dropdown
    const userButton = screen.getByRole('button', { name: /JD/i });
    fireEvent.click(userButton);

    // Dropdown should now be visible
    expect(screen.getByText('Your Profile')).toBeInTheDocument();
    expect(screen.getByText('API Tokens')).toBeInTheDocument();
    expect(screen.getByText('Sign Out')).toBeInTheDocument();
  });

  it('closes dropdown when clicking outside', () => {
    renderWithAuth();

    // Open dropdown
    const userButton = screen.getByRole('button', { name: /JD/i });
    fireEvent.click(userButton);
    expect(screen.getByText('Your Profile')).toBeInTheDocument();

    // Click outside (on the overlay)
    const overlay = document.querySelector('.fixed.inset-0');
    fireEvent.click(overlay!);

    // Dropdown should be closed
    expect(screen.queryByText('Your Profile')).not.toBeInTheDocument();
  });

  it('navigates to profile when profile link is clicked', () => {
    renderWithAuth();

    // Open dropdown
    const userButton = screen.getByRole('button', { name: /JD/i });
    fireEvent.click(userButton);

    // Click profile link
    const profileLink = screen.getByText('Your Profile');
    fireEvent.click(profileLink);

    // Dropdown should close
    expect(screen.queryByText('Your Profile')).not.toBeInTheDocument();
  });

  it('handles logout correctly', async () => {
    renderWithAuth();

    // Open dropdown
    const userButton = screen.getByRole('button', { name: /JD/i });
    fireEvent.click(userButton);

    // Click sign out
    const signOutButton = screen.getByText('Sign Out');
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
    expect(screen.getByText('4genthub')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /JD/i })).not.toBeInTheDocument();
  });

  it('renders theme toggle in menu for authenticated users', () => {
    renderWithAuth();
    // Theme toggle should be present in the menu items (as Dark/Light button)
    expect(screen.getAllByText('Dark').length).toBeGreaterThan(0);
  });

  it('renders theme toggle in menu for non-authenticated users', () => {
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

    // Theme toggle should be present in the menu for non-auth users too
    expect(screen.getAllByText('Dark').length).toBeGreaterThan(0);
  });
});