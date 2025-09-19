import React, { createContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { jwtDecode } from 'jwt-decode';
import Cookies from 'js-cookie';
import logger from '../utils/logger';
import { websocketService } from '../services/websocketService';

// Types for authentication
export interface User {
  id: string;
  email: string;
  username: string;
  roles: string[];
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface SignupResult {
  success: boolean;
  requires_email_verification?: boolean;
  message?: string;
  access_token?: string;
  refresh_token?: string;
}

export interface JWTPayload {
  sub: string;
  email: string;
  username?: string;
  roles?: string[];
  exp: number;
  iat: number;
  type: string;
}

export interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, username: string, password: string) => Promise<SignupResult>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  setTokens: (tokens: AuthTokens) => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

import { API_BASE_URL } from '../config/environment';

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokensState] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Decode JWT token to extract user information
  const decodeToken = (token: string): User | null => {
    try {
      const decoded = jwtDecode<JWTPayload>(token);
      
      // Check if token is expired
      if (decoded.exp * 1000 < Date.now()) {
        return null;
      }

      return {
        id: decoded.sub,
        email: decoded.email,
        username: decoded.username || decoded.email.split('@')[0],
        roles: decoded.roles || ['user']
      };
    } catch (error) {
      logger.error('Error decoding token:', error);
      return null;
    }
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

    // Decode and set user
    const userData = decodeToken(tokens.access_token);
    setUser(userData);
  }, []);

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
        setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token
        });
        // Decode and set user from token
        const userData = decodeToken(data.access_token);
        if (userData) {
          setUser(userData);

          // Connect WebSocket with the new access token for real-time updates
          try {
            if (!websocketService.isConnected()) {
              await websocketService.connect(data.access_token);
              logger.info('WebSocket connected after successful login');
            }
          } catch (error) {
            logger.error('Failed to connect WebSocket after login:', error);
          }
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
        setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token
        });
        // Decode and set user from token
        const userData = decodeToken(data.access_token);
        if (userData) {
          setUser(userData);
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
      if (websocketService.isConnected()) {
        websocketService.disconnect();
        logger.info('WebSocket connection closed during logout');
      }
    } catch (error) {
      logger.error('Error closing WebSocket during logout:', error);
    }

    // Clear authentication state
    setUser(null);
    setTokensState(null);
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');

    logger.info('Logout complete - user session cleared');
  }, []);

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
            if (websocketService.isConnected()) {
              websocketService.disconnect();
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
      
      setTokens(newTokens);
      
      // Update user info from new access token
      const userData = decodeToken(data.access_token);
      if (userData) {
        setUser(userData);

        // Reconnect WebSocket with new token for continued real-time updates
        try {
          if (websocketService.isConnected()) {
            await websocketService.reconnectWithNewToken(data.access_token);
            logger.info('WebSocket reconnected with refreshed token');
          }
        } catch (error) {
          logger.error('Failed to reconnect WebSocket with new token:', error);
        }
      }
      
    } catch (error) {
      logger.error('Token refresh error:', error);

      // Disconnect WebSocket on any refresh failure
      try {
        if (websocketService.isConnected()) {
          websocketService.disconnect();
          logger.info('WebSocket disconnected due to token refresh error');
        }
      } catch (wsError) {
        logger.error('Error disconnecting WebSocket during token refresh error:', wsError);
      }

      logout();
      throw error;
    }
  }, [setTokens]);

  // Check for existing tokens on mount
  useEffect(() => {
    const access_token = Cookies.get('access_token');
    const refresh_token = Cookies.get('refresh_token');

    if (access_token && refresh_token) {
      const userData = decodeToken(access_token);
      
      if (userData) {
        setUser(userData);
        setTokensState({ access_token, refresh_token });
      } else if (refresh_token) {
        // Token expired, try to refresh
        refreshToken().catch(() => {
          logout();
        });
      }
    }
    
    setIsLoading(false);
  }, [refreshToken]);

  // Set up token refresh interval
  useEffect(() => {
    if (!tokens?.access_token) return;

    const decoded = jwtDecode<JWTPayload>(tokens.access_token);
    const expiresIn = decoded.exp * 1000 - Date.now();
    
    // Refresh token 1 minute before expiry
    const refreshTime = Math.max(0, expiresIn - 60000);
    
    const timer = setTimeout(() => {
      refreshToken().catch(() => {
        logout();
      });
    }, refreshTime);

    return () => clearTimeout(timer);
  }, [tokens, refreshToken]);

  // Listen for logout events from API layer
  useEffect(() => {
    const handleLogoutEvent = () => {
      logout();
    };

    window.addEventListener('auth-logout', handleLogoutEvent);
    return () => window.removeEventListener('auth-logout', handleLogoutEvent);
  }, []);

  const value: AuthContextType = {
    user,
    tokens,
    isAuthenticated: !!user,
    isLoading,
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