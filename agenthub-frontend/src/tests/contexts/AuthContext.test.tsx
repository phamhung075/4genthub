import React from 'react';
import { render, screen, act, waitFor, fireEvent } from './../test-utils';
import { render as rtlRender } from '@testing-library/react';
import { AuthProvider, useAuth } from '../../contexts/AuthContext';
import type { JWTPayload } from '../../types/authTypes';
import { API_BASE_URL } from '../../config/environment';
import Cookies from 'js-cookie';
import * as jwtDecode from 'jwt-decode';
import logger from '../../utils/logger';

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
import { useNotificationStore } from '../../store/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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

  // Captures the context value produced by the *rendered* AuthProvider so tests
  // can await the provider's real async handlers instead of relying on a DOM click
  // handler that discards the returned promise.
  let authContext: ReturnType<typeof useAuth> | null = null;

  // Helper component to access context values
  const TestComponent = () => {
    const context = useAuth();
    authContext = context;

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
    authContext = null;
    useNotificationStore.getState().reset();
    mockDisconnect.mockClear();
    mockUseWebSocket.mockClear();
    (Cookies.get as any).mockReset();
    (Cookies.set as any).mockReset();
    (Cookies.remove as any).mockReset();
    (jwtDecode.jwtDecode as any).mockReset();
    (global.fetch as any).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
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

    // MEASURED DEFECT (dashboard-token row): a minted API token decodes, so the app built a username
    // from its email claim, threw, and returned null exactly like an expired token; the mount path
    // then refreshed, the refresh failed, and logout() cleared both cookies - every request after
    // that 403 and the user told nothing. The guard reports the refusal and leaves the credentials
    // alone. Both cases also fail if the silent logout path returns, because that path removes both
    // cookies and POSTs /api/auth/refresh.
    const expectStoredTokenRefused = async (claims: Record<string, unknown>, reason: RegExp) => {
      vi.mocked(Cookies.get).mockImplementation((key?: string) => {
        if (key === 'access_token') return 'stored-token';
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return undefined;
      });
      // These payloads deliberately step outside JWTPayload: what a token the declared shape does not
      // describe does at runtime is the subject of the case.
      vi.mocked(jwtDecode.jwtDecode).mockReturnValue(claims as unknown as JWTPayload);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Settle the mount path, including any refresh a missing guard would have started.
      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });
      await act(async () => {
        await Promise.resolve();
      });

      // The silent logout path clears both cookies and POSTs /api/auth/refresh: neither happens.
      expect(Cookies.remove).not.toHaveBeenCalled();
      expect(global.fetch).not.toHaveBeenCalledWith(
        `${API_BASE_URL}/api/auth/refresh`,
        expect.anything()
      );
      // Not signed in, and told why rather than logged out with no reason.
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      expect(authContext!.authError).toMatch(reason);
    };

    // The DECLARATION path: the mint endpoint writes type "api_token" (jwt_service.go GenerateToken),
    // so the refusal names what the token says it is instead of inferring from a missing claim.
    it('refuses a token that declares type api_token and names the declaration', async () => {
      await expectStoredTokenRefused(
        {
          sub: 'user-123',
          scopes: ['read'],
          type: 'api_token',
          exp: Math.floor(Date.now() / 1000) + 3600
        },
        /declares type "api_token"/i
      );
    });

    // The INFERENCE path: no declaration and no identity claim either, so the wording must say it
    // reasoned from absence rather than naming a token type it was never told.
    it('refuses a token with neither a declared type nor an email claim', async () => {
      await expectStoredTokenRefused(
        { sub: 'user-123', exp: Math.floor(Date.now() / 1000) + 3600 },
        /carries no email claim and declares no type/i
      );
    });

    // The access cookie is written for 7 days and the refresh cookie for 30 (setTokens), so a user who
    // never signed out can arrive holding ONLY the refresh cookie. That is the case the refresh
    // endpoint exists for: the session is restored instead of the user being asked to sign in again.
    it('restores a session from a refresh cookie when the access cookie is gone', async () => {
      vi.mocked(Cookies.get).mockImplementation((key?: string) =>
        key === 'refresh_token' ? 'live-refresh-token' : undefined
      );
      vi.mocked(Cookies.set).mockImplementation((key: string, value: string) => {
        void key;
        return value;
      });
      // The body the client reads from the refresh endpoint; a stand-in for Response, not one.
      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => ({ access_token: 'restored-access', refresh_token: 'restored-refresh' })
      } as unknown as Response);
      vi.mocked(jwtDecode.jwtDecode).mockReturnValue(mockDecodedToken);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
      });
      expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/auth/refresh`,
        expect.anything()
      );
    });

    it('does not attempt a refresh when neither cookie is present', async () => {
      vi.mocked(Cookies.get).mockImplementation(() => undefined);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });
      await act(async () => {
        await Promise.resolve();
      });

      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      expect(global.fetch).not.toHaveBeenCalledWith(
        `${API_BASE_URL}/api/auth/refresh`,
        expect.anything()
      );
    });

    // An explicit sign-out must keep clearing BOTH cookies, and the refresh-cookie-only branch must
    // not resurrect the session it ended. The jar models removal so "signed out" is read back through
    // Cookies.get rather than asserted by hand.
    it('an explicit sign-out clears both cookies and is not undone by a refresh', async () => {
      const removed: string[] = [];
      vi.mocked(Cookies.remove).mockImplementation((key?: string) => {
        if (key) removed.push(key);
      });
      vi.mocked(Cookies.get).mockImplementation((key?: string) => {
        if (!key || removed.includes(key)) return undefined;
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return undefined;
      });
      vi.mocked(jwtDecode.jwtDecode).mockReturnValue(mockDecodedToken);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
      await waitFor(() => {
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
      });

      fireEvent.click(screen.getByRole('button', { name: /^logout$/i }));

      await waitFor(() => {
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      });
      expect(Cookies.remove).toHaveBeenCalledWith('access_token');
      expect(Cookies.remove).toHaveBeenCalledWith('refresh_token');
      expect(Cookies.get('access_token')).toBeUndefined();
      expect(Cookies.get('refresh_token')).toBeUndefined();
      expect(global.fetch).not.toHaveBeenCalledWith(
        `${API_BASE_URL}/api/auth/refresh`,
        expect.anything()
      );
    });

    // The MOUNT's own failure path, which nothing pinned before: a refresh cookie the mount cannot use
    // is cleared and the app lands signed out, rather than retrying the dead cookie on every load.
    it('clears a refresh cookie the mount cannot use and lands signed out', async () => {
      vi.mocked(Cookies.get).mockImplementation((key?: string) =>
        key === 'refresh_token' ? 'dead-refresh-token' : undefined
      );
      vi.mocked(global.fetch).mockRejectedValue(new Error('Network error'));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });
      await act(async () => {
        await Promise.resolve();
      });

      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/auth/refresh`,
        expect.anything()
      );
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      expect(Cookies.remove).toHaveBeenCalledWith('access_token');
      expect(Cookies.remove).toHaveBeenCalledWith('refresh_token');
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

      // First decode sees the expired token; the refreshed token is decoded on
      // every subsequent call (decode after refresh + expiry-timer effect).
      (jwtDecode.jwtDecode as any)
        .mockReturnValueOnce(expiredToken)
        .mockReturnValue(mockDecodedToken);

      // Mock successful token refresh
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token'
        })
      });

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

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(
        act(async () => {
          await authContext!.login('test@example.com', 'password');
        })
      ).rejects.toThrow('Invalid credentials');
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

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(
        act(async () => {
          await authContext!.login('test@example.com', 'password');
        })
      ).rejects.toThrow('Please verify your email before signing in. Check your inbox for the verification link.');
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

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(
        act(async () => {
          await authContext!.login('test@example.com', 'password');
        })
      ).rejects.toThrow('Please verify your email before signing in. Check your inbox for the verification link.');
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

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      let result: any;
      await act(async () => {
        result = await authContext!.signup('new@example.com', 'newuser', 'password');
      });

      expect(result).toMatchObject({ requires_email_verification: true });

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

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(
        act(async () => {
          await authContext!.signup('new@example.com', 'newuser', 'password');
        })
      ).rejects.toThrow('Email already exists');
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

    it('clears the notification inbox on logout', async () => {
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

      // Notifications are addressed to an identity; a sign-out must not leave them on screen.
      useNotificationStore.getState().add({ id: 'n1', message: 'meant for this user' });
      expect(useNotificationStore.getState().notifications).toHaveLength(1);

      act(() => {
        getByText('Logout').click();
      });

      expect(useNotificationStore.getState().notifications).toHaveLength(0);
      expect(useNotificationStore.getState().unreadCount).toBe(0);
    });

    it('clears the query cache on logout', async () => {
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });

      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      queryClient.setQueryData(['seatRooms'], [{ id: 'r1', slug: 'secret', name: 'previous user room' }]);

      const { getByText } = rtlRender(
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });
      expect(queryClient.getQueryData(['seatRooms'])).toBeDefined();

      act(() => {
        getByText('Logout').click();
      });

      // The keys carry no user id, so a cache left behind would render for the next identity.
      expect(queryClient.getQueryData(['seatRooms'])).toBeUndefined();
    });

    it('clears the cache and inbox when login replaces a live session', async () => {
      // A is live (restored from cookies), then B signs in on /login without any logout: the route
      // is public and the form swaps identity with SPA navigation, so this module and the cache stay
      // mounted and nothing else would drop A's rows.
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });

      (jwtDecode.jwtDecode as any).mockImplementation((token: string) =>
        token === 'b-access-token' ? { ...mockDecodedToken, email: 'b@example.com' } : mockDecodedToken
      );

      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      queryClient.setQueryData(['seatRooms'], [{ id: 'r1', slug: 'a-private-room', name: 'A room' }]);
      useNotificationStore.getState().add({ id: 'n1', message: 'A private message', from: 'agent' });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          access_token: 'b-access-token',
          refresh_token: 'b-refresh-token'
        })
      });

      const { getByText } = rtlRender(
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      await act(async () => {
        getByText('Login').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('b@example.com');
      });

      expect(queryClient.getQueryData(['seatRooms'])).toBeUndefined();
      expect(useNotificationStore.getState().notifications).toEqual([]);
    });

    it('clears the cache and inbox when signup establishes a new identity', async () => {
      // /signup is public and auto-logs-in, so it reaches the same boundary as login.
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });

      (jwtDecode.jwtDecode as any).mockImplementation((token: string) =>
        token === 'b-access-token'
          ? { ...mockDecodedToken, sub: 'user-b', email: 'b@example.com' }
          : mockDecodedToken
      );

      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      queryClient.setQueryData(['seatRooms'], [{ id: 'r1', slug: 'a-private-room', name: 'A room' }]);
      useNotificationStore.getState().add({ id: 'n1', message: 'A private message', from: 'agent' });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          access_token: 'b-access-token',
          refresh_token: 'b-refresh-token'
        })
      });

      const { getByText } = rtlRender(
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      await act(async () => {
        getByText('Signup').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('b@example.com');
      });

      expect(queryClient.getQueryData(['seatRooms'])).toBeUndefined();
      expect(useNotificationStore.getState().notifications).toEqual([]);
    });

    it('clears the cache and inbox when a refresh returns another identity', async () => {
      // The tokens are plain same-origin document cookies shared by every tab, so a refresh fired in
      // this tab after another tab signed in as B hands this tab B's identity.
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });

      (jwtDecode.jwtDecode as any).mockImplementation((token: string) =>
        token === 'b-access-token'
          ? { ...mockDecodedToken, sub: 'user-b', email: 'b@example.com' }
          : mockDecodedToken
      );

      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      queryClient.setQueryData(['seatRooms'], [{ id: 'r1', slug: 'a-private-room', name: 'A room' }]);
      useNotificationStore.getState().add({ id: 'n1', message: 'A private message', from: 'agent' });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'b-access-token',
          refresh_token: 'b-refresh-token'
        })
      });

      const { getByText } = rtlRender(
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      await act(async () => {
        getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('b@example.com');
      });

      expect(queryClient.getQueryData(['seatRooms'])).toBeUndefined();
      expect(useNotificationStore.getState().notifications).toEqual([]);
    });

    it('keeps the cache when a refresh returns the same identity', async () => {
      // The guard must not fire on the ordinary refresh: dropping the cache every refresh window
      // would be worse than the leak it closes.
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });

      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      queryClient.setQueryData(['seatRooms'], [{ id: 'r1', slug: 'a-private-room', name: 'A room' }]);
      useNotificationStore.getState().add({ id: 'n1', message: 'A private message', from: 'agent' });

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: mockTokens.access_token,
          refresh_token: mockTokens.refresh_token
        })
      });

      const { getByText } = rtlRender(
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      await act(async () => {
        getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://test-api.com/api/auth/refresh',
          expect.objectContaining({ method: 'POST' })
        );
      });

      expect(queryClient.getQueryData(['seatRooms'])).toEqual([
        { id: 'r1', slug: 'a-private-room', name: 'A room' }
      ]);
      expect(useNotificationStore.getState().notifications).toHaveLength(1);
    });

    it('keeps refreshToken stable across a token change', async () => {
      // The guard's dependency must not churn this callback: the mount and refresh-timer effects list
      // refreshToken, and a new identity each render re-runs them (that shape already ended in a 4GB
      // heap once, via logout's deps). discardPreviousIdentity is a useCallback with only
      // useQueryClient() in it, which is provider-stable, so the array addition must be inert.
      (Cookies.get as any).mockReturnValue(null);
      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const before = authContext!.refreshToken;

      await act(async () => {
        getByText('Set Tokens').click();
      });

      expect(authContext!.refreshToken).toBe(before);
    });

    it('clears the cache when a refresh arrives with no usable identity on either side', async () => {
      // Fail-safe direction: a token with no `sub` on both sides must clear rather than keep another
      // identity's rows. No previous session still skips (that is the mount path, empty cache).
      const noSub = { ...mockDecodedToken, sub: undefined };

      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });

      (jwtDecode.jwtDecode as any).mockReturnValue(noSub);

      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      queryClient.setQueryData(['seatRooms'], [{ id: 'r1', slug: 'a-private-room', name: 'A room' }]);

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'no-sub-access-token',
          refresh_token: 'no-sub-refresh-token'
        })
      });

      const { getByText } = rtlRender(
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <TestComponent />
          </AuthProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      });

      await act(async () => {
        getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(queryClient.getQueryData(['seatRooms'])).toBeUndefined();
      });
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
    it('should refresh token successfully', async () => {
      (Cookies.get as any).mockImplementation((key: string) => {
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return null;
      });

      (jwtDecode.jwtDecode as any).mockReturnValue(mockDecodedToken);

      // This state is a refresh cookie with no access cookie, which is now restored ON MOUNT as well,
      // so the response is persistent rather than one-shot: the mount's refresh consumes one and the
      // explicit refreshToken() below is the call under test.
      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => ({
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token'
        })
      } as unknown as Response);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await act(async () => {
        await authContext!.refreshToken();
      });

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
        await authContext!.refreshToken().catch(() => {
          // Expected to reject; this test asserts the observable session cleanup.
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('none');
      });
      expect(Cookies.remove).toHaveBeenCalledWith('access_token');
      expect(Cookies.remove).toHaveBeenCalledWith('refresh_token');
    });

    it('should disconnect WebSocket on token refresh failure', async () => {
      // Mock WebSocket as connected
      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        disconnect: mockDisconnect
      });

      // A session is present (BOTH cookies) and decodes, so the MOUNT does not refresh by itself. With
      // the refresh-cookie-only scaffold this test previously carried, the mount consumed the queued
      // 401 and called disconnect on its own, while the explicit call below reached an unmocked fetch,
      // threw a TypeError, and was swallowed - so the assertion passed without the claim being tested.
      vi.mocked(Cookies.get).mockImplementation((key?: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return undefined;
      });

      vi.mocked(jwtDecode.jwtDecode).mockReturnValue(mockDecodedToken);

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid refresh token' })
      } as unknown as Response);

      const { getByText } = render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Asserting the REJECTION, not just the cleanup: the 401 path throws this message, while the
      // unmocked-fetch failure threw a TypeError - so this line is what makes the case exercise the
      // explicit call rather than the mount's.
      await expect(
        act(async () => {
          await authContext!.refreshToken();
        })
      ).rejects.toThrow('Token refresh failed');

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it('should automatically refresh token before expiry', async () => {
      vi.useFakeTimers();
      try {
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

        // Fast-forward to 1 minute before expiry (refreshTime = expiresIn - 60000)
        await act(async () => {
          vi.advanceTimersByTime(60 * 1000);
        });

        expect(global.fetch).toHaveBeenCalledWith(
          'http://test-api.com/api/auth/refresh',
          expect.any(Object)
        );
      } finally {
        vi.useRealTimers();
      }
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
      // Mock production environment (vi.stubEnv updates import.meta.env for all modules)
      vi.stubEnv('MODE', 'production');

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

      const loggerErrorSpy = vi.spyOn(logger, 'error').mockImplementation();

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('none');
        expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      });

      expect(loggerErrorSpy).toHaveBeenCalledWith('Error decoding token:', expect.any(Error));

      loggerErrorSpy.mockRestore();
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

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await act(async () => {
        await authContext!.login('test@example.com', 'password');
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      // The user should have username derived from email
      expect(authContext!.user?.username).toBe('test');
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

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await act(async () => {
        await authContext!.login('test@example.com', 'password');
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      // The user should have default roles
      expect(authContext!.user?.roles).toEqual(['user']);
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
        // Use the raw RTL render so the test-utils AuthProvider wrapper is not applied.
        rtlRender(<TestComponent />);
      }).toThrow('useAuth must be used within an AuthProvider');

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Error Handling', () => {
    it('should console error on login failure', async () => {
      const loggerErrorSpy = vi.spyOn(logger, 'error').mockImplementation();

      (Cookies.get as any).mockReturnValue(null);
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(
        act(async () => {
          await authContext!.login('test@example.com', 'password');
        })
      ).rejects.toThrow('Network error');

      expect(loggerErrorSpy).toHaveBeenCalledWith('Login error:', expect.any(Error));

      loggerErrorSpy.mockRestore();
    });

    it('should console error on signup failure', async () => {
      const loggerErrorSpy = vi.spyOn(logger, 'error').mockImplementation();

      (Cookies.get as any).mockReturnValue(null);
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(
        act(async () => {
          await authContext!.signup('new@example.com', 'newuser', 'password');
        })
      ).rejects.toThrow('Network error');

      expect(loggerErrorSpy).toHaveBeenCalledWith('Signup error:', expect.any(Error));

      loggerErrorSpy.mockRestore();
    });

    it('should console error on token refresh failure', async () => {
      const loggerErrorSpy = vi.spyOn(logger, 'error').mockImplementation();

      // A session is present (BOTH cookies), so the MOUNT does not refresh by itself - the
      // refresh-cookie-only mount has its own case above, and this one is about what an explicit
      // refresh failure does.
      vi.mocked(Cookies.get).mockImplementation((key?: string) => {
        if (key === 'access_token') return mockTokens.access_token;
        if (key === 'refresh_token') return mockTokens.refresh_token;
        return undefined;
      });
      vi.mocked(jwtDecode.jwtDecode).mockReturnValue(mockDecodedToken);

      vi.mocked(global.fetch).mockRejectedValueOnce(new Error('Network error'));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await expect(
        act(async () => {
          await authContext!.refreshToken();
        })
      ).rejects.toThrow('Network error');

      expect(loggerErrorSpy).toHaveBeenCalledWith('Token refresh error:', expect.any(Error));

      loggerErrorSpy.mockRestore();
    });
  });
});
