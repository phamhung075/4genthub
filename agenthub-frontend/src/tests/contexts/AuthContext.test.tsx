import React from 'react';
import { render, screen, act, waitFor } from './../test-utils';
import { AuthProvider, AuthContext } from '../../contexts/AuthContext';
import { API_BASE_URL } from '../../config/environment';
import { useContext } from 'react';
import Cookies from 'js-cookie';
import * as jwtDecode from 'jwt-decode';

// Mock dependencies
vi.mock('js-cookie');
vi.mock('jwt-decode');
vi.mock('../../hooks/useWebSocketV2');

// Mock fetch
global.fetch = vi.fn();

// Mock useWebSocket hook
const mockDisconnect = vi.fn();
const mockUseWebSocket = vi.fn(() => ({
  isConnected: false,
  disconnect: mockDisconnect
}));

// Mock import.meta.env and API_BASE_URL
(import.meta as any).env = { 
  MODE: 'test'
};

vi.mock('../../config/environment', () => ({
  API_BASE_URL: 'http://test-api.com'
}));

// Import useWebSocket mock after mocking
import { useWebSocket } from '../../hooks/useWebSocketV2';
(useWebSocket as any).mockImplementation(mockUseWebSocket);

describe('AuthContext', () => {
  const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
    username: 'testuser',
    roles: ['user']
  };

  const mockTokens = {
    access_token: 'mock-access-token',
    refresh_token: 'mock-refresh-token'
  };

  const mockDecodedToken = {
    sub: 'user-123',
    email: 'test@example.com',
    username: 'testuser',
    roles: ['user'],
    exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
    iat: Math.floor(Date.now() / 1000),
    type: 'access'
  };

  // Helper component to access context values
  const TestComponent = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error('AuthContext not provided');
    
    return (
      <div>
        <div data-testid="user">{context.user ? context.user.email : 'none'}</div>
        <div data-testid="is-authenticated">{String(context.isAuthenticated)}</div>
        <div data-testid="is-loading">{String(context.isLoading)}</div>
        <button onClick={() => context.logout()}>Logout</button>
        <button onClick={() => context.login('test@example.com', 'password')}>Login</button>
        <button onClick={() => context.signup('new@example.com', 'newuser', 'password')}>Signup</button>
        <button onClick={() => context.refreshToken()}>Refresh</button>
        <button onClick={() => context.setTokens(mockTokens)}>Set Tokens</button>
      </div>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockDisconnect.mockClear();
    mockUseWebSocket.mockClear();
    (Cookies.get as any).mockReset();
    (Cookies.set as any).mockReset();
    (Cookies.remove as any).mockReset();
    (jwtDecode.jwtDecode as any).mockReset();
    (global.fetch as any).mockReset();
  });

  describe('Initial State', () => {
    it('should initialize with loading state', () => {
      (Cookies.get as any).mockReturnValue(null);
      
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      expect(screen.getByTestId('user')).toHaveTextContent('none');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    });

    it('should restore user from existing valid tokens', async () => {
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });
    });

    it('should handle expired token on mount', async () => {
      const expiredToken = {
        ...mockDecodedToken,
        exp: Math.floor(Date.now() / 1000) - 3600 // Expired 1 hour ago
      };

      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (jwtDecode.jwtDecode as any).mockReturnValueOnce(expiredToken);

      // Mock successful token refresh
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token'
        })
      });

      // Return valid token after refresh
      (jwtDecode.jwtDecode as any).mockReturnValueOnce(mockDecodedToken);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://test-api.com/api/auth/refresh',
          expect.objectContaining({
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ refresh_token: mockTokens.refresh_token })
          })
        );
      });
    });
  });

  describe('Login', () => {
    it('should login successfully', async () => {
      (Cookies.get as any).mockReturnValue(null);
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);
      
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          access_token: mockTokens.access_token,
          refresh_token: mockTokens.refresh_token
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await act(async () => {
        getByText('Login').click();
      });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://test-api.com/api/auth/login',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
              email: 'test@example.com',
              password: 'password'
            })
          }
        );
      });

      expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');

      // Check tokens were stored
      expect(Cookies.set).toHaveBeenCalledWith(
        'access_token',
        mockTokens.access_token,
        expect.objectContaining({
          expires: 7,
          sameSite: 'strict',
          secure: false
        })
      );
    });

    it('should handle login failure', async () => {
      (Cookies.get as any).mockReturnValue(null);
      
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({
          detail: 'Invalid credentials'
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(async () => {
        await act(async () => {
          getByText('Login').click();
        });
      }).rejects.toThrow('Invalid credentials');
    });

    it('should handle email verification required error', async () => {
      (Cookies.get as any).mockReturnValue(null);
      
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => ({
          detail: 'Email not verified'
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(async () => {
        await act(async () => {
          getByText('Login').click();
        });
      }).rejects.toThrow('Please verify your email before signing in. Check your inbox for the verification link.');
    });

    it('should handle email verification response', async () => {
      (Cookies.get as any).mockReturnValue(null);
      
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          requires_email_verification: true
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(async () => {
        await act(async () => {
          getByText('Login').click();
        });
      }).rejects.toThrow('Please verify your email before signing in. Check your inbox for the verification link.');
    });
  });

  describe('Signup', () => {
    it('should signup and require email verification', async () => {
      (Cookies.get as any).mockReturnValue(null);
      
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          requires_email_verification: true,
          message: 'Please check your email to verify your account'
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      let result;
      await act(async () => {
        const authContext = (AuthProvider as any).Consumer._currentValue;
        result = await authContext.signup('new@example.com', 'newuser', 'password');
      });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api.com/api/auth/register',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify({
            email: 'new@example.com',
            password: 'password',
            username: 'newuser',
            full_name: 'newuser'
          })
        }
      );

      // User should not be logged in when email verification is required
      expect(screen.getByTestId('user')).toHaveTextContent('none');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    });

    it('should signup and auto-login when no verification required', async () => {
      (Cookies.get as any).mockReturnValue(null);
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);
      
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          access_token: mockTokens.access_token,
          refresh_token: mockTokens.refresh_token
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await act(async () => {
        getByText('Signup').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
      });
    });

    it('should handle signup failure', async () => {
      (Cookies.get as any).mockReturnValue(null);
      
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          detail: 'Email already exists'
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(async () => {
        await act(async () => {
          getByText('Signup').click();
        });
      }).rejects.toThrow('Email already exists');
    });
  });

  describe('Logout', () => {
    it('should clear user and tokens on logout', async () => {
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      act(() => {
        getByText('Logout').click();
      });

      expect(screen.getByTestId('user')).toHaveTextContent('none');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      
      expect(Cookies.remove).toHaveBeenCalledWith('access_token');
      expect(Cookies.remove).toHaveBeenCalledWith('refresh_token');
    });
    
    it('should disconnect WebSocket on logout', async () => {
      // Mock WebSocket as connected
      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        disconnect: mockDisconnect
      });
      
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      act(() => {
        getByText('Logout').click();
      });

      expect(mockDisconnect).toHaveBeenCalled();
      expect(screen.getByTestId('user')).toHaveTextContent('none');
      expect(Cookies.remove).toHaveBeenCalledWith('access_token');
      expect(Cookies.remove).toHaveBeenCalledWith('refresh_token');
    });
  });

  describe('Token Refresh', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('should refresh token successfully', async () => {
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token'
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await act(async () => {
        getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://test-api.com/api/auth/refresh',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
              refresh_token: mockTokens.refresh_token
            })
          }
        );
      });

      expect(Cookies.set).toHaveBeenCalledWith(
        'access_token',
        'new-access-token',
        expect.any(Object)
      );
    });

    it('should logout on refresh failure', async () => {
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({
          detail: 'Invalid refresh token'
        })
      });

      await act(async () => {
        try {
          await getByText('Refresh').click();
        } catch (error) {
          // Expected to throw
        }
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('none');
        expect(Cookies.remove).toHaveBeenCalledWith('access_token');
        expect(Cookies.remove).toHaveBeenCalledWith('refresh_token');
      });
    });

    it('should disconnect WebSocket on token refresh failure', async () => {
      // Mock WebSocket as connected
      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        disconnect: mockDisconnect
      });
      
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid refresh token' })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await act(async () => {
        try {
          await getByText('Refresh').click();
        } catch (error) {
          // Expected to throw
        }
      });

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it('should automatically refresh token before expiry', async () => {
      const nearExpiryToken = {
        ...mockDecodedToken,
        exp: Math.floor(Date.now() / 1000) + 120 // Expires in 2 minutes
      };

      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (jwtDecode.jwtDecode as any).mockReturnValue(nearExpiryToken);

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'refreshed-access-token',
          refresh_token: 'refreshed-refresh-token'
        })
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Fast-forward to 1 minute before expiry
      await act(async () => {
        jest.advanceTimersByTime(60 * 1000);
      });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://test-api.com/api/auth/refresh',
          expect.any(Object)
        );
      });
    });
  });

  describe('setTokens', () => {
    it('should set tokens and decode user', async () => {
      (Cookies.get as any).mockReturnValue(null);
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      act(() => {
        getByText('Set Tokens').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
      });

      expect(Cookies.set).toHaveBeenCalledWith(
        'access_token',
        mockTokens.access_token,
        expect.objectContaining({
          expires: 7,
          sameSite: 'strict',
          secure: false // test mode
        })
      );

      expect(Cookies.set).toHaveBeenCalledWith(
        'refresh_token',
        mockTokens.refresh_token,
        expect.objectContaining({
          expires: 30,
          sameSite: 'strict',
          secure: false
        })
      );
    });

    it('should use secure cookies in production', async () => {
      // Mock production environment
      (import.meta as any).env.MODE = 'production';
      
      (Cookies.get as any).mockReturnValue(null);
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      act(() => {
        getByText('Set Tokens').click();
      });

      await waitFor(() => {
        expect(Cookies.set).toHaveBeenCalledWith(
          'access_token',
          mockTokens.access_token,
          expect.objectContaining({
            secure: true
          })
        );
      });

      // Reset environment
      (import.meta as any).env.MODE = 'test';
    });
  });

  describe('Token Decoding', () => {
    it('should handle malformed tokens', async () => {
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return 'malformed-token';
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (jwtDecode.jwtDecode as any).mockImplementation(() => {
        throw new Error('Invalid token');
      });

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation();

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('none');
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      });

      expect(consoleErrorSpy).toHaveBeenCalledWith('Error decoding token:', expect.any(Error));
      
      consoleErrorSpy.mockRestore();
    });

    it('should extract username from email if not in token', async () => {
      const tokenWithoutUsername = {
        ...mockDecodedToken,
        username: undefined
      };

      (Cookies.get as any).mockReturnValue(null);
      (jwtDecode.jwtDecode as any).mockReturnValue(tokenWithoutUsername);

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          access_token: mockTokens.access_token,
          refresh_token: mockTokens.refresh_token
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await act(async () => {
        getByText('Login').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      // The user should have username derived from email
      const authContext = (AuthProvider as any).Consumer._currentValue;
      expect(authContext.user.username).toBe('test');
    });

    it('should use default roles if not in token', async () => {
      const tokenWithoutRoles = {
        ...mockDecodedToken,
        roles: undefined
      };

      (Cookies.get as any).mockReturnValue(null);
      (jwtDecode.jwtDecode as any).mockReturnValue(tokenWithoutRoles);

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          access_token: mockTokens.access_token,
          refresh_token: mockTokens.refresh_token
        })
      });

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await act(async () => {
        getByText('Login').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      // The user should have default roles
      const authContext = (AuthProvider as any).Consumer._currentValue;
      expect(authContext.user.roles).toEqual(['user']);
    });
  });

  describe('Event Listeners', () => {
    it('should handle logout event from API layer', async () => {
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      const { container } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      // Dispatch auth-logout event
      const logoutEvent = new Event('auth-logout');
      window.dispatchEvent(logoutEvent);

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('none');
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
        expect(Cookies.remove).toHaveBeenCalledWith('access_token');
        expect(Cookies.remove).toHaveBeenCalledWith('refresh_token');
      });
    });
  });

  describe('Context Access', () => {
    it('should throw error when AuthContext is used without provider', () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation();

      expect(() => {
        render(<TestComponent />);
      }).toThrow('AuthContext not provided');

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Error Handling', () => {
    it('should console error on login failure', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation();
      
      (Cookies.get as any).mockReturnValue(null);
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(async () => {
        await act(async () => {
          getByText('Login').click();
        });
      }).rejects.toThrow('Network error');

      expect(consoleErrorSpy).toHaveBeenCalledWith('Login error:', expect.any(Error));
      
      consoleErrorSpy.mockRestore();
    });

    it('should console error on signup failure', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation();
      
      (Cookies.get as any).mockReturnValue(null);
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(async () => {
        await act(async () => {
          getByText('Signup').click();
        });
      }).rejects.toThrow('Network error');

      expect(consoleErrorSpy).toHaveBeenCalledWith('Signup error:', expect.any(Error));
      
      consoleErrorSpy.mockRestore();
    });

    it('should console error on token refresh failure', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation();
      
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });
      
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(async () => {
        await act(async () => {
          getByText('Refresh').click();
        });
      }).rejects.toThrow('Network error');

      expect(consoleErrorSpy).toHaveBeenCalledWith('Token refresh error:', expect.any(Error));
      
      consoleErrorSpy.mockRestore();
    });
  });
});