import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Updated Registration Form Handler
 * Redirects to success page instead of login
 */
const handleRegistrationSubmit = async (formData: any) => {
  const navigate = useNavigate();
  
  try {
    const response = await fetch('http://localhost:8000/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData)
    });

    const data = await response.json();

    if (response.ok && data.success === true) {
      // SUCCESS! Redirect to success page with user data
      navigate('/registration-success', {
        state: {
          email: data.email,
          username: data.username,
          auto_login_token: data.auto_login_token,
          message: data.message,
          next_steps: data.next_steps
        }
      });
      
      // Alternative: Use query params if state doesn't work
      // navigate(`/registration-success?email=${encodeURIComponent(data.email)}&username=${encodeURIComponent(data.username || '')}`);
      
    } else {
      // Handle error - show error message
      const errorMessage = typeof data.detail === 'string' 
        ? data.detail 
        : data.detail?.message || 'Registration failed';
      
      // Show error in your UI
      showErrorMessage(errorMessage);
    }
  } catch (error) {
    console.error('Registration error:', error);
    showErrorMessage('Network error. Please try again.');
  }
};

/**
 * Example Registration Form Component
 */
export const RegistrationForm: React.FC = () => {
  const navigate = useNavigate();
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const formData = new FormData(e.currentTarget);
    const data = {
      email: formData.get('email') as string,
      password: formData.get('password') as string,
      username: formData.get('username') as string,
    };

    try {
      const response = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (response.ok && result.success === true) {
        // SUCCESS! Redirect to success page
        navigate('/registration-success', {
          state: {
            email: result.email,
            username: result.username,
            auto_login_token: result.auto_login_token
          }
        });
      } else {
        // Show error message
        const errorMsg = typeof result.detail === 'string' 
          ? result.detail 
          : 'Registration failed. Please check your information.';
        setError(errorMsg);
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}
      
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">
          Email
        </label>
        <input
          type="email"
          name="email"
          id="email"
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
      </div>

      <div>
        <label htmlFor="username" className="block text-sm font-medium text-gray-700">
          Username (optional)
        </label>
        <input
          type="text"
          name="username"
          id="username"
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">
          Password
        </label>
        <input
          type="password"
          name="password"
          id="password"
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
        <p className="mt-1 text-sm text-gray-500">
          Must contain: 8+ characters, uppercase, lowercase, number, special character
        </p>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        {loading ? 'Creating Account...' : 'Register'}
      </button>
    </form>
  );
};

// Helper function to show error messages
function showErrorMessage(message: string) {
  // Implementation depends on your UI framework
  // Could be a toast, modal, or inline error
  console.error('Registration error:', message);
  alert(message); // Simple fallback
}

export default RegistrationForm;