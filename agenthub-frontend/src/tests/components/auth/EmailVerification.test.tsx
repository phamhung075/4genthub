import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter, useNavigate } from 'react-router-dom';
import { EmailVerification } from '../../../components/auth/EmailVerification';
import { useAuth } from '../../../hooks/useAuth';

// Mock dependencies
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: jest.fn(),
}));

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

// Mock fetch
global.fetch = jest.fn();

describe('EmailVerification', () => {
  const mockNavigate = jest.fn();
  const mockSetTokens = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useNavigate as jest.Mock).mockReturnValue(mockNavigate);
    (useAuth as jest.Mock).mockReturnValue({ setTokens: mockSetTokens });
    
    // Reset fetch mock
    (global.fetch as jest.Mock).mockReset();
    
    // Clear window.location.hash
    window.location.hash = '';
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <EmailVerification />
      </BrowserRouter>
    );
  };

  describe('Initial Rendering', () => {
    it('renders processing state initially', () => {
      renderComponent();
      
      expect(screen.getByText('Email Verification')).toBeInTheDocument();
      expect(screen.getByText('Processing your verification...')).toBeInTheDocument();
      expect(screen.getByText('Verifying your email...')).toBeInTheDocument();
    });
  });

  describe('Successful Verification', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    it('handles successful email verification for signup', async () => {
      window.location.hash = '#access_token=test-access&refresh_token=test-refresh&type=signup';
      
      renderComponent();

      await waitFor(() => {
        expect(mockSetTokens).toHaveBeenCalledWith({
          access_token: 'test-access',
          refresh_token: 'test-refresh'
        });
      });

      expect(screen.getByText('Verification complete!')).toBeInTheDocument();
      expect(screen.getByText('Email verified successfully! Welcome to agenthub.')).toBeInTheDocument();

      // Check navigation after timeout
      jest.advanceTimersByTime(2000);
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });

    it('handles successful email verification for password recovery', async () => {
      window.location.hash = '#access_token=test-access&refresh_token=test-refresh&type=recovery';
      
      renderComponent();

      await waitFor(() => {
        expect(mockSetTokens).toHaveBeenCalledWith({
          access_token: 'test-access',
          refresh_token: 'test-refresh'
        });
      });

      expect(screen.getByText('Password reset verified. You can now set a new password.')).toBeInTheDocument();

      // Check navigation to reset password page
      jest.advanceTimersByTime(2000);
      expect(mockNavigate).toHaveBeenCalledWith('/reset-password');
    });

    it('handles successful email verification without type', async () => {
      window.location.hash = '#access_token=test-access&refresh_token=test-refresh';
      
      renderComponent();

      await waitFor(() => {
        expect(mockSetTokens).toHaveBeenCalledWith({
          access_token: 'test-access',
          refresh_token: 'test-refresh'
        });
      });

      expect(screen.getByText('Email verified successfully!')).toBeInTheDocument();

      jest.advanceTimersByTime(2000);
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  describe('Error Handling', () => {
    it('handles error from URL parameters', async () => {
      window.location.hash = '#error=invalid_request&error_description=Custom error message';
      
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Verification failed')).toBeInTheDocument();
        expect(screen.getByText('Custom error message')).toBeInTheDocument();
      });

      expect(mockSetTokens).not.toHaveBeenCalled();
    });

    it('handles error without description', async () => {
      window.location.hash = '#error=invalid_request';
      
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Verification failed. Please try again.')).toBeInTheDocument();
      });
    });

    it('handles invalid or expired link', async () => {
      // No tokens in hash
      window.location.hash = '';
      
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Verification failed')).toBeInTheDocument();
        expect(screen.getByText('Email link is invalid or has expired')).toBeInTheDocument();
      });

      // Should show resend form
      expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      expect(screen.getByText('Resend Verification Email')).toBeInTheDocument();
    });
  });

  describe('Resend Verification Email', () => {
    beforeEach(() => {
      // Set up error state with resend form
      window.location.hash = '';
    });

    it('validates email input before sending', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      });

      const submitButton = screen.getByText('Resend Verification Email');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Please enter your email address')).toBeInTheDocument();
      });

      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('successfully resends verification email', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      });

      const emailInput = screen.getByPlaceholderText('Enter your email address');
      const submitButton = screen.getByText('Resend Verification Email');

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(submitButton);

      // Check loading state
      expect(screen.getByText('Sending...')).toBeInTheDocument();
      expect(emailInput).toBeDisabled();
      expect(submitButton).toBeDisabled();

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://localhost:8000/auth/supabase/resend-verification',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: 'test@example.com' }),
          }
        );
      });

      await waitFor(() => {
        expect(screen.getByText('Verification email sent! Please check your inbox.')).toBeInTheDocument();
        expect(screen.getByText('Verification complete!')).toBeInTheDocument();
      });

      // Resend form should be hidden
      expect(screen.queryByPlaceholderText('Enter your email address')).not.toBeInTheDocument();
    });

    it('handles resend verification API error', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Email not found' }),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      });

      const emailInput = screen.getByPlaceholderText('Enter your email address');
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(screen.getByText('Resend Verification Email'));

      await waitFor(() => {
        expect(screen.getByText('Email not found')).toBeInTheDocument();
      });
    });

    it('handles resend verification network error', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      renderComponent();

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      });

      const emailInput = screen.getByPlaceholderText('Enter your email address');
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(screen.getByText('Resend Verification Email'));

      await waitFor(() => {
        expect(screen.getByText('Failed to resend verification email. Please try again.')).toBeInTheDocument();
      });
    });

    it('uses custom API URL from environment variable', async () => {
      // Mock import.meta.env
      const originalViteApiUrl = (import.meta as any).env.VITE_API_URL;
      (import.meta as any).env = { VITE_API_URL: 'https://api.example.com' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      });

      const emailInput = screen.getByPlaceholderText('Enter your email address');
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(screen.getByText('Resend Verification Email'));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'https://api.example.com/auth/supabase/resend-verification',
          expect.any(Object)
        );
      });

      // Restore original
      (import.meta as any).env.VITE_API_URL = originalViteApiUrl;
    });
  });

  describe('Navigation Buttons', () => {
    it('shows navigation buttons on error without resend form', async () => {
      window.location.hash = '#error=invalid_request';
      
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Go to Sign Up')).toBeInTheDocument();
        expect(screen.getByText('Go to Login')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Go to Sign Up'));
      expect(mockNavigate).toHaveBeenCalledWith('/signup');

      fireEvent.click(screen.getByText('Go to Login'));
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });

    it('shows navigation buttons on error with resend form', async () => {
      window.location.hash = '';
      
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Go to Sign Up')).toBeInTheDocument();
        expect(screen.getByText('Go to Login')).toBeInTheDocument();
      });

      const signupButtons = screen.getAllByText('Go to Sign Up');
      const loginButtons = screen.getAllByText('Go to Login');

      fireEvent.click(signupButtons[0]);
      expect(mockNavigate).toHaveBeenCalledWith('/signup');

      fireEvent.click(loginButtons[0]);
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });

  describe('UI Elements', () => {
    it('displays correct icons for different states', async () => {
      const { rerender } = renderComponent();

      // Processing state - uses Loader2 icon
      expect(screen.getByText('Email Verification')).toBeInTheDocument();
      
      // Success state
      window.location.hash = '#access_token=test&refresh_token=test';
      rerender(
        <BrowserRouter>
          <EmailVerification />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Verification complete!')).toBeInTheDocument();
      });

      // Error state
      window.location.hash = '#error=invalid';
      rerender(
        <BrowserRouter>
          <EmailVerification />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Verification failed')).toBeInTheDocument();
      });
    });
  });
});