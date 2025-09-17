// React Hook for CRUD Permissions
// Provides easy access to user permissions in React components

import { useState, useEffect, useCallback } from 'react';
import { TokenPermissionParser, TokenPermissions } from '../utils/tokenPermissions';

export interface UsePermissionsReturn {
  permissions: TokenPermissions;
  hasPermission: (permission: keyof TokenPermissions) => boolean;
  hasFullCrud: boolean;
  canAccessResource: (resource: string) => boolean;
  allowedResources: string[];
  userRoles: string[];
  isLoading: boolean;
  error: string | null;
  refreshPermissions: () => void;
}

export function usePermissions(): UsePermissionsReturn {
  const [permissions, setPermissions] = useState<TokenPermissions>({
    create: false,
    read: false,
    update: false,
    delete: false
  });
  const [allowedResources, setAllowedResources] = useState<string[]>([]);
  const [userRoles, setUserRoles] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPermissions = useCallback(() => {
    try {
      setIsLoading(true);
      setError(null);

      // Get token from localStorage or sessionStorage
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
      
      if (!token) {
        setError('No authentication token found');
        setPermissions({
          create: false,
          read: false,
          update: false,
          delete: false
        });
        setAllowedResources([]);
        setUserRoles([]);
        return;
      }

      // Check if token is expired
      if (TokenPermissionParser.isTokenExpired(token)) {
        setError('Token has expired');
        // Optionally trigger token refresh here
        return;
      }

      // Extract permissions
      const extractedPermissions = TokenPermissionParser.extractPermissions(token);
      setPermissions(extractedPermissions);

      // Extract allowed resources
      const resources = TokenPermissionParser.getAllowedResources(token);
      setAllowedResources(resources);

      // Extract user roles
      const roles = TokenPermissionParser.getUserRoles(token);
      setUserRoles(roles);

    } catch (err) {
      console.error('Error loading permissions:', err);
      setError(err instanceof Error ? err.message : 'Failed to load permissions');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPermissions();

    // Listen for storage changes (e.g., token updates from other tabs)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'access_token') {
        loadPermissions();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [loadPermissions]);

  const hasPermission = useCallback((permission: keyof TokenPermissions): boolean => {
    return permissions[permission];
  }, [permissions]);

  const hasFullCrud = permissions.create && permissions.read && permissions.update && permissions.delete;

  const canAccessResource = useCallback((resource: string): boolean => {
    return allowedResources.includes(resource);
  }, [allowedResources]);

  return {
    permissions,
    hasPermission,
    hasFullCrud,
    canAccessResource,
    allowedResources,
    userRoles,
    isLoading,
    error,
    refreshPermissions: loadPermissions
  };
}

// HOC for protecting components based on permissions
export function withPermission<P extends object>(
  Component: React.ComponentType<P>,
  requiredPermission: keyof TokenPermissions | 'fullCrud'
) {
  return function ProtectedComponent(props: P) {
    const { permissions, hasFullCrud, isLoading } = usePermissions();

    if (isLoading) {
      return <div>Loading permissions...</div>;
    }

    const hasRequiredPermission = 
      requiredPermission === 'fullCrud' 
        ? hasFullCrud 
        : permissions[requiredPermission];

    if (!hasRequiredPermission) {
      return <div>You don't have permission to access this feature.</div>;
    }

    return <Component {...props} />;
  };
}

// Context provider for permissions (optional, for deeper component trees)
import React, { createContext, useContext } from 'react';

const PermissionsContext = createContext<UsePermissionsReturn | null>(null);

export function PermissionsProvider({ children }: { children: React.ReactNode }) {
  const permissions = usePermissions();
  
  return (
    <PermissionsContext.Provider value={permissions}>
      {children}
    </PermissionsContext.Provider>
  );
}

export function usePermissionsContext(): UsePermissionsReturn {
  const context = useContext(PermissionsContext);
  if (!context) {
    throw new Error('usePermissionsContext must be used within PermissionsProvider');
  }
  return context;
}