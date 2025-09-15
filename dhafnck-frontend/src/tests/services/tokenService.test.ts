import { tokenService } from '../../services/tokenService';
import { authenticatedFetch } from '../../hooks/useAuthenticatedFetch';
import { API_BASE_URL } from '../../config/environment';
import { vi } from 'vitest';

// Mock the authenticated fetch function
vi.mock('../../hooks/useAuthenticatedFetch', () => ({
  authenticatedFetch: vi.fn(),
}));

const mockAuthenticatedFetch = vi.mocked(authenticatedFetch);

describe('tokenService', () => {
  const baseUrl = `${API_BASE_URL}/api/v2/tokens`;

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock console.log to avoid noise in tests
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('listTokens', () => {
    it('fetches all tokens successfully', async () => {
      const mockTokensResponse = {
        data: [
          { id: '1', name: 'Token 1', scopes: ['read:tasks'] },
          { id: '2', name: 'Token 2', scopes: ['write:tasks'] },
        ],
        total: 2
      };
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(mockTokensResponse),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.listTokens();

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v2/tokens`, {
        method: 'GET',
      });
      expect(result).toEqual(mockTokensResponse);
    });

    it('handles empty token list', async () => {
      const emptyResponse = { data: [], total: 0 };
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(emptyResponse),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.listTokens();

      expect(result).toEqual(emptyResponse);
    });

    it('handles fetch error', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: vi.fn().mockResolvedValue({ message: 'Server error' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.listTokens()).rejects.toThrow('Server error');
    });
  });

  describe('getTokenDetails', () => {
    it('fetches a specific token by id', async () => {
      const mockToken = { 
        id: '123', 
        name: 'Test Token',
        scopes: ['read:tasks'],
        is_active: true 
      };
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(mockToken),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.getTokenDetails('123');

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v2/tokens/123`, {
        method: 'GET',
      });
      expect(result).toEqual(mockToken);
    });

    it('handles not found error', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
        json: vi.fn().mockResolvedValue({ message: 'Token not found' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.getTokenDetails('999')).rejects.toThrow('Token not found');
    });
  });

  describe('generateToken', () => {
    it('generates a new token with all fields', async () => {
      const newTokenData = {
        name: 'New Token',
        scopes: ['read:tasks', 'write:tasks'],
        expires_in_days: 30,
        rate_limit: 100,
      };
      
      const createdToken = {
        id: '456',
        name: 'New Token',
        token: 'generated-token-value',
        scopes: ['read:tasks', 'write:tasks'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-31T00:00:00Z',
        usage_count: 0,
        rate_limit: 100,
      };
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(createdToken),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.generateToken(newTokenData);

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v2/tokens/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newTokenData),
      });
      expect(result).toEqual({ data: createdToken });
    });

    it('handles validation error', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        json: vi.fn().mockResolvedValue({ message: 'Validation failed' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.generateToken({ 
        name: '', 
        scopes: [], 
        expires_in_days: 30 
      })).rejects.toThrow('Validation failed');
    });
  });

  describe('updateTokenScopes', () => {
    it('updates token scopes', async () => {
      const newScopes = ['read:tasks', 'write:tasks', 'execute:mcp'];
      
      const updatedToken = {
        id: '123',
        name: 'Test Token',
        scopes: newScopes,
        is_active: true,
      };
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(updatedToken),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.updateTokenScopes('123', newScopes);

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v2/tokens/123/scopes`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ scopes: newScopes }),
      });
      expect(result).toEqual(updatedToken);
    });

    it('handles update error', async () => {
      const mockResponse = {
        ok: false,
        status: 403,
        json: vi.fn().mockResolvedValue({ message: 'Forbidden' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.updateTokenScopes('123', ['admin'])).rejects.toThrow('Forbidden');
    });
  });

  describe('revokeToken', () => {
    it('revokes a token successfully', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({ success: true }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await tokenService.revokeToken('123');

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v2/tokens/123`, {
        method: 'DELETE',
      });
    });

    it('handles revocation error', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: vi.fn().mockResolvedValue({ message: 'Revocation failed' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.revokeToken('123')).rejects.toThrow('Revocation failed');
    });
  });

  describe('rotateToken', () => {
    it('rotates a token and returns new value', async () => {
      const rotatedToken = {
        id: '123',
        name: 'Test Token',
        token: 'new-rotated-token',
        scopes: ['read:tasks'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-31T00:00:00Z',
        usage_count: 0,
      };
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(rotatedToken),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.rotateToken('123');

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v2/tokens/123/rotate`, {
        method: 'POST',
      });
      expect(result).toEqual({ data: rotatedToken });
      expect(result.data.token).toBe('new-rotated-token');
    });

    it('handles rotation error', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        json: vi.fn().mockResolvedValue({ message: 'Rotation failed' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.rotateToken('123')).rejects.toThrow('Rotation failed');
    });
  });

  describe('validateToken', () => {
    it('validates a token successfully', async () => {
      const validationResult = {
        valid: true,
        scopes: ['read:tasks', 'write:tasks'],
        user_id: 'user-123',
      };
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(validationResult),
      } as unknown as Response;
      
      // Mock fetch directly for validateToken as it doesn't use authenticatedFetch
      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await tokenService.validateToken('test-token-value');

      expect(global.fetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v2/tokens/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'token=test-token-value',
      });
      expect(result).toEqual(validationResult);
    });

    it('handles invalid token', async () => {
      const mockResponse = {
        ok: false,
        status: 401,
        json: vi.fn().mockResolvedValue({ error: 'Invalid token' }),
      } as unknown as Response;
      
      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await tokenService.validateToken('invalid-token');

      expect(result.valid).toBe(false);
    });
  });

  describe('getTokenUsageStats', () => {
    it('fetches token usage statistics', async () => {
      const stats = {
        total_requests: 1000,
        requests_today: 50,
        rate_limit_hits: 5,
        last_used: '2024-01-01T12:00:00Z',
        daily_breakdown: [
          { date: '2024-01-01', count: 50 },
          { date: '2023-12-31', count: 45 }
        ]
      };
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(stats),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.getTokenUsageStats('123');

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(`${API_BASE_URL}/api/v2/tokens/123/usage`, {
        method: 'GET',
      });
      expect(result).toEqual(stats);
    });

    it('handles stats not available', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
        json: vi.fn().mockResolvedValue({ message: 'Stats not found' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.getTokenUsageStats('123')).rejects.toThrow('Stats not found');
    });
  });

  describe('error handling', () => {
    it('handles json parsing error gracefully', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.listTokens()).rejects.toThrow('Failed to fetch tokens');
    });

    it('handles 401 unauthorized', async () => {
      const mockResponse = {
        ok: false,
        status: 401,
        json: vi.fn().mockResolvedValue({ error: 'Unauthorized' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.listTokens()).rejects.toThrow('Unauthorized');
    });

    it('handles 403 forbidden', async () => {
      const mockResponse = {
        ok: false,
        status: 403,
        json: vi.fn().mockResolvedValue({ message: 'Forbidden' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.generateToken({ 
        name: 'Test', 
        scopes: ['admin'],
        expires_in_days: 30 
      })).rejects.toThrow('Forbidden');
    });

    it('handles 500 server error', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: vi.fn().mockResolvedValue({ message: 'Internal Server Error' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.listTokens()).rejects.toThrow('Internal Server Error');
    });
  });

  describe('edge cases', () => {
    it('handles empty token name', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        json: vi.fn().mockResolvedValue({ message: 'Name is required' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.generateToken({ 
        name: '', 
        scopes: ['read:tasks'],
        expires_in_days: 30 
      })).rejects.toThrow('Name is required');
    });

    it('handles very long token names', async () => {
      const longName = 'a'.repeat(256);
      const tokenData = { 
        name: longName,
        scopes: ['read:tasks'],
        expires_in_days: 30,
        rate_limit: 100
      };
      const createdToken = { 
        id: '123', 
        name: longName,
        token: 'test-token',
        scopes: ['read:tasks'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-31T00:00:00Z',
        usage_count: 0,
        rate_limit: 100
      };
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(createdToken),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.generateToken(tokenData);

      expect(result.data.name).toBe(longName);
    });

    it('handles special characters in token names', async () => {
      const specialName = 'Test!@#$%^&*()';
      const tokenData = { 
        name: specialName,
        scopes: ['read:tasks'],
        expires_in_days: 30
      };
      const createdToken = { 
        id: '123', 
        name: specialName,
        token: 'test-token',
        scopes: ['read:tasks'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-31T00:00:00Z',
        usage_count: 0
      };
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(createdToken),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.generateToken(tokenData);

      expect(result.data.name).toBe(specialName);
    });

    it('handles negative rate limits', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        json: vi.fn().mockResolvedValue({ message: 'Rate limit must be positive' }),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      await expect(tokenService.generateToken({ 
        name: 'Test', 
        scopes: ['read:tasks'],
        expires_in_days: 30,
        rate_limit: -1 
      })).rejects.toThrow('Rate limit must be positive');
    });

    it('handles very large rate limits', async () => {
      const largeRateLimit = 1000000;
      const tokenData = { 
        name: 'Test', 
        scopes: ['read:tasks'],
        expires_in_days: 30,
        rate_limit: largeRateLimit 
      };
      const createdToken = { 
        id: '123',
        name: 'Test',
        token: 'test-token',
        scopes: ['read:tasks'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-31T00:00:00Z',
        usage_count: 0,
        rate_limit: largeRateLimit
      };
      
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue(createdToken),
      } as unknown as Response;
      
      mockAuthenticatedFetch.mockResolvedValue(mockResponse);

      const result = await tokenService.generateToken(tokenData);

      expect(result.data.rate_limit).toBe(largeRateLimit);
    });
  });
});