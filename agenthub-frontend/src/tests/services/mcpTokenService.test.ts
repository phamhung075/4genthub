// MCPTokenService Tests
import Cookies from 'js-cookie';
import { mcpTokenService } from '../../services/mcpTokenService';

// Mock js-cookie with default export for Vitest compatibility
vi.mock('js-cookie', () => {
  const mockCookies = {
    get: vi.fn(),
  };
  return {
    default: mockCookies,
    ...mockCookies
  };
});

// Mock import.meta.env
const mockApiUrl = 'http://localhost:8000';
(import.meta as any).env = { VITE_API_URL: mockApiUrl };

// Global fetch mock
global.fetch = vi.fn();

describe('MCPTokenService', () => {
  const mockAccessToken = 'mock-supabase-token';
  const mockMCPToken = 'mock-mcp-token-12345';
  const mockExpiry = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(); // 24 hours from now
  const mockStats = {
    total_tokens: 10,
    active_tokens: 3,
    expired_tokens: 7,
    unique_users: 5,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset service state
    mcpTokenService.clearCache();
    // Default to authenticated state
    (Cookies.get as any).mockImplementation((key: string) => {
      if (key === 'access_token') return mockAccessToken;
      return null;
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('isAuthenticated', () => {
    it('should return true when access token exists', () => {
      expect(mcpTokenService.isAuthenticated()).toBe(true);
      expect(Cookies.get).toHaveBeenCalledWith('access_token');
    });

    it('should return false when access token does not exist', () => {
      (Cookies.get as any).mockReturnValue(null);
      expect(mcpTokenService.isAuthenticated()).toBe(false);
    });
  });

  describe('generateMCPToken', () => {
    it('should generate token successfully with default expiry', async () => {
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await mcpTokenService.generateMCPToken();

      expect(fetch).toHaveBeenCalledWith(
        `${mockApiUrl}/api/v2/mcp-tokens/generate`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${mockAccessToken}`,
          },
          body: JSON.stringify({
            expires_in_hours: 24,
            description: 'Token for MCP requests from frontend',
          }),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should generate token with custom expiry', async () => {
      const customExpiry = 48;
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: new Date(Date.now() + customExpiry * 60 * 60 * 1000).toISOString(),
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      await mcpTokenService.generateMCPToken(customExpiry);

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({
            expires_in_hours: customExpiry,
            description: 'Token for MCP requests from frontend',
          }),
        })
      );
    });

    it('should handle HTTP error responses', async () => {
      const errorMessage = 'Unauthorized';
      (fetch as any).mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ message: errorMessage }),
      });

      const result = await mcpTokenService.generateMCPToken();

      expect(result).toEqual({
        success: false,
        message: errorMessage,
      });
    });

    it('should handle JSON parse errors on error response', async () => {
      (fetch as any).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      const result = await mcpTokenService.generateMCPToken();

      expect(result).toEqual({
        success: false,
        message: 'Failed to generate token',
      });
    });

    it('should handle network errors', async () => {
      const networkError = new Error('Network error');
      (fetch as any).mockRejectedValue(networkError);

      const result = await mcpTokenService.generateMCPToken();

      expect(result).toEqual({
        success: false,
        message: 'Network error',
      });
    });

    it('should cache token on successful generation', async () => {
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      await mcpTokenService.generateMCPToken();

      // Test that subsequent getMCPToken calls use cache
      const token = await mcpTokenService.getMCPToken();
      expect(token).toBe(mockMCPToken);
      expect(fetch).toHaveBeenCalledTimes(1); // Only initial generation
    });

    it('should work without authentication token', async () => {
      (Cookies.get as any).mockReturnValue(null);
      
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      await mcpTokenService.generateMCPToken();

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json',
            // No Authorization header
          },
        })
      );
    });
  });

  describe('getMCPToken', () => {
    it('should return cached token if valid', async () => {
      // First generate a token
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      await mcpTokenService.generateMCPToken();
      (fetch as any).mockClear();

      // Get token should use cache
      const token = await mcpTokenService.getMCPToken();
      expect(token).toBe(mockMCPToken);
      expect(fetch).not.toHaveBeenCalled();
    });

    it('should generate new token if cache is empty', async () => {
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      const token = await mcpTokenService.getMCPToken();
      
      expect(token).toBe(mockMCPToken);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('should generate new token if cached token expires soon', async () => {
      // Generate token that expires in 3 minutes
      const soonExpiry = new Date(Date.now() + 3 * 60 * 1000).toISOString();
      const mockResponse1 = {
        success: true,
        token: 'soon-to-expire-token',
        expires_at: soonExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse1,
      });

      await mcpTokenService.generateMCPToken();
      
      // New token with longer expiry
      const mockResponse2 = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse2,
      });

      const token = await mcpTokenService.getMCPToken();
      
      expect(token).toBe(mockMCPToken);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('should return null if token generation fails', async () => {
      (fetch as any).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ message: 'Server error' }),
      });

      const token = await mcpTokenService.getMCPToken();
      
      expect(token).toBeNull();
    });

    it('should handle token without expiry', async () => {
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: null,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      await mcpTokenService.generateMCPToken();
      
      // Should not use cache since no expiry
      const token = await mcpTokenService.getMCPToken();
      
      expect(token).toBe(mockMCPToken);
      expect(fetch).toHaveBeenCalledTimes(2); // Initial + regeneration
    });
  });

  describe('revokeTokens', () => {
    it('should revoke tokens successfully', async () => {
      // First generate a token to have something cached
      const mockGenerateResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockGenerateResponse,
      });

      await mcpTokenService.generateMCPToken();

      // Now revoke
      const mockRevokeResponse = {
        success: true,
        message: 'All tokens revoked',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockRevokeResponse,
      });

      const result = await mcpTokenService.revokeTokens();

      expect(fetch).toHaveBeenLastCalledWith(
        `${mockApiUrl}/api/v2/mcp-tokens/revoke`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${mockAccessToken}`,
          },
        }
      );

      expect(result).toBe(true);

      // Verify cache is cleared
      const token = await mcpTokenService.getMCPToken();
      expect(fetch).toHaveBeenCalledTimes(3); // generate + revoke + regenerate
    });

    it('should return false on revoke failure', async () => {
      (fetch as any).mockResolvedValue({
        ok: false,
        json: async () => ({ success: false, message: 'Revoke failed' }),
      });

      const result = await mcpTokenService.revokeTokens();
      
      expect(result).toBe(false);
    });

    it('should handle network errors during revoke', async () => {
      (fetch as any).mockRejectedValue(new Error('Network error'));

      const result = await mcpTokenService.revokeTokens();
      
      expect(result).toBe(false);
    });
  });

  describe('getTokenStats', () => {
    it('should get token statistics successfully', async () => {
      const mockResponse = {
        success: true,
        stats: mockStats,
        message: 'Stats retrieved',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await mcpTokenService.getTokenStats();

      expect(fetch).toHaveBeenCalledWith(
        `${mockApiUrl}/api/v2/mcp-tokens/stats`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${mockAccessToken}`,
          },
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('should return null on HTTP error', async () => {
      (fetch as any).mockResolvedValue({
        ok: false,
        status: 404,
      });

      const result = await mcpTokenService.getTokenStats();
      
      expect(result).toBeNull();
    });

    it('should return null on network error', async () => {
      (fetch as any).mockRejectedValue(new Error('Network error'));

      const result = await mcpTokenService.getTokenStats();
      
      expect(result).toBeNull();
    });
  });

  describe('getMCPHeaders', () => {
    it('should return headers with MCP token', async () => {
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      const headers = await mcpTokenService.getMCPHeaders();

      expect(headers).toEqual({
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'MCP-Protocol-Version': '2025-06-18',
        'Authorization': `Bearer ${mockMCPToken}`,
        'X-MCP-Token': mockMCPToken,
      });
    });

    it('should return headers without token if generation fails', async () => {
      (fetch as any).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ message: 'Server error' }),
      });

      const headers = await mcpTokenService.getMCPHeaders();

      expect(headers).toEqual({
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
        'MCP-Protocol-Version': '2025-06-18',
      });
    });
  });

  describe('testMCPToken', () => {
    it('should test token successfully', async () => {
      // Mock token generation
      const mockTokenResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokenResponse,
      });

      // Mock MCP test request
      const mockMCPResponse = {
        jsonrpc: '2.0',
        id: 1,
        result: {
          tools: new Array(25).fill({ name: 'tool' }), // 25 tools
        },
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMCPResponse,
      });

      const result = await mcpTokenService.testMCPToken();

      expect(fetch).toHaveBeenLastCalledWith(
        `${mockApiUrl}/mcp`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
            'MCP-Protocol-Version': '2025-06-18',
            'Authorization': `Bearer ${mockMCPToken}`,
            'X-MCP-Token': mockMCPToken,
          },
          body: JSON.stringify({
            jsonrpc: '2.0',
            id: 1,
            method: 'tools/list',
            params: {},
          }),
        }
      );

      expect(result).toEqual({
        success: true,
        message: 'MCP token working! Found 25 tools',
      });
    });

    it('should handle failed token generation', async () => {
      (fetch as any).mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ message: 'Unauthorized' }),
      });

      const result = await mcpTokenService.testMCPToken();

      expect(result).toEqual({
        success: false,
        message: 'Failed to generate MCP token',
      });
    });

    it('should handle MCP request failure', async () => {
      // Mock successful token generation
      const mockTokenResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokenResponse,
      });

      // Mock failed MCP request
      (fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 403,
      });

      const result = await mcpTokenService.testMCPToken();

      expect(result).toEqual({
        success: false,
        message: 'MCP request failed: HTTP 403',
      });
    });

    it('should handle network errors during test', async () => {
      // Mock successful token generation
      const mockTokenResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokenResponse,
      });

      // Mock network error
      (fetch as any).mockRejectedValueOnce(new Error('Connection refused'));

      const result = await mcpTokenService.testMCPToken();

      expect(result).toEqual({
        success: false,
        message: 'Connection refused',
      });
    });

    it('should handle missing tools in response', async () => {
      // Mock token generation
      const mockTokenResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokenResponse,
      });

      // Mock MCP response without tools
      const mockMCPResponse = {
        jsonrpc: '2.0',
        id: 1,
        result: {},
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMCPResponse,
      });

      const result = await mcpTokenService.testMCPToken();

      expect(result).toEqual({
        success: true,
        message: 'MCP token working! Found 0 tools',
      });
    });

    it('should handle non-Error exceptions', async () => {
      // Mock token generation
      const mockTokenResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokenResponse,
      });

      // Mock throwing non-Error
      (fetch as any).mockRejectedValueOnce('String error');

      const result = await mcpTokenService.testMCPToken();

      expect(result).toEqual({
        success: false,
        message: 'Unknown error',
      });
    });
  });

  describe('clearCache', () => {
    it('should clear cached token and expiry', async () => {
      // First generate a token
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      await mcpTokenService.generateMCPToken();
      
      // Clear cache
      mcpTokenService.clearCache();

      // Should regenerate token
      const token = await mcpTokenService.getMCPToken();
      
      expect(token).toBe(mockMCPToken);
      expect(fetch).toHaveBeenCalledTimes(2); // Initial + after clear
    });
  });

  describe('console logging', () => {
    let consoleLogSpy: jest.SpyInstance;
    let consoleErrorSpy: jest.SpyInstance;

    beforeEach(() => {
      consoleLogSpy = vi.spyOn(console, 'log').mockImplementation();
      consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation();
    });

    afterEach(() => {
      consoleLogSpy.mockRestore();
      consoleErrorSpy.mockRestore();
    });

    it('should log successful token generation', async () => {
      const mockResponse = {
        success: true,
        token: mockMCPToken,
        expires_at: mockExpiry,
        message: 'Token generated successfully',
      };

      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      });

      await mcpTokenService.generateMCPToken();

      // Logger adds formatted prefix, check that call contains expected message
      expect(consoleLogSpy).toHaveBeenCalled();
      const logCalls = consoleLogSpy.mock.calls;
      expect(logCalls.some((call: any) => call.some((arg: any) =>
        typeof arg === 'string' && arg.includes('MCP token generated successfully')
      ))).toBe(true);
    });

    it('should log token generation errors', async () => {
      const error = new Error('Network error');
      (fetch as any).mockRejectedValue(error);

      await mcpTokenService.generateMCPToken();

      // Logger adds formatted prefix, check that call contains expected message
      expect(consoleErrorSpy).toHaveBeenCalled();
      const errorCalls = consoleErrorSpy.mock.calls;
      expect(errorCalls.some((call: any) => call.some((arg: any) =>
        typeof arg === 'string' && arg.includes('Failed to generate MCP token')
      ))).toBe(true);
    });

    it('should log getMCPToken failures', async () => {
      (fetch as any).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ message: 'Server error' }),
      });

      await mcpTokenService.getMCPToken();

      // Logger adds formatted prefix, check that call contains expected message
      expect(consoleErrorSpy).toHaveBeenCalled();
      const errorCalls = consoleErrorSpy.mock.calls;
      expect(errorCalls.some((call: any) => call.some((arg: any) =>
        typeof arg === 'string' && arg.includes('Failed to obtain MCP token')
      ))).toBe(true);
    });

    it('should log successful token revocation', async () => {
      (fetch as any).mockResolvedValue({
        ok: true,
        json: async () => ({ success: true }),
      });

      await mcpTokenService.revokeTokens();

      // Logger adds formatted prefix, check that call contains expected message
      expect(consoleLogSpy).toHaveBeenCalled();
      const logCalls = consoleLogSpy.mock.calls;
      expect(logCalls.some((call: any) => call.some((arg: any) =>
        typeof arg === 'string' && arg.includes('MCP tokens revoked successfully')
      ))).toBe(true);
    });

    it('should log token revocation errors', async () => {
      const error = new Error('Network error');
      (fetch as any).mockRejectedValue(error);

      await mcpTokenService.revokeTokens();

      // Logger adds formatted prefix, check that call contains expected message
      expect(consoleErrorSpy).toHaveBeenCalled();
      const errorCalls = consoleErrorSpy.mock.calls;
      expect(errorCalls.some((call: any) => call.some((arg: any) =>
        typeof arg === 'string' && arg.includes('Failed to revoke MCP tokens')
      ))).toBe(true);
    });

    it('should log stats retrieval errors', async () => {
      const error = new Error('Stats error');
      (fetch as any).mockRejectedValue(error);

      await mcpTokenService.getTokenStats();

      // Logger adds formatted prefix, check that call contains expected message
      expect(consoleErrorSpy).toHaveBeenCalled();
      const errorCalls = consoleErrorSpy.mock.calls;
      expect(errorCalls.some((call: any) => call.some((arg: any) =>
        typeof arg === 'string' && arg.includes('Failed to get token stats')
      ))).toBe(true);
    });

    it('should log cache clearing', () => {
      mcpTokenService.clearCache();

      // Logger adds formatted prefix, check that call contains expected message
      expect(consoleLogSpy).toHaveBeenCalled();
      const logCalls = consoleLogSpy.mock.calls;
      expect(logCalls.some((call: any) => call.some((arg: any) =>
        typeof arg === 'string' && arg.includes('MCP token cache cleared')
      ))).toBe(true);
    });
  });
});