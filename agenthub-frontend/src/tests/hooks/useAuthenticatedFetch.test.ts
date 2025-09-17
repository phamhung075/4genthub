import { renderHook, act } from '@testing-library/react';
import { useAuthenticatedFetch, authenticatedFetch } from '../../hooks/useAuthenticatedFetch';
import { useAuth } from '../../hooks/useAuth';
import { jest } from '@jest/globals';
import Cookies from 'js-cookie';

// Mock the auth hook
jest.mock('../../hooks/useAuth');

// Mock js-cookie
jest.mock('js-cookie');

const mockUseAuth = jest.mocked(useAuth);
const mockCookies = jest.mocked(Cookies);

// Mock global fetch
global.fetch = jest.fn() as jest.MockedFunction<typeof fetch>;
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('useAuthenticatedFetch', () => {
  const mockTokens = {
    access_token: 'test-access-token',
    refresh_token: 'test-refresh-token',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({
      tokens: mockTokens,
      refreshToken: jest.fn(),
      logout: jest.fn(),
    });
    mockCookies.get.mockReturnValue('test-access-token');
  });

  it('returns a function when rendered in a hook', () => {
    const { result } = renderHook(() => useAuthenticatedFetch());
    expect(typeof result.current).toBe('function');
  });

  it('makes authenticated request with bearer token and returns Response object', async () => {
    const mockResponse = {
      ok: true,
      status: 200,
      json: async () => ({ data: 'test' }),
    } as Response;
    mockFetch.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useAuthenticatedFetch());
    
    await act(async () => {
      const response = await result.current('/api/test', {
        method: 'GET',
      });
      expect(response).toBe(mockResponse);
    });

    expect(mockFetch).toHaveBeenCalledWith('/api/test', {
      method: 'GET',
      headers: {
        Authorization: 'Bearer test-access-token',
      },
    });
  });

  it('preserves existing headers when adding authorization', async () => {
    const mockResponse = {
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    } as Response;
    mockFetch.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useAuthenticatedFetch());
    
    let response: Response;
    await act(async () => {
      response = await result.current('/api/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Custom-Header': 'custom-value',
        },
        body: JSON.stringify({ test: 'data' }),
      });
    });

    expect(response!).toBe(mockResponse);
    expect(mockFetch).toHaveBeenCalledWith('/api/test', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Custom-Header': 'custom-value',
        Authorization: 'Bearer test-access-token',
      },
      body: JSON.stringify({ test: 'data' }),
    });
  });

  it('makes request without auth header when tokens are not available', async () => {
    mockUseAuth.mockReturnValue({
      tokens: null,
      refreshToken: jest.fn(),
      logout: jest.fn(),
    });

    const mockResponse = {
      ok: true,
      status: 200,
      json: async () => ({ public: true }),
    } as Response;
    mockFetch.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useAuthenticatedFetch());
    
    let response: Response;
    await act(async () => {
      response = await result.current('/api/public');
    });

    expect(response!).toBe(mockResponse);
    expect(mockFetch).toHaveBeenCalledWith('/api/public', {});
  });

  it('handles non-JSON responses', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockRejectedValue(new Error('Invalid JSON')),
      text: async () => 'Plain text response',
    } as unknown as Response);

    const { result } = renderHook(() => useAuthenticatedFetch());
    
    await act(async () => {
      const response = await result.current('/api/text');
      expect(response).toBe(mockResponse);
    });
  });

  it('handles network errors', async () => {
    const networkError = new Error('Network error');
    mockFetch.mockRejectedValueOnce(networkError);

    const { result } = renderHook(() => useAuthenticatedFetch());
    
    await expect(act(async () => {
      await result.current('/api/error');
    })).rejects.toThrow('Network error');
  });

  it('can be used in non-React context with access token from cookies', async () => {
    const mockResponse = { data: 'standalone' };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    // Mock cookie access
    mockCookies.get.mockReturnValue('cookie-token');

    const response = await authenticatedFetch('/api/standalone', {
      method: 'GET',
    });

    expect(mockFetch).toHaveBeenCalledWith('/api/standalone', {
      method: 'GET',
      headers: {
        'Authorization': 'Bearer cookie-token',
      },
    });
    expect(mockCookies.get).toHaveBeenCalledWith('access_token');
  });

  it('handles 401 unauthorized responses', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ error: 'Unauthorized' }),
    } as Response);

    const { result } = renderHook(() => useAuthenticatedFetch());
    
    await act(async () => {
      const response = await result.current('/api/protected');
      expect(response).toBe(mockResponse);
      expect(mockResponse.status).toBe(401);
    });
  });

  it('handles 401 responses by refreshing token and retrying', async () => {
    const refreshToken = jest.fn().mockResolvedValue(undefined);
    
    mockUseAuth.mockReturnValue({
      tokens: mockTokens,
      refreshToken,
      logout: jest.fn(),
    });

    const mockSuccessResponse = {
      ok: true,
      status: 200,
      json: async () => ({ refreshed: true }),
    } as Response;

    // First request returns 401
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
      } as Response)
      .mockResolvedValueOnce(mockSuccessResponse);

    const { result } = renderHook(() => useAuthenticatedFetch());
    
    let response: Response;
    await act(async () => {
      response = await result.current('/api/test');
    });

    expect(response!).toBe(mockSuccessResponse);
    expect(refreshToken).toHaveBeenCalled();
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('supports all HTTP methods', async () => {
    const methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'];
    
    for (const method of methods) {
      const mockResponse = {
        ok: true,
        status: 200,
        json: async () => ({ method }),
      } as Response;
      mockFetch.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useAuthenticatedFetch());
      
      let response: Response;
      await act(async () => {
        response = await result.current('/api/test', { method });
      });

      expect(response!).toBe(mockResponse);
      expect(mockFetch).toHaveBeenLastCalledWith('/api/test', {
        method,
        headers: {
          Authorization: 'Bearer test-access-token',
        },
      });
    }
  });

  it('supports skipAuth option', async () => {
    const mockResponse = {
      ok: true,
      status: 200,
      json: async () => ({ public: true }),
    } as Response;
    mockFetch.mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useAuthenticatedFetch());
    
    let response: Response;
    await act(async () => {
      response = await result.current('/api/public', { skipAuth: true });
    });

    expect(response!).toBe(mockResponse);
    expect(mockFetch).toHaveBeenCalledWith('/api/public', {});
  });

  it('handles refresh token failure by logging out', async () => {
    const refreshToken = jest.fn().mockRejectedValue(new Error('Refresh failed'));
    const logout = jest.fn();
    
    mockUseAuth.mockReturnValue({
      tokens: mockTokens,
      refreshToken,
      logout,
    });

    // First request returns 401
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
    } as Response);

    const { result } = renderHook(() => useAuthenticatedFetch());
    
    await expect(act(async () => {
      await result.current('/api/test');
    })).rejects.toThrow('Session expired. Please login again.');

    expect(refreshToken).toHaveBeenCalled();
    expect(logout).toHaveBeenCalled();
  });
});

describe('authenticatedFetch (standalone)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('adds authorization header when token is available in cookies', async () => {
    mockCookies.get.mockReturnValue('cookie-access-token');
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    } as Response);

    await authenticatedFetch('/api/test');

    expect(mockFetch).toHaveBeenCalledWith('/api/test', {
      headers: {
        'Authorization': 'Bearer cookie-access-token',
      },
    });
  });

  it('makes request without auth header when no token in cookies', async () => {
    mockCookies.get.mockReturnValue(undefined);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ public: true }),
    } as Response);

    await authenticatedFetch('/api/public');

    expect(mockFetch).toHaveBeenCalledWith('/api/public', {});
  });

  it('preserves existing headers when adding authorization', async () => {
    mockCookies.get.mockReturnValue('cookie-token');
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    } as Response);

    await authenticatedFetch('/api/test', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Custom-Header': 'custom-value',
      },
      body: JSON.stringify({ test: 'data' }),
    });

    expect(mockFetch).toHaveBeenCalledWith('/api/test', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Custom-Header': 'custom-value',
        'Authorization': 'Bearer cookie-token',
      },
      body: JSON.stringify({ test: 'data' }),
    });
  });

  it('returns response including 401 unauthorized responses', async () => {
    mockCookies.get.mockReturnValue('invalid-token');
    const unauthorizedResponse = {
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
    } as Response;
    
    mockFetch.mockResolvedValueOnce(unauthorizedResponse);

    const response = await authenticatedFetch('/api/protected');

    expect(response).toBe(unauthorizedResponse);
    expect(response.status).toBe(401);
  });
});