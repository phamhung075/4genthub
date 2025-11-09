import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { CircularProgress, Box } from '@mui/material';
import { useAuth } from '../../hooks/useAuth';
import { DISABLE_AUTH } from '../../config/environment';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireRoles = []
}) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  // Bypass authentication if VITE_DISABLE_AUTH is true
  if (DISABLE_AUTH) {
    console.info('🚫 Authentication bypassed (VITE_DISABLE_AUTH=true)');
    return <>{children}</>;
  }

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role requirements if specified
  if (requireRoles.length > 0 && user) {
    const hasRequiredRole = requireRoles.some(role =>
      user.roles.includes(role)
    );

    if (!hasRequiredRole) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  return <>{children}</>;
};