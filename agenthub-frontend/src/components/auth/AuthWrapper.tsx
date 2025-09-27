import React from 'react';
import { AuthProvider } from '../../contexts/AuthContext';
import { MuiThemeWrapper } from '../../contexts/MuiThemeProvider';

interface AuthWrapperProps {
  children: React.ReactNode;
}

export const AuthWrapper: React.FC<AuthWrapperProps> = ({ children }) => {
  return (
    <AuthProvider>
      <MuiThemeWrapper>
        {children}
      </MuiThemeWrapper>
    </AuthProvider>
  );
};