import { CheckCircle } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

/**
 * Registration Success Page
 * Full page display showing registration success with 5 second countdown
 * Supports dark/light theme modes
 */
const RegistrationSuccess: React.FC = () => {
  const [countdown, setCountdown] = useState(5);
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get registration data from navigation state or URL params
  const queryParams = new URLSearchParams(location.search);
  const email = location.state?.email || queryParams.get('email') || 'your email';
  const username = location.state?.username || queryParams.get('username') || '';
  const autoLoginToken = location.state?.auto_login_token;

  useEffect(() => {
    // Save email for login page
    if (email) {
      sessionStorage.setItem('registered_email', email);
      sessionStorage.setItem('registration_success', 'true');
    }

    // Handle auto-login token if provided
    if (autoLoginToken) {
      localStorage.setItem('auth_token', autoLoginToken);
      localStorage.setItem('user_email', email);
    }

    // Start countdown
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          // Redirect based on whether we have auto-login token
          if (autoLoginToken) {
            navigate('/dashboard');
          } else {
            navigate(`/login?email=${encodeURIComponent(email)}&registered=true`);
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Cleanup
    return () => clearInterval(timer);
  }, [email, autoLoginToken, navigate]);

  const handleContinue = () => {
    if (autoLoginToken) {
      navigate('/dashboard');
    } else {
      navigate(`/login?email=${encodeURIComponent(email)}&registered=true`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {/* Success Card */}
        <div className="bg-white dark:bg-gray-800 dark:border dark:border-gray-700 rounded-2xl shadow-2xl p-8 text-center transform transition-all duration-500">
          
          {/* Animated Success Icon */}
          <div className="relative mb-6">
            <div className="w-24 h-24 mx-auto bg-gradient-to-r from-green-400 to-green-600 rounded-full flex items-center justify-center animate-bounce">
              <CheckCircle className="w-16 h-16 text-white" />
            </div>
            {/* Pulse Effect */}
            <div className="absolute inset-0 w-24 h-24 mx-auto bg-green-400 rounded-full animate-ping opacity-20"></div>
          </div>

          {/* Success Title */}
          <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100 mb-3">
            🎉 Congratulations!
          </h1>
          
          {/* Success Message */}
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-6">
            Your account has been created successfully
          </p>

          {/* User Info Card */}
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-gray-700 dark:to-gray-600 rounded-xl p-4 mb-6">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Registered Email:</p>
            <p className="text-lg font-semibold text-gray-800 dark:text-gray-100">{email}</p>
            {username && (
              <>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 mb-1">Username:</p>
                <p className="text-lg font-semibold text-gray-800 dark:text-gray-100">{username}</p>
              </>
            )}
          </div>

          {/* Next Steps */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-xl p-4 mb-6 text-left">
            <h3 className="font-semibold text-gray-700 dark:text-gray-200 mb-3">✨ What's Next?</h3>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
              <li className="flex items-start">
                <span className="text-green-500 mr-2 mt-0.5">✓</span>
                <span>Check your email for verification link (if required)</span>
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2 mt-0.5">✓</span>
                <span>Log in with your email and password</span>
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2 mt-0.5">✓</span>
                <span>Complete your profile settings</span>
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2 mt-0.5">✓</span>
                <span>Start exploring the platform features</span>
              </li>
            </ul>
          </div>

          {/* Countdown Timer */}
          <div className="mb-6">
            <p className="text-gray-600 dark:text-gray-300 mb-2">
              {autoLoginToken 
                ? 'Taking you to your dashboard in' 
                : 'Redirecting to login page in'}
            </p>
            <div className="relative">
              <div className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-blue-600">
                {countdown}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">seconds</div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 justify-center">
            <button
              onClick={handleContinue}
              className="px-8 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold rounded-lg hover:from-green-600 hover:to-green-700 transition-all duration-200 transform shadow-lg"
            >
              Continue Now
            </button>
            <button
              onClick={() => setCountdown(999)} // Stop countdown
              className="px-8 py-3 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 font-semibold rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500 transition-all duration-200"
            >
              Stay Here
            </button>
          </div>
        </div>

        {/* Additional Info */}
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Need help? {' '}
            <a href="/support" className="text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-medium">
              Contact Support
            </a>
          </p>
        </div>
      </div>

      {/* Background Decorations */}
      <div className="fixed top-10 left-10 w-20 h-20 bg-green-200 dark:bg-green-800 rounded-full mix-blend-multiply filter blur-xl opacity-70 dark:opacity-30 animate-blob"></div>
      <div className="fixed top-10 right-10 w-20 h-20 bg-purple-200 dark:bg-purple-800 rounded-full mix-blend-multiply filter blur-xl opacity-70 dark:opacity-30 animate-blob animation-delay-2000"></div>
      <div className="fixed bottom-10 left-20 w-20 h-20 bg-blue-200 dark:bg-blue-800 rounded-full mix-blend-multiply filter blur-xl opacity-70 dark:opacity-30 animate-blob animation-delay-4000"></div>
    </div>
  );
};

export default RegistrationSuccess;