// Token Permission Utilities
// Parse and validate CRUD permissions from JWT tokens

import logger from './logger';

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
  permissions?: TokenPermissions;
  allowed_resources?: string[];
  
  // Scopes
  scope?: string;
}

export class TokenPermissionParser {
  /**
   * Decode JWT token without verification (for client-side use)
   */
  static decodeToken(token: string): DecodedToken | null {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        logger.error('Invalid JWT format');
        return null;
      }
      
      const payload = parts[1];
      const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
      return decoded;
    } catch (error) {
      logger.error('Error decoding token:', error);
      return null;
    }
  }
  
  /**
   * Extract CRUD permissions from token
   */
  static extractPermissions(token: string): TokenPermissions {
    const decoded = this.decodeToken(token);
    
    if (!decoded) {
      return {
        create: false,
        read: false,
        update: false,
        delete: false
      };
    }
    
    // Check direct permissions object
    if (decoded.permissions) {
      return {
        create: decoded.permissions.create || false,
        read: decoded.permissions.read || false,
        update: decoded.permissions.update || false,
        delete: decoded.permissions.delete || false
      };
    }
    
    // Check scope-based permissions
    const scope = decoded.scope || '';
    const scopes = scope.split(' ');
    
    return {
      create: scopes.includes('mcp-crud-create'),
      read: scopes.includes('mcp-crud-read'),
      update: scopes.includes('mcp-crud-update'),
      delete: scopes.includes('mcp-crud-delete')
    };
  }
  
  /**
   * Check if user has specific permission
   */
  static hasPermission(token: string, permission: keyof TokenPermissions): boolean {
    const permissions = this.extractPermissions(token);
    return permissions[permission];
  }
  
  /**
   * Check if user has all CRUD permissions
   */
  static hasFullCrud(token: string): boolean {
    const permissions = this.extractPermissions(token);
    return permissions.create && permissions.read && permissions.update && permissions.delete;
  }
  
  /**
   * Get allowed resources from token
   */
  static getAllowedResources(token: string): string[] {
    const decoded = this.decodeToken(token);
    
    if (!decoded) {
      return [];
    }
    
    // Check direct allowed_resources
    if (decoded.allowed_resources) {
      return decoded.allowed_resources;
    }
    
    // Default resources based on role
    const roles = decoded.realm_roles || [];
    if (roles.includes('admin')) {
      return ['projects', 'tasks', 'contexts', 'agents', 'branches', 'subtasks', 'users', 'settings'];
    } else if (roles.includes('developer')) {
      return ['projects', 'tasks', 'contexts', 'agents', 'branches', 'subtasks'];
    } else if (roles.includes('user')) {
      return ['tasks', 'contexts', 'subtasks'];
    }
    
    return [];
  }
  
  /**
   * Check if user can access specific resource
   */
  static canAccessResource(token: string, resource: string): boolean {
    const allowedResources = this.getAllowedResources(token);
    return allowedResources.includes(resource);
  }
  
  /**
   * Get user roles from token
   */
  static getUserRoles(token: string): string[] {
    const decoded = this.decodeToken(token);
    
    if (!decoded) {
      return [];
    }
    
    // Combine realm roles and client roles
    const realmRoles = decoded.realm_roles || [];
    const realmAccessRoles = decoded.realm_access?.roles || [];
    
    return [...new Set([...realmRoles, ...realmAccessRoles])];
  }
  
  /**
   * Check if token is expired
   */
  static isTokenExpired(token: string): boolean {
    const decoded = this.decodeToken(token);
    
    if (!decoded || !decoded.exp) {
      return true;
    }
    
    const now = Date.now() / 1000;
    return decoded.exp < now;
  }
  
  /**
   * Get token expiration time
   */
  static getTokenExpiration(token: string): Date | null {
    const decoded = this.decodeToken(token);
    
    if (!decoded || !decoded.exp) {
      return null;
    }
    
    return new Date(decoded.exp * 1000);
  }
  
  /**
   * Generate permission matrix for UI
   */
  static getPermissionMatrix(token: string): Record<string, TokenPermissions> {
    const resources = this.getAllowedResources(token);
    const permissions = this.extractPermissions(token);
    
    const matrix: Record<string, TokenPermissions> = {};
    
    resources.forEach(resource => {
      matrix[resource] = { ...permissions };
    });
    
    return matrix;
  }
}

// Export convenience functions
export const hasPermission = TokenPermissionParser.hasPermission;
export const extractPermissions = TokenPermissionParser.extractPermissions;
export const hasFullCrud = TokenPermissionParser.hasFullCrud;
export const canAccessResource = TokenPermissionParser.canAccessResource;
export const getUserRoles = TokenPermissionParser.getUserRoles;
export const isTokenExpired = TokenPermissionParser.isTokenExpired;