// Keycloak Authentication Service
// Direct authentication with Keycloak server using resource owner password credentials flow

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'https://your-keycloak-server.com';
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'your-realm';
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'your-client-id';
const KEYCLOAK_CLIENT_SECRET = import.meta.env.VITE_KEYCLOAK_CLIENT_SECRET || 'your-client-secret';

export interface KeycloakTokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  refresh_expires_in: number;
  token_type: string;
}

export class KeycloakAuthService {
  private tokenEndpoint: string;

  constructor() {
    this.tokenEndpoint = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`;
  }

  async login(username: string, password: string): Promise<KeycloakTokenResponse> {
    console.log('Attempting Keycloak login for:', username);
    console.log('Token endpoint:', this.tokenEndpoint);
    
    const formData = new URLSearchParams();
    formData.append('grant_type', 'password');
    formData.append('client_id', KEYCLOAK_CLIENT_ID);
    formData.append('client_secret', KEYCLOAK_CLIENT_SECRET);
    formData.append('username', username);
    formData.append('password', password);
    
    // Request all CRUD scopes and additional permissions
    formData.append('scope', 'openid profile email offline_access mcp-api mcp-roles mcp-profile mcp-crud-create mcp-crud-read mcp-crud-update mcp-crud-delete');

    console.log('Request body:', formData.toString());

    try {
      const response = await fetch(this.tokenEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });

      console.log('Response status:', response.status);

      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Login failed' }));
        console.error('Keycloak error response:', error);
        throw new Error(error.error_description || error.error || 'Login failed');
      }

      const result = await response.json();
      console.log('Login successful, received tokens');
      return result;
    } catch (err) {
      console.error('Keycloak login error:', err);
      throw err;
    }
  }

  async refreshToken(refreshToken: string): Promise<KeycloakTokenResponse> {
    const formData = new URLSearchParams();
    formData.append('grant_type', 'refresh_token');
    formData.append('client_id', KEYCLOAK_CLIENT_ID);
    formData.append('client_secret', KEYCLOAK_CLIENT_SECRET);
    formData.append('refresh_token', refreshToken);

    const response = await fetch(this.tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Token refresh failed' }));
      throw new Error(error.error_description || error.error || 'Token refresh failed');
    }

    return response.json();
  }

  async logout(refreshToken: string): Promise<void> {
    const logoutEndpoint = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/logout`;
    
    const formData = new URLSearchParams();
    formData.append('client_id', KEYCLOAK_CLIENT_ID);
    formData.append('client_secret', KEYCLOAK_CLIENT_SECRET);
    formData.append('refresh_token', refreshToken);

    await fetch(logoutEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
  }
}

export const keycloakAuth = new KeycloakAuthService();