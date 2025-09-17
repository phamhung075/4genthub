import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import UserProfileDropdown from '../../components/UserProfileDropdown';
import { AuthContext } from '../../contexts/AuthContext';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useTheme
vi.mock('../../hooks/useTheme', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: vi.fn(),
  }),
}));

// Mock toast hook
vi.mock('../../components/ui/toast', () => ({
  useInfoToast: () => vi.fn(),
}));

describe('UserProfileDropdown', () => {
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
          <UserProfileDropdown />
        </AuthContext.Provider>
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('navigates to help page when Help & Support is clicked', () => {
    renderWithAuth();

    // Click the user button to open dropdown
    const userButton = screen.getByRole('button');
    fireEvent.click(userButton);

    // Find and click the Help & Support menu item
    const helpButton = screen.getByText('Help & Support');
    fireEvent.click(helpButton);

    // Should navigate to /help
    expect(mockNavigate).toHaveBeenCalledWith('/help');
  });

  it('displays Help & Support menu item with correct icon', () => {
    renderWithAuth();

    // Click the user button to open dropdown
    const userButton = screen.getByRole('button');
    fireEvent.click(userButton);

    // Verify Help & Support menu item is present
    expect(screen.getByText('Help & Support')).toBeInTheDocument();

    // Verify the HelpCircle icon is present (it's an SVG with specific path)
    const helpIcon = document.querySelector('svg circle[cx="12"][cy="12"][r="10"]');
    expect(helpIcon).toBeInTheDocument();
  });

  it('returns null when user is not authenticated', () => {
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
          <UserProfileDropdown />
        </AuthContext.Provider>
      </BrowserRouter>
    );

    // Should render nothing when user is null
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});