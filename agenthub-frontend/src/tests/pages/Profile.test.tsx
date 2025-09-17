import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { Profile } from '../../pages/Profile';
import { AuthContext } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

// Mock react-router-dom
vi.mock('react-router-dom');
const mockNavigate = vi.fn();

// Mock useTheme hook
vi.mock('../../hooks/useTheme', () => ({
  useTheme: () => ({
    theme: 'light',
    setTheme: vi.fn(),
    toggleTheme: vi.fn(),
  }),
}));

// Mock window.alert
global.alert = vi.fn();

describe('Profile', () => {
  const mockUser = {
    id: '123',
    username: 'John Doe',
    email: 'john@example.com',
    roles: ['user', 'admin']
  };

  const renderWithAuth = (user = mockUser) => {
    return render(
      <AuthContext.Provider value={{
        user,
        isAuthenticated: !!user,
        login: vi.fn(),
        logout: vi.fn(),
        loading: false,
        refreshUser: vi.fn(),
      }}>
        <Profile />
      </AuthContext.Provider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
    (useNavigate as ReturnType<typeof vi.fn>).mockReturnValue(mockNavigate);
  });

  it('renders loading state when context is not available', () => {
    render(<Profile />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders login prompt when user is not authenticated', () => {
    renderWithAuth(null);
    expect(screen.getByText('Please log in to view your profile.')).toBeInTheDocument();
  });

  it('renders profile page with user information', () => {
    renderWithAuth();
    
    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByText('Manage your account settings and preferences')).toBeInTheDocument();
    expect(screen.getByText('JD')).toBeInTheDocument(); // Initials
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
  });

  it('displays user roles correctly', () => {
    renderWithAuth();
    
    expect(screen.getByText('user')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
  });

  it('renders all three tabs', () => {
    renderWithAuth();
    
    expect(screen.getByRole('button', { name: /Account/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Security/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Preferences/i })).toBeInTheDocument();
  });

  it('switches between tabs correctly', () => {
    renderWithAuth();
    
    // Initially on Account tab
    expect(screen.getByText('Account Information')).toBeInTheDocument();
    
    // Click Security tab
    fireEvent.click(screen.getByRole('button', { name: /Security/i }));
    expect(screen.getByText('Security Settings')).toBeInTheDocument();
    expect(screen.queryByText('Account Information')).not.toBeInTheDocument();
    
    // Click Preferences tab
    fireEvent.click(screen.getByRole('button', { name: /Preferences/i }));
    expect(screen.getByText('Customize your application experience')).toBeInTheDocument();
    expect(screen.queryByText('Security Settings')).not.toBeInTheDocument();
  });

  it('enables edit mode when Edit Profile button is clicked', () => {
    renderWithAuth();
    
    const editButton = screen.getByRole('button', { name: /Edit Profile/i });
    fireEvent.click(editButton);
    
    // Should show Save and Cancel buttons
    expect(screen.getByRole('button', { name: /Save/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Edit Profile/i })).not.toBeInTheDocument();
    
    // Input fields should be enabled
    const usernameInput = screen.getByLabelText(/Username/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    expect(usernameInput).not.toBeDisabled();
    expect(emailInput).not.toBeDisabled();
  });

  it('cancels edit mode and reverts changes', () => {
    renderWithAuth();
    
    // Enter edit mode
    fireEvent.click(screen.getByRole('button', { name: /Edit Profile/i }));
    
    // Change username
    const usernameInput = screen.getByLabelText(/Username/i) as HTMLInputElement;
    fireEvent.change(usernameInput, { target: { value: 'New Name' } });
    expect(usernameInput.value).toBe('New Name');
    
    // Cancel
    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }));
    
    // Should exit edit mode and revert changes
    expect(screen.getByRole('button', { name: /Edit Profile/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Save/i })).not.toBeInTheDocument();
    expect(usernameInput.value).toBe('John Doe');
    expect(usernameInput).toBeDisabled();
  });

  it('saves profile changes', async () => {
    renderWithAuth();
    
    // Enter edit mode
    fireEvent.click(screen.getByRole('button', { name: /Edit Profile/i }));
    
    // Change username and email
    const usernameInput = screen.getByLabelText(/Username/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    fireEvent.change(usernameInput, { target: { value: 'Jane Doe' } });
    fireEvent.change(emailInput, { target: { value: 'jane@example.com' } });
    
    // Save
    fireEvent.click(screen.getByRole('button', { name: /Save/i }));
    
    // Should show success alert and exit edit mode
    await waitFor(() => {
      expect(global.alert).toHaveBeenCalledWith('Profile updated successfully!');
    });
    expect(screen.getByRole('button', { name: /Edit Profile/i })).toBeInTheDocument();
  });

  it('displays correct initials for different name formats', () => {
    // Single name
    renderWithAuth({ ...mockUser, username: 'Alice' });
    expect(screen.getByText('AL')).toBeInTheDocument();
  });

  it('renders security tab content correctly', () => {
    renderWithAuth();
    
    fireEvent.click(screen.getByRole('button', { name: /Security/i }));
    
    expect(screen.getByText('Manage API Tokens')).toBeInTheDocument();
    expect(screen.getByText('Change Password')).toBeInTheDocument();
    expect(screen.getByText('Enable Two-Factor Authentication')).toBeInTheDocument();
    expect(screen.getByText('Manage Sessions')).toBeInTheDocument();
    expect(screen.getByText('About API Tokens')).toBeInTheDocument();
    expect(screen.getByText(/API tokens allow you to authenticate/)).toBeInTheDocument();
  });

  it('navigates to token management page when Manage API Tokens is clicked', () => {
    renderWithAuth();
    
    fireEvent.click(screen.getByRole('button', { name: /Security/i }));
    
    const manageTokensButton = screen.getByRole('button', { name: /Manage API Tokens/i });
    fireEvent.click(manageTokensButton);
    
    expect(mockNavigate).toHaveBeenCalledWith('/tokens');
  });

  it('navigates to token management from the API tokens info section', () => {
    renderWithAuth();
    
    fireEvent.click(screen.getByRole('button', { name: /Security/i }));
    
    const tokenLink = screen.getByRole('button', { name: /Go to Token Management/i });
    fireEvent.click(tokenLink);
    
    expect(mockNavigate).toHaveBeenCalledWith('/tokens');
  });

  it('renders preferences tab content correctly', () => {
    renderWithAuth();
    
    fireEvent.click(screen.getByRole('button', { name: /Preferences/i }));
    
    expect(screen.getByText('Appearance')).toBeInTheDocument();
    expect(screen.getByText('Theme Preference')).toBeInTheDocument();
    expect(screen.getByText('Light Mode')).toBeInTheDocument();
    expect(screen.getByText('Dark Mode')).toBeInTheDocument();
    expect(screen.getByText('Email Notifications')).toBeInTheDocument();
    expect(screen.getByText('Receive email notifications for important updates')).toBeInTheDocument();
  });

  it('disables preference controls when not in edit mode', () => {
    renderWithAuth();
    
    fireEvent.click(screen.getByRole('button', { name: /Preferences/i }));
    
    const notificationCheckbox = screen.getByRole('checkbox', { name: /Receive email notifications for important updates/i }) as HTMLInputElement;
    
    expect(notificationCheckbox).toBeDisabled();
  });

  it('enables preference controls in edit mode', () => {
    renderWithAuth();
    
    // Enter edit mode
    fireEvent.click(screen.getByRole('button', { name: /Edit Profile/i }));
    
    // Switch to preferences tab
    fireEvent.click(screen.getByRole('button', { name: /Preferences/i }));
    
    const notificationCheckbox = screen.getByRole('checkbox', { name: /Receive email notifications for important updates/i }) as HTMLInputElement;
    
    expect(notificationCheckbox).not.toBeDisabled();
  });

  it('allows switching between light and dark theme', () => {
    const mockSetTheme = vi.fn();
    vi.mocked(require('../../hooks/useTheme').useTheme).mockReturnValue({
      theme: 'light',
      setTheme: mockSetTheme,
      toggleTheme: vi.fn(),
    });

    renderWithAuth();
    
    fireEvent.click(screen.getByRole('button', { name: /Preferences/i }));
    
    // Click dark mode button
    const darkModeButton = screen.getByRole('button', { name: /Dark Mode/i });
    fireEvent.click(darkModeButton);
    
    expect(mockSetTheme).toHaveBeenCalledWith('dark');
  });

  it('displays user ID correctly', () => {
    renderWithAuth();
    
    const userIdInput = screen.getByDisplayValue('123');
    expect(userIdInput).toBeInTheDocument();
    expect(userIdInput).toBeDisabled();
  });
});