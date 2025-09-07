import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { CheckCircle, XCircle, Loader2, Mail } from 'lucide-react';

export const EmailVerification: React.FC = () => {
  const navigate = useNavigate();
  const { setTokens } = useAuth();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Verifying your email...');
  const [showResendForm, setShowResendForm] = useState(false);
  const [resendEmail, setResendEmail] = useState('');
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMessage, setResendMessage] = useState('');

  useEffect(() => {
    // Parse the URL hash to extract tokens
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');
    const type = params.get('type');
    const error = params.get('error');
    const errorDescription = params.get('error_description');

    if (error) {
      setStatus('error');
      setMessage(errorDescription || 'Verification failed. Please try again.');
      return;
    }

    if (accessToken && refreshToken) {
      // Store the tokens
      setTokens({
        access_token: accessToken,
        refresh_token: refreshToken
      });

      setStatus('success');
      
      if (type === 'signup') {
        setMessage('Email verified successfully! Welcome to DhafnckMCP.');
      } else if (type === 'recovery') {
        setMessage('Password reset verified. You can now set a new password.');
        // For password recovery, redirect to a password reset form
        setTimeout(() => {
          navigate('/reset-password');
        }, 2000);
        return;
      } else {
        setMessage('Email verified successfully!');
      }

      // Redirect to dashboard after a short delay
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    } else {
      setStatus('error');
      setMessage('Email link is invalid or has expired');
      setShowResendForm(true);
    }
  }, [setTokens, navigate]);

  const handleResendVerification = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!resendEmail) {
      setResendMessage('Please enter your email address');
      return;
    }

    setResendLoading(true);
    setResendMessage('');

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/auth/supabase/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: resendEmail }),
      });

      const data = await response.json();
      
      if (response.ok && data.success) {
        setStatus('success');
        setMessage('Verification email sent! Please check your inbox.');
        setShowResendForm(false);
      } else {
        setResendMessage(data.detail || 'Failed to resend verification email. Please try again.');
      }
    } catch (err) {
      setResendMessage('Failed to resend verification email. Please try again.');
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Email Verification</CardTitle>
          <CardDescription>
            {status === 'processing' && 'Processing your verification...'}
            {status === 'success' && 'Verification complete!'}
            {status === 'error' && 'Verification failed'}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center space-y-4">
          {status === 'processing' && (
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
          )}
          {status === 'success' && (
            <CheckCircle className="h-12 w-12 text-green-500" />
          )}
          {status === 'error' && (
            <XCircle className="h-12 w-12 text-red-500" />
          )}
          
          <p className="text-center text-sm text-gray-600 dark:text-gray-400">
            {message}
          </p>

          {status === 'error' && showResendForm && (
            <div className="flex flex-col space-y-4 w-full">
              <form onSubmit={handleResendVerification} className="flex flex-col space-y-3">
                <input
                  type="email"
                  placeholder="Enter your email address"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                  disabled={resendLoading}
                />
                <button
                  type="submit"
                  disabled={resendLoading}
                  className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                >
                  {resendLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Sending...</span>
                    </>
                  ) : (
                    <>
                      <Mail className="h-4 w-4" />
                      <span>Resend Verification Email</span>
                    </>
                  )}
                </button>
              </form>
              
              {resendMessage && (
                <p className="text-sm text-red-500 text-center">{resendMessage}</p>
              )}
              
              <div className="flex flex-col space-y-2">
                <button
                  onClick={() => navigate('/signup')}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  Go to Sign Up
                </button>
                <button
                  onClick={() => navigate('/login')}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  Go to Login
                </button>
              </div>
            </div>
          )}
          
          {status === 'error' && !showResendForm && (
            <div className="flex flex-col space-y-2 w-full">
              <button
                onClick={() => navigate('/signup')}
                className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
              >
                Go to Sign Up
              </button>
              <button
                onClick={() => navigate('/login')}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Go to Login
              </button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};