import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AuthWrapper } from '../../../components/auth/AuthWrapper';
import { AuthProvider } from '../../../contexts/AuthContext';
import { MuiThemeWrapper } from '../../../contexts/MuiThemeProvider';

// Mock the context providers
jest.mock('../../../contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="auth-provider">{children}</div>
  ),
}));

jest.mock('../../../contexts/MuiThemeProvider', () => ({
  MuiThemeWrapper: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mui-theme-wrapper">{children}</div>
  ),
}));

describe('AuthWrapper', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders children correctly', () => {
    const testContent = 'Test Child Content';
    
    render(
      <AuthWrapper>
        <div>{testContent}</div>
      </AuthWrapper>
    );
    
    expect(screen.getByText(testContent)).toBeInTheDocument();
  });

  it('wraps children with AuthProvider', () => {
    render(
      <AuthWrapper>
        <div>Test Content</div>
      </AuthWrapper>
    );
    
    expect(screen.getByTestId('auth-provider')).toBeInTheDocument();
  });

  it('wraps children with MuiThemeWrapper', () => {
    render(
      <AuthWrapper>
        <div>Test Content</div>
      </AuthWrapper>
    );
    
    expect(screen.getByTestId('mui-theme-wrapper')).toBeInTheDocument();
  });

  it('maintains correct nesting order', () => {
    render(
      <AuthWrapper>
        <div data-testid="child-content">Test Content</div>
      </AuthWrapper>
    );
    
    const authProvider = screen.getByTestId('auth-provider');
    const muiThemeWrapper = screen.getByTestId('mui-theme-wrapper');
    const childContent = screen.getByTestId('child-content');
    
    // Check that MuiThemeWrapper is inside AuthProvider
    expect(authProvider).toContainElement(muiThemeWrapper);
    
    // Check that child content is inside MuiThemeWrapper
    expect(muiThemeWrapper).toContainElement(childContent);
  });

  it('renders multiple children correctly', () => {
    render(
      <AuthWrapper>
        <div>First Child</div>
        <div>Second Child</div>
        <span>Third Child</span>
      </AuthWrapper>
    );
    
    expect(screen.getByText('First Child')).toBeInTheDocument();
    expect(screen.getByText('Second Child')).toBeInTheDocument();
    expect(screen.getByText('Third Child')).toBeInTheDocument();
  });

  it('handles null children gracefully', () => {
    render(
      <AuthWrapper>
        {null}
      </AuthWrapper>
    );
    
    expect(screen.getByTestId('auth-provider')).toBeInTheDocument();
    expect(screen.getByTestId('mui-theme-wrapper')).toBeInTheDocument();
  });

  it('handles undefined children gracefully', () => {
    render(
      <AuthWrapper>
        {undefined}
      </AuthWrapper>
    );
    
    expect(screen.getByTestId('auth-provider')).toBeInTheDocument();
    expect(screen.getByTestId('mui-theme-wrapper')).toBeInTheDocument();
  });

  it('passes through complex React elements', () => {
    const ComplexComponent = () => (
      <div>
        <h1>Title</h1>
        <p>Paragraph</p>
        <button>Button</button>
      </div>
    );
    
    render(
      <AuthWrapper>
        <ComplexComponent />
      </AuthWrapper>
    );
    
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Paragraph')).toBeInTheDocument();
    expect(screen.getByText('Button')).toBeInTheDocument();
  });
});