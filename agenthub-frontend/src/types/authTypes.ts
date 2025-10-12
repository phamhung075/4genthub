/**
 * Authentication Types
 * Consolidated types for authentication, users, tokens, and permissions
 */

// =============================================================================
// User and Authentication Types
// =============================================================================

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
  exp?: number;
  username?: string;
  roles?: string[];
  iat?: number;
  iss?: string;
  aud?: string | string[];
  // Add other JWT payload fields as needed
}

// =============================================================================
// Token Permissions Types
// =============================================================================

export interface TokenPermissions {
  create: boolean;
  read: boolean;
  update: boolean;
  delete: boolean;
}

export interface ResourceAccess {
  [resource: string]: string[];
}

export interface DecodedToken {
  exp?: number;
  iat?: number;
  auth_time?: number;
  jti?: string;
  iss?: string;
  aud?: string | string[];
  sub?: string;
  typ?: string;
  azp?: string;
  session_state?: string;
  acr?: string;

  // User information
  email?: string;
  email_verified?: boolean;
  name?: string;
  preferred_username?: string;
  given_name?: string;
  family_name?: string;

  // Roles and permissions
  realm_roles?: string[];
  realm_access?: {
    roles: string[];
  };
  resource_access?: {
    [client: string]: {
      roles: string[];
    };
  };

  // CRUD permissions
  permissions?: {
    create?: boolean;
    read?: boolean;
    update?: boolean;
    delete?: boolean;
  };

  // Additional custom claims
  [key: string]: any;
}