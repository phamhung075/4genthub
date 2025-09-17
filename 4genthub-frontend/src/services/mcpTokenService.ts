// MCP Token Service - Generate and manage tokens for MCP requests
import Cookies from 'js-cookie';
import { taskApiV2 } from './apiV2';
import { API_BASE_URL } from '../config/environment';

interface MCPToken {
  success: boolean;
  token?: string;
  expires_at?: string;
  message: string;
}

interface TokenStats {
  success: boolean;
  stats: {
    total_tokens: number;
    active_tokens: number;
    expired_tokens: number;
    unique_users: number;
  };
  message: string;
}

class MCPTokenService {
  private cachedToken: string | null = null;
  private tokenExpiry: Date | null = null;

  /**
   * Get current auth headers (Supabase token for frontend API calls)
   */
  private getAuthHeaders(): HeadersInit {
    const token = Cookies.get('access_token');
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
  }

  /**
   * Check if we have a valid cached MCP token
   */
  private hasValidCachedToken(): boolean {
    if (!this.cachedToken || !this.tokenExpiry) {
      return false;
    }
    
    // Check if token expires within the next 5 minutes
    const fiveMinutesFromNow = new Date(Date.now() + 5 * 60 * 1000);
    return this.tokenExpiry > fiveMinutesFromNow;
  }

  /**
   * Generate a new MCP token from the backend
   */
  async generateMCPToken(expiresInHours: number = 24): Promise<MCPToken> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v2/mcp-tokens/generate`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          expires_in_hours: expiresInHours,
          description: 'Token for MCP requests from frontend'
        })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ message: 'Failed to generate token' }));
        throw new Error(error.message || `HTTP ${response.status}`);
      }

      const result: MCPToken = await response.json();
      
      if (result.success && result.token) {
        // Cache the token
        this.cachedToken = result.token;
        this.tokenExpiry = result.expires_at ? new Date(result.expires_at) : null;
        
        console.log('MCP token generated successfully, expires:', result.expires_at);
      }

      return result;
    } catch (error) {
      console.error('Failed to generate MCP token:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Get a valid MCP token (generate if needed)
   */
  async getMCPToken(): Promise<string | null> {
    // Return cached token if valid
    if (this.hasValidCachedToken()) {
      return this.cachedToken;
    }

    // Generate new token
    const result = await this.generateMCPToken();
    
    if (result.success && result.token) {
      return result.token;
    }

    console.error('Failed to obtain MCP token:', result.message);
    return null;
  }

  /**
   * Revoke all MCP tokens for the current user
   */
  async revokeTokens(): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v2/mcp-tokens/revoke`, {
        method: 'DELETE',
        headers: this.getAuthHeaders()
      });

      const result = await response.json();
      
      if (result.success) {
        // Clear cached token
        this.cachedToken = null;
        this.tokenExpiry = null;
        console.log('MCP tokens revoked successfully');
      }

      return result.success;
    } catch (error) {
      console.error('Failed to revoke MCP tokens:', error);
      return false;
    }
  }

  /**
   * Get MCP token statistics
   */
  async getTokenStats(): Promise<TokenStats | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v2/mcp-tokens/stats`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to get token stats:', error);
      return null;
    }
  }

  /**
   * Create headers for MCP requests (with MCP token)
   */
  async getMCPHeaders(): Promise<HeadersInit> {
    const token = await this.getMCPToken();
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream',
      'MCP-Protocol-Version': '2025-06-18'
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
      headers['X-MCP-Token'] = token; // Alternative header for MCP requests
    }

    return headers;
  }

  /**
   * Test MCP token functionality
   */
  async testMCPToken(): Promise<{ success: boolean; message: string }> {
    try {
      const token = await this.getMCPToken();
      
      if (!token) {
        return { success: false, message: 'Failed to generate MCP token' };
      }

      // Test the token by making a simple MCP request
      const headers = await this.getMCPHeaders();
      
      const response = await fetch(`${API_BASE_URL}/mcp`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: 1,
          method: 'tools/list',
          params: {}
        })
      });

      if (response.ok) {
        const result = await response.json();
        return { 
          success: true, 
          message: `MCP token working! Found ${result.result?.tools?.length || 0} tools`
        };
      } else {
        return { 
          success: false, 
          message: `MCP request failed: HTTP ${response.status}` 
        };
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Clear cached token (force regeneration)
   */
  clearCache(): void {
    this.cachedToken = null;
    this.tokenExpiry = null;
    console.log('MCP token cache cleared');
  }

  /**
   * Check if user is authenticated (has Supabase token)
   */
  isAuthenticated(): boolean {
    return !!Cookies.get('access_token');
  }
}

// Export singleton instance
export const mcpTokenService = new MCPTokenService();