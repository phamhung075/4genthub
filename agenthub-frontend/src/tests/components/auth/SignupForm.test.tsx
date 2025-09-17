import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, useNavigate } from 'react-router-dom';
import { SignupForm } from '../../../components/auth/SignupForm';
import { useAuth } from '../../../hooks/useAuth';

// Mock dependencies
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useNavigate: jest.fn(),
  Link: ({ to, children }: any) => <a href={to}>{children}</a>,
}));

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

// Mock fetch
global.fetch = jest.fn();

// Mock import.meta.env
const mockEnv = {
  VITE_API_URL: 'http://localhost:8000'
};

Object.defineProperty(global, 'import', {
  value: {
    meta: {
      env: mockEnv
    }
  },
  writable: true,
  configurable: true
});

describe('SignupForm', () => {
  const mockNavigate = jest.fn();
  const mockSignup = jest.fn();
  let user: any;

  beforeEach(() => {
    jest.clearAllMocks();
    (useNavigate as jest.Mock).mockReturnValue(mockNavigate);
    (useAuth as jest.Mock).mockReturnValue({ signup: mockSignup });
    (global.fetch as jest.Mock).mockReset();
    user = userEvent.setup();
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <SignupForm />
      </BrowserRouter>
    );
  };

  describe('Form Rendering', () => {
    it('renders all form elements correctly', () => {
      renderComponent();

      expect(screen.getByText('Sign Up')).toBeInTheDocument();
      expect(screen.getByText('Create your account to get started')).toBeInTheDocument();
      expect(screen.getByLabelText('Email Address')).toBeInTheDocument();
      expect(screen.getByLabelText('Username')).toBeInTheDocument();
      expect(screen.getByLabelText('Password')).toBeInTheDocument();
      expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Sign Up' })).toBeInTheDocument();
      expect(screen.getByText('Already have an account? Sign In')).toBeInTheDocument();
    });

    it('has proper input attributes', () => {
      renderComponent();

      const emailInput = screen.getByLabelText('Email Address');
      expect(emailInput).toHaveAttribute('name', 'email');
      expect(emailInput).toHaveAttribute('type', 'text');
      expect(emailInput).toHaveAttribute('required');

      const passwordInput = screen.getByLabelText('Password');
      expect(passwordInput).toHaveAttribute('name', 'password');
      expect(passwordInput).toHaveAttribute('type', 'password');
      expect(passwordInput).toHaveAttribute('required');
    });
  });

  describe('Form Validation', () => {
    it('validates email format', async () => {
      renderComponent();

      const emailInput = screen.getByLabelText('Email Address');
      const submitButton = screen.getByRole('button', { name: 'Sign Up' });

      // Invalid email
      await user.type(emailInput, 'invalid-email');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Invalid email address')).toBeInTheDocument();
      });

      // Valid email
      await user.clear(emailInput);
      await user.type(emailInput, 'test@example.com');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.queryByText('Invalid email address')).not.toBeInTheDocument();
      });
    });

    it('validates username requirements', async () => {
      renderComponent();

      const usernameInput = screen.getByLabelText('Username');
      const submitButton = screen.getByRole('button', { name: 'Sign Up' });

      // Too short
      await user.type(usernameInput, 'ab');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Username must be at least 3 characters')).toBeInTheDocument();
      });

      // Too long
      await user.clear(usernameInput);
      await user.type(usernameInput, 'a'.repeat(21));
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Username must not exceed 20 characters')).toBeInTheDocument();
      });

      // Invalid characters
      await user.clear(usernameInput);
      await user.type(usernameInput, 'user@name');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Username can only contain letters, numbers, and underscores')).toBeInTheDocument();
      });
    });

    it('validates password requirements', async () => {
      renderComponent();

      const passwordInput = screen.getByLabelText('Password');
      const submitButton = screen.getByRole('button', { name: 'Sign Up' });

      // Too short
      await user.type(passwordInput, 'Pass1!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument();
      });

      // Too weak
      await user.clear(passwordInput);
      await user.type(passwordInput, 'password');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Password is too weak. Use a mix of uppercase, lowercase, numbers, and special characters')).toBeInTheDocument();
      });
    });

    it('validates password confirmation', async () => {
      renderComponent();

      const passwordInput = screen.getByLabelText('Password');
      const confirmPasswordInput = screen.getByLabelText('Confirm Password');
      const submitButton = screen.getByRole('button', { name: 'Sign Up' });

      await user.type(passwordInput, 'Password123!');
      await user.type(confirmPasswordInput, 'Password456!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
      });
    });

    it('validates all required fields', async () => {
      renderComponent();

      const submitButton = screen.getByRole('button', { name: 'Sign Up' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument();
        expect(screen.getByText('Username is required')).toBeInTheDocument();
        expect(screen.getByText('Password is required')).toBeInTheDocument();
        expect(screen.getByText('Please confirm your password')).toBeInTheDocument();
      });
    });
  });

  describe('Password Strength Indicator', () => {
    it('shows password strength as user types', async () => {
      renderComponent();

      const passwordInput = screen.getByLabelText('Password');

      // Weak password
      await user.type(passwordInput, 'weak');
      expect(screen.getByText('Very Weak')).toBeInTheDocument();

      // Medium password
      await user.clear(passwordInput);
      await user.type(passwordInput, 'Medium123');
      expect(screen.getByText('Fair')).toBeInTheDocument();

      // Strong password
      await user.clear(passwordInput);
      await user.type(passwordInput, 'Strong123!@#');
      expect(screen.getByText('Strong')).toBeInTheDocument();
    });

    it('shows password requirements checklist', async () => {
      renderComponent();

      const passwordInput = screen.getByLabelText('Password');
      
      await user.type(passwordInput, 'p');

      expect(screen.getByText('At least 8 characters')).toBeInTheDocument();
      expect(screen.getByText('One lowercase letter')).toBeInTheDocument();
      expect(screen.getByText('One uppercase letter')).toBeInTheDocument();
      expect(screen.getByText('One number')).toBeInTheDocument();
      expect(screen.getByText('One special character')).toBeInTheDocument();
    });
  });

  describe('Password Visibility Toggle', () => {
    it('toggles password visibility', async () => {
      renderComponent();

      const passwordInput = screen.getByLabelText('Password');
      const toggleButtons = screen.getAllByLabelText(/toggle password visibility/i);
      const passwordToggle = toggleButtons[0];

      expect(passwordInput).toHaveAttribute('type', 'password');

      await user.click(passwordToggle);
      expect(passwordInput).toHaveAttribute('type', 'text');

      await user.click(passwordToggle);
      expect(passwordInput).toHaveAttribute('type', 'password');
    });

    it('toggles confirm password visibility', async () => {
      renderComponent();

      const confirmPasswordInput = screen.getByLabelText('Confirm Password');
      const toggleButtons = screen.getAllByLabelText(/toggle confirm password visibility/i);
      const confirmPasswordToggle = toggleButtons[0];

      expect(confirmPasswordInput).toHaveAttribute('type', 'password');

      await user.click(confirmPasswordToggle);
      expect(confirmPasswordInput).toHaveAttribute('type', 'text');

      await user.click(confirmPasswordToggle);
      expect(confirmPasswordInput).toHaveAttribute('type', 'password');
    });
  });

  describe('Form Submission', () => {
    it('successfully signs up with email verification required', async () => {
      mockSignup.mockResolvedValueOnce({
        requires_email_verification: true,
        message: 'Please check your email to verify your account',
        success: true
      });

      renderComponent();

      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');

      const submitButton = screen.getByRole('button', { name: 'Sign Up' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockSignup).toHaveBeenCalledWith('test@example.com', 'testuser', 'Password123!');
        expect(screen.getByText('Please check your email to verify your account')).toBeInTheDocument();
        expect(screen.getByText('📧 Check your inbox for the verification email')).toBeInTheDocument();
        expect(screen.getByText('✅ Click the link in the email to verify your account')).toBeInTheDocument();
        expect(screen.getByText('🔐 After verification, you can sign in')).toBeInTheDocument();
      });

      // Submit button should be disabled
      expect(submitButton).toBeDisabled();
      expect(submitButton).toHaveTextContent('Check Your Email');
    });

    it('navigates to dashboard when email verification not required', async () => {
      mockSignup.mockResolvedValueOnce({
        success: true,
        requires_email_verification: false
      });

      renderComponent();

      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');

      await user.click(screen.getByRole('button', { name: 'Sign Up' }));

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
      });
    });

    it('handles signup errors for existing unverified users', async () => {
      mockSignup.mockRejectedValueOnce(new Error('User already registered but email not verified'));

      renderComponent();

      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');

      await user.click(screen.getByRole('button', { name: 'Sign Up' }));

      await waitFor(() => {
        expect(screen.getByText('This email is already registered but not verified.')).toBeInTheDocument();
        expect(screen.getByText('Would you like to resend the verification email?')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Resend Verification Email' })).toBeInTheDocument();
      });
    });

    it('handles general signup errors', async () => {
      mockSignup.mockRejectedValueOnce(new Error('Network error'));

      renderComponent();

      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');

      await user.click(screen.getByRole('button', { name: 'Sign Up' }));

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });
    });

    it('handles unexpected response format', async () => {
      mockSignup.mockResolvedValueOnce({ unexpected: 'response' });

      renderComponent();

      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');

      await user.click(screen.getByRole('button', { name: 'Sign Up' }));

      await waitFor(() => {
        expect(screen.getByText('Registration completed but response was unexpected. Please try signing in.')).toBeInTheDocument();
      });
    });

    it('shows loading state during submission', async () => {
      mockSignup.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

      renderComponent();

      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');

      const submitButton = screen.getByRole('button', { name: 'Sign Up' });
      await user.click(submitButton);

      expect(submitButton).toBeDisabled();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  describe('Resend Verification Email', () => {
    it('successfully resends verification email from success alert', async () => {
      mockSignup.mockResolvedValueOnce({
        requires_email_verification: true,
        message: 'Please verify your email'
      });

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      renderComponent();

      // Complete signup first
      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');
      await user.click(screen.getByRole('button', { name: 'Sign Up' }));

      await waitFor(() => {
        expect(screen.getByText("Didn't receive the email?")).toBeInTheDocument();
      });

      // Click resend button in success alert
      const resendButtons = screen.getAllByRole('button', { name: 'Resend Verification Email' });
      await user.click(resendButtons[0]);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          `${mockEnv.VITE_API_URL}/auth/supabase/resend-verification`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: 'test@example.com' })
          }
        );
        expect(screen.getByText('Verification email sent! Please check your inbox.')).toBeInTheDocument();
      });
    });

    it('handles resend verification error', async () => {
      mockSignup.mockRejectedValueOnce(new Error('User already registered'));

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Invalid email' })
      });

      renderComponent();

      // Trigger error state
      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');
      await user.click(screen.getByRole('button', { name: 'Sign Up' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Resend Verification Email' })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Resend Verification Email' }));

      await waitFor(() => {
        expect(screen.getByText('Invalid email')).toBeInTheDocument();
      });
    });

    it('handles resend verification network error', async () => {
      mockSignup.mockRejectedValueOnce(new Error('User already registered'));

      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      renderComponent();

      // Trigger error state
      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');
      await user.click(screen.getByRole('button', { name: 'Sign Up' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Resend Verification Email' })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Resend Verification Email' }));

      await waitFor(() => {
        expect(screen.getByText('Failed to resend verification email. Please try again.')).toBeInTheDocument();
      });
    });
  });

  describe('Navigation', () => {
    it('has link to sign in page', () => {
      renderComponent();

      const signInLink = screen.getByText('Already have an account? Sign In');
      expect(signInLink.closest('a')).toHaveAttribute('href', '/login');
    });
  });

  describe('Error Handling UI', () => {
    it('allows closing error alerts', async () => {
      mockSignup.mockRejectedValueOnce(new Error('Test error'));

      renderComponent();

      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');
      await user.click(screen.getByRole('button', { name: 'Sign Up' }));

      await waitFor(() => {
        expect(screen.getByText('Test error')).toBeInTheDocument();
      });

      const closeButton = screen.getByRole('button', { name: 'Close' });
      await user.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByText('Test error')).not.toBeInTheDocument();
      });
    });
  });

  describe('Environment Variables', () => {
    it('uses custom API URL from environment variable', async () => {
      const originalEnv = mockEnv.VITE_API_URL;
      mockEnv.VITE_API_URL = 'https://api.example.com';

      mockSignup.mockRejectedValueOnce(new Error('User already registered'));
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });

      renderComponent();

      // Trigger error state and resend
      await user.type(screen.getByLabelText('Email Address'), 'test@example.com');
      await user.type(screen.getByLabelText('Username'), 'testuser');
      await user.type(screen.getByLabelText('Password'), 'Password123!');
      await user.type(screen.getByLabelText('Confirm Password'), 'Password123!');
      await user.click(screen.getByRole('button', { name: 'Sign Up' }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Resend Verification Email' })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: 'Resend Verification Email' }));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'https://api.example.com/auth/supabase/resend-verification',
          expect.any(Object)
        );
      });

      mockEnv.VITE_API_URL = originalEnv;
    });
  });
});