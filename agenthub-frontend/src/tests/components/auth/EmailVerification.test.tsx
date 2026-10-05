import React from 'react';
import { render, screen, waitFor, fireEvent, act } from './../../test-utils';
import { useNavigate } from 'react-router-dom';
import { EmailVerification } from '../../../components/auth/EmailVerification';
import { API_BASE_URL } from '../../../config/environment';
import { useAuth } from '../../../hooks/useAuth';

// Mock dependencies
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: vi.fn(),
  };
});

vi.mock('../../../hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

// Mock fetch
global.fetch = vi.fn();

describe('EmailVerification', () => {
  const mockNavigate = vi.fn();
  const mockSetTokens = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useNavigate as any).mockReturnValue(mockNavigate);
    (useAuth as any).mockReturnValue({ setTokens: mockSetTokens });

    // Reset fetch mock
    (global.fetch as any).mockReset();

    // Clear window.location.hash
    window.location.hash = '';
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const renderComponent = () => {
    return render(
      <EmailVerification />
    );
  };

  describe('Initial Rendering', () => {
    // The hash is parsed in an effect during render, so the 'processing' state is never
    // observable; without a hash the component settles on the invalid-link state.
    it('renders the verification card for a link without tokens', () => {
      renderComponent();

      expect(screen.getByText('Email Verification')).toBeInTheDocument();
      expect(screen.getByText('Verification failed')).toBeInTheDocument();
      expect(screen.getByText('Email link is invalid or has expired')).toBeInTheDocument();
    });
  });

  describe('Successful Verification', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    it('handles successful email verification for signup', async () => {
      window.location.hash = '#access_token=test-access&refresh_token=test-refresh&type=signup';

      renderComponent();

      // The hash is parsed in an effect that runs during render, so no waiting is needed
      // (and waitFor would hang under fake timers).
      expect(mockSetTokens).toHaveBeenCalledWith({
        access_token: 'test-access',
        refresh_token: 'test-refresh'
      });

      expect(screen.getByText('Verification complete!')).toBeInTheDocument();
      expect(screen.getByText('Email verified successfully! Welcome to agenthub.')).toBeInTheDocument();

      // Check navigation after timeout
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });

    it('handles successful email verification for password recovery', async () => {
      window.location.hash = '#access_token=test-access&refresh_token=test-refresh&type=recovery';

      renderComponent();

      // The hash is parsed in an effect that runs during render, so no waiting is needed
      // (and waitFor would hang under fake timers).
      expect(mockSetTokens).toHaveBeenCalledWith({
        access_token: 'test-access',
        refresh_token: 'test-refresh'
      });

      expect(screen.getByText('Password reset verified. You can now set a new password.')).toBeInTheDocument();

      // Check navigation to reset password page
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      expect(mockNavigate).toHaveBeenCalledWith('/reset-password');
    });

    it('handles successful email verification without type', async () => {
      window.location.hash = '#access_token=test-access&refresh_token=test-refresh';

      renderComponent();

      // The hash is parsed in an effect that runs during render, so no waiting is needed
      // (and waitFor would hang under fake timers).
      expect(mockSetTokens).toHaveBeenCalledWith({
        access_token: 'test-access',
        refresh_token: 'test-refresh'
      });

      expect(screen.getByText('Email verified successfully!')).toBeInTheDocument();

      act(() => {
        vi.advanceTimersByTime(2000);
      });
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
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      });

      const emailInput = screen.getByPlaceholderText('Enter your email address');
      const submitButton = screen.getByRole('button', { name: 'Resend Verification Email' });

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
      (global.fetch as any).mockResolvedValueOnce({
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
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

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

    it('posts to the configured API base URL', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      renderComponent();

      const emailInput = screen.getByPlaceholderText('Enter your email address');
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(screen.getByRole('button', { name: 'Resend Verification Email' }));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          `${API_BASE_URL}/auth/supabase/resend-verification`,
          expect.any(Object)
        );
      });
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
    it('shows the success state for a link with tokens and the error state for an error link', () => {
      window.location.hash = '#access_token=test&refresh_token=test';
      const { unmount } = renderComponent();
      expect(screen.getByText('Verification complete!')).toBeInTheDocument();
      unmount();

      // The hash is only read on mount, so the error state needs a fresh render.
      window.location.hash = '#error=invalid';
      renderComponent();
      expect(screen.getByText('Verification failed')).toBeInTheDocument();
    });
  });
});
