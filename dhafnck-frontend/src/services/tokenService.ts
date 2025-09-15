import { authenticatedFetch } from '../hooks/useAuthenticatedFetch';
import { API_BASE_URL, DEBUG_MODE } from '../config/environment';

// Log API URL only in debug mode
if (DEBUG_MODE) {
  console.log('TokenService - API_BASE_URL:', API_BASE_URL);
}

interface GenerateTokenRequest {
  name: string;
  scopes: string[];
  expires_in_days: number;
  rate_limit?: number;
}

interface TokenResponse {
  id: string;
  name: string;
  token?: string;
  scopes: string[];
  created_at: string;
  expires_at: string;
  last_used_at?: string;
  usage_count: number;
  rate_limit?: number;
  is_active: boolean;
}

interface TokenListResponse {
  data: TokenResponse[];
  total: number;
}

class TokenService {
  // Updated 2025-09-15: Using /api/v2/tokens endpoint (not /api/auth/tokens)
  private baseUrl = `${API_BASE_URL}/api/v2/tokens`;

  constructor() {
    console.log('TokenService initialized with baseUrl:', this.baseUrl);
  }

  async generateToken(request: GenerateTokenRequest): Promise<{ data: TokenResponse }> {
    console.log('TokenService.generateToken - calling:', `${this.baseUrl}/generate`);
    const response = await authenticatedFetch(`${this.baseUrl}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to generate token' }));
      throw new Error(error.message || 'Failed to generate token');
    }

    const tokenResponse = await response.json();
    // Backend returns TokenResponse directly, wrap it for frontend use
    return { data: tokenResponse };
  }

  async listTokens(): Promise<TokenListResponse> {
    console.log('Fetching tokens from:', this.baseUrl);
    const response = await authenticatedFetch(this.baseUrl, {
      method: 'GET',
    });

    console.log('Response status:', response.status);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to fetch tokens' }));
      console.error('Token fetch error:', error);
      throw new Error(error.message || error.error || 'Failed to fetch tokens');
    }

    const data = await response.json();
    console.log('Token list response:', data);
    return data;
  }

  async revokeToken(tokenId: string): Promise<void> {
    const response = await authenticatedFetch(`${this.baseUrl}/${tokenId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to revoke token' }));
      throw new Error(error.message || 'Failed to revoke token');
    }
  }

  async getTokenDetails(tokenId: string): Promise<TokenResponse> {
    const response = await authenticatedFetch(`${this.baseUrl}/${tokenId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to fetch token details' }));
      throw new Error(error.message || 'Failed to fetch token details');
    }

    return response.json();
  }

  async updateTokenScopes(tokenId: string, scopes: string[]): Promise<TokenResponse> {
    const response = await authenticatedFetch(`${this.baseUrl}/${tokenId}/scopes`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ scopes }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to update token scopes' }));
      throw new Error(error.message || 'Failed to update token scopes');
    }

    return response.json();
  }

  async rotateToken(tokenId: string): Promise<{ data: TokenResponse }> {
    const response = await authenticatedFetch(`${this.baseUrl}/${tokenId}/rotate`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to rotate token' }));
      throw new Error(error.message || 'Failed to rotate token');
    }

    const tokenResponse = await response.json();
    // Backend returns TokenResponse directly, wrap it for frontend use
    return { data: tokenResponse };
  }

  async getTokenUsageStats(tokenId: string): Promise<any> {
    const response = await authenticatedFetch(`${this.baseUrl}/${tokenId}/usage`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to fetch usage stats' }));
      throw new Error(error.message || 'Failed to fetch usage stats');
    }

    return response.json();
  }

  // Validate a token (useful for testing)
  async validateToken(token: string): Promise<{ valid: boolean; scopes?: string[]; user_id?: string }> {
    const response = await fetch(`${API_BASE_URL}/api/v2/tokens/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `token=${encodeURIComponent(token)}`,
    });

    if (!response.ok) {
      return { valid: false };
    }

    return response.json();
  }
}

export const tokenService = new TokenService();