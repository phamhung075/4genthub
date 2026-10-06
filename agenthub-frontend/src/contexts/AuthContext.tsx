import React, { createContext, useState, useEffect, ReactNode, useCallback, useContext, useRef } from 'react';
import { jwtDecode } from 'jwt-decode';
import Cookies from 'js-cookie';
import logger from '../utils/logger';
import { useWebSocket } from '../hooks/useWebSocketV2';

// Import types from centralized location
import type { User, AuthTokens, SignupResult, JWTPayload } from '../types/authTypes';
import type { AuthContextType } from '../types/componentTypes';

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

/** What a token can and cannot become. `not-a-session-token` decodes but is not a session access token. */
type TokenIdentity =
  | { ok: true; user: User }
  | { ok: false; reason: 'undecodable' | 'expired' }
  | { ok: false; reason: 'not-a-session-token'; declaredType: string | null };

/**
 * The user-facing reason a stored token cannot start a session, or null when there is nothing to say.
 * The token's own `type` claim is a DECLARATION of what it is - the mint endpoint writes `api_token`,
 * a login writes `access` - so when it is present the refusal names it. When it is absent the refusal
 * is an INFERENCE from the absent identity claim instead, and the wording says that rather than
 * claiming to know what the token is.
 */
const sessionRefusal = (identity: TokenIdentity): string | null => {
  if (identity.ok || identity.reason !== 'not-a-session-token') {
    return null;
  }
  if (identity.declaredType) {
    return `The token stored for this browser is not a session token: it declares type "${identity.declaredType}". Sign in again, or use it against the API instead of as a session token.`;
  }
  return 'The token stored for this browser cannot start a session: it carries no email claim and declares no type. Sign in again, or use it against the API instead of as a session token.';
};

interface AuthProviderProps {
  children: ReactNode;
}

import { API_BASE_URL } from '../config/environment';
import { useQueryClient } from '@tanstack/react-query';
import { useNotificationStore } from '../store/notifications';

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  // `logout` must not change identity when `user` changes: the mount and refresh-token effects list
  // it as a dependency, so a new identity re-runs them (a refresh/logout loop under test).
  const userRef = useRef<User | null>(null);
  userRef.current = user;
  const [tokens, setTokensState] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // A token that could not form a session is reported here rather than by clearing the session
  // silently; null when there is nothing to explain.
  const [authError, setAuthError] = useState<string | null>(null);

  // Only initialize WebSocket when we have valid user and token
  const shouldConnectWebSocket = !!(user?.id && tokens?.access_token);

  // CRITICAL FIX: Only call useWebSocket when credentials are available
  // This prevents "missing credentials" warnings during initial render
  const {
    isConnected: isWebSocketConnected,
    disconnect: disconnectWebSocket,
  } = useWebSocket(
    user?.id || '',
    tokens?.access_token || ''
  );

  // A session is built from the token's claims: `sub` is the identity and `email` names it. The token
  // also declares what it IS in its `type` claim, which is the honest thing to read first: a token
  // minted by POST /api/v2/tokens says `type: api_token` while a login's token says `type: access`.
  // Only when there is no declaration does this fall back to the absent claim.
  const classifyToken = (token: string): TokenIdentity => {
    let decoded: JWTPayload;
    try {
      decoded = jwtDecode<JWTPayload>(token);
    } catch (error) {
      logger.error('Error decoding token:', error);
      return { ok: false, reason: 'undecodable' };
    }

    // Check if token is expired
    if (decoded.exp && decoded.exp * 1000 < Date.now()) {
      return { ok: false, reason: 'expired' };
    }

    if (decoded.type && decoded.type !== 'access') {
      return { ok: false, reason: 'not-a-session-token', declaredType: decoded.type };
    }

    // No declaration says otherwise, so this is an INFERENCE FROM ABSENCE: the app builds a username
    // from the email claim, and a token without one cannot name a user. It is not evidence of what
    // the token is - only the `type` check above reads that.
    if (typeof decoded.email !== 'string' || decoded.email === '') {
      return { ok: false, reason: 'not-a-session-token', declaredType: null };
    }

    return {
      ok: true,
      user: {
        id: decoded.sub,
        email: decoded.email,
        username: decoded.username || decoded.email.split('@')[0],
        roles: decoded.roles || ['user']
      }
    };
  };

  // Set tokens and update user state
  const setTokens = useCallback((tokens: AuthTokens) => {
    setTokensState(tokens);

    // Store tokens in cookies
    Cookies.set('access_token', tokens.access_token, {
      expires: 7, // 7 days - longer storage for better UX
      sameSite: 'strict',
      secure: import.meta.env.MODE === 'production'
    });

    Cookies.set('refresh_token', tokens.refresh_token, {
      expires: 30, // 30 days
      sameSite: 'strict',
      secure: import.meta.env.MODE === 'production'
    });

    // Classify and set user
    const identity = classifyToken(tokens.access_token);
    setUser(identity.ok ? identity.user : null);
    setAuthError(sessionRefusal(identity));
  }, []);

  // An identity boundary: a new identity's tokens are arriving, so anything cached for the previous
  // one must go. Needed on login and signup because /login and /signup are public routes and their
  // forms swap identity with SPA navigation - no logout runs, and the client lives above the router,
  // so neither the cache nor this module remounts to drop the old identity's rows and inbox.
  const discardPreviousIdentity = useCallback(() => {
    queryClient.clear();
    useNotificationStore.getState().reset();
  }, [queryClient]);

  // Login function - Updated to use unified auth API
  const login = async (email: string, password: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        credentials: 'include', // Include cookies for CORS
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        // Check if it's an email verification issue
        if (response.status === 403) {
          throw new Error('Please verify your email before signing in. Check your inbox for the verification link.');
        }
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();

      // Check if email verification is required
      if (data.requires_email_verification) {
        throw new Error('Please verify your email before signing in. Check your inbox for the verification link.');
      }

      if (data.access_token && data.refresh_token) {
        discardPreviousIdentity();
        setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token
        });
        // Decode and set user from token
        const identity = classifyToken(data.access_token);
        setAuthError(sessionRefusal(identity));
        if (identity.ok) {
          setUser(identity.user);

          // Connect WebSocket with the new access token for real-time updates
          // WebSocket connection handled by useWebSocket hook
        }
      } else {
        throw new Error('No tokens received from server');
      }
    } catch (error) {
      logger.error('Login error:', error);
      throw error;
    }
  };

  // Signup function - Updated to use unified auth API
  const signup = async (email: string, username: string, password: string): Promise<SignupResult> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        credentials: 'include', // Include cookies for CORS
        body: JSON.stringify({
          email,
          password,
          username,  // Will be stored in user metadata
          full_name: username  // Optional: can be different from username
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
      }

      const data = await response.json();

      // Check if email verification is required
      if (data.requires_email_verification) {
        // Don't auto-login, user needs to verify email first
        return {
          success: true,
          requires_email_verification: true,
          message: data.message || 'Please check your email to verify your account'
        };
      }

      // If email verification is not required (unlikely with Supabase)
      if (data.success && data.access_token) {
        discardPreviousIdentity();
        setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token
        });
        // Decode and set user from token
        const identity = classifyToken(data.access_token);
        setAuthError(sessionRefusal(identity));
        if (identity.ok) {
          setUser(identity.user);
        }
      }

      return data;
    } catch (error) {
      logger.error('Signup error:', error);
      throw error;
    }
  };

  // Logout function with WebSocket cleanup
  const logout = useCallback(() => {
    logger.info('Logging out user and cleaning up all connections');

    // Disconnect WebSocket BEFORE clearing authentication state
    try {
      if (isWebSocketConnected) {
        disconnectWebSocket();
        logger.info('WebSocket connection closed during logout');
      }
    } catch (error) {
      logger.error('Error closing WebSocket during logout:', error);
    }

    // Clear authentication state
    setUser(null);
    setTokensState(null);
    setAuthError(null);
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');

    // Notifications are addressed to an identity, so they must not survive a user switch in the
    // same tab (the query cache is not cleared, but it holds no other identity's message text).
    useNotificationStore.getState().reset();

    // The query cache is the same hazard at list scale: its keys carry no user id, so the next
    // user in this tab would render the previous user's tasks, seats and projects. Only a live
    // session can have cached another identity's data: the mount path (a cookie that does not
    // decode) has no session and starts with an empty cache on a fresh load, so it must not wipe
    // a cache a caller has already primed.
    if (userRef.current) {
      queryClient.clear();
    }

    logger.info('Logout complete - user session cleared');
  }, [disconnectWebSocket, isWebSocketConnected, queryClient]);

  // Refresh token function
  const refreshToken = useCallback(async () => {
    try {
      const refresh_token = Cookies.get('refresh_token');

      if (!refresh_token) {
        throw new Error('No refresh token available');
      }

      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        credentials: 'include', // Include cookies for CORS
        body: JSON.stringify({ refresh_token }),
      });

      if (!response.ok) {
        // If refresh token is invalid or expired, clear tokens and disconnect WebSocket
        if (response.status === 401) {
          logger.error('Refresh token expired or invalid - logging out');

          // Disconnect WebSocket before clearing tokens
          try {
            if (isWebSocketConnected) {
              disconnectWebSocket();
              logger.info('WebSocket disconnected due to token refresh failure');
            }
          } catch (error) {
            logger.error('Error disconnecting WebSocket during token refresh failure:', error);
          }

          // Clear cookies first
          Cookies.remove('access_token');
          Cookies.remove('refresh_token');
          logout();
        }
        throw new Error('Token refresh failed');
      }

      const data = await response.json();

      // Update tokens - refresh_token might not always be returned
      const newTokens = {
        access_token: data.access_token,
        refresh_token: data.refresh_token || refresh_token  // Use existing if not provided
      };

      const identity = classifyToken(data.access_token);
      setAuthError(sessionRefusal(identity));
      const userData = identity.ok ? identity.user : null;

      // A refresh can come back with a DIFFERENT identity: these are plain same-origin document
      // cookies shared by every tab, so if another tab logged out and signed in as someone else,
      // this tab's refresh picks that identity up. That is an identity replacement like login, so
      // the previous identity's cache and inbox must go - while the ordinary same-identity refresh,
      // which is the common case, must not drop the cache.
      // Unusable identity data (a token with no `sub` on either side) fails toward clearing rather
      // than toward keeping another identity's rows. No previous session still skips the clear.
      const previousId = userRef.current?.id;
      if (userData && userRef.current && (!userData.id || !previousId || userData.id !== previousId)) {
        discardPreviousIdentity();
      }

      setTokens(newTokens);

      // Update user info from new access token
      if (userData) {
        setUser(userData);

        // Reconnect WebSocket with new token for continued real-time updates
      }

    } catch (error) {
      logger.error('Token refresh error:', error);

      // Disconnect WebSocket on any refresh failure
      try {
        if (isWebSocketConnected) {
          disconnectWebSocket();
          logger.info('WebSocket disconnected due to token refresh error');
        }
      } catch (wsError) {
        logger.error('Error disconnecting WebSocket during token refresh error:', wsError);
      }

      logout();
      throw error;
    }
  }, [disconnectWebSocket, isWebSocketConnected, logout, setTokens, discardPreviousIdentity]);

  // Check for existing tokens on mount and establish WebSocket connection
  useEffect(() => {
    const access_token = Cookies.get('access_token');
    const refresh_token = Cookies.get('refresh_token');

    if (access_token && refresh_token) {
      const identity = classifyToken(access_token);

      if (identity.ok) {
        setUser(identity.user);
        setTokensState({ access_token, refresh_token });
        setAuthError(null);
      } else if (identity.reason === 'not-a-session-token') {
        // NON-DESTRUCTIVE by design: a token that cannot form a session is not a dead session.
        // Report why and leave the stored credentials alone - refreshing and then logging out turns
        // "this token is unusable" into a silent logout that clears the cookies and every call 403.
        setAuthError(sessionRefusal(identity));
        logger.warn('Stored token is not a session token; leaving the stored credentials alone');
      } else {
        // Expired or undecodable: the ordinary expiry path, try the refresh token.
        refreshToken().catch(() => {
          logout();
        });
      }
    } else if (refresh_token) {
      // The access cookie is written for 7 days and the refresh cookie for 30 (see setTokens), so a
      // user who never signed out arrives here holding ONLY the refresh cookie: the access cookie has
      // simply expired. That is the case the refresh endpoint exists for, so try it before deciding
      // the session is gone. logout() clears BOTH cookies, so a refresh cookie that survived means
      // the user did not end the session; a state with neither cookie still falls through below and
      // shows the login form, which is what an explicit sign-out must keep landing on.
      refreshToken().catch(() => {
        logout();
      });
    } else {
      // No tokens available - ensure WebSocket is disconnected
      if (isWebSocketConnected) {
        disconnectWebSocket();
        logger.info('WebSocket disconnected - no authentication tokens available');
      }
    }

    setIsLoading(false);
  }, [disconnectWebSocket, isWebSocketConnected, logout, refreshToken]);

  // Set up token refresh interval
  useEffect(() => {
    if (!tokens?.access_token) return;

    const decoded = jwtDecode<JWTPayload>(tokens.access_token);
    const expiresIn = decoded.exp ? decoded.exp * 1000 - Date.now() : 0;

    // Refresh token 1 minute before expiry
    const refreshTime = Math.max(0, expiresIn - 60000);

    const timer = setTimeout(() => {
      refreshToken().catch(() => {
        logout();
      });
    }, refreshTime);

    return () => clearTimeout(timer);
  }, [tokens, refreshToken]);

  // Keep-alive mechanism to prevent Keycloak session timeout
  useEffect(() => {
    if (!tokens?.access_token) return;

    // Ping backend every 2 minutes to keep session alive
    // This prevents clientSessionIdleTimeout from expiring
    const keepAliveInterval = setInterval(async () => {
      try {
        await fetch(`${API_BASE_URL}/api/v2/connections/health`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`,
            'Content-Type': 'application/json',
          },
          credentials: 'include',
        });
      } catch (error) {
        // Don't throw - keep-alive failures shouldn't disrupt user experience
      }
    }, 120000); // 2 minutes (120 seconds)

    logger.info('Session keep-alive mechanism started');
    return () => {
      clearInterval(keepAliveInterval);
      logger.info('Session keep-alive mechanism stopped');
    };
  }, [tokens?.access_token]);

  // Listen for logout events from API layer
  useEffect(() => {
    const handleLogoutEvent = () => {
      logout();
    };

    window.addEventListener('auth-logout', handleLogoutEvent);
    return () => window.removeEventListener('auth-logout', handleLogoutEvent);
  }, [logout]);

  const value: AuthContextType = {
    user,
    tokens,
    isAuthenticated: !!user,
    isLoading,
    authError,
    login,
    signup,
    logout,
    refreshToken,
    setTokens
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook to use the auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
