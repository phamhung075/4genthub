import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, Link } from 'react-router-dom';
import {
  Box,
  Button,
  TextField,
  Typography,
  Alert,
  Container,
  Paper,
  IconButton,
  InputAdornment,
  CircularProgress,
  Divider,
  LinearProgress,
  useTheme
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Email,
  Lock,
  Person,
  CheckCircle,
  Cancel
} from '@mui/icons-material';
import { useAuth } from '../../hooks/useAuth';
import { ThemeToggle } from '../ThemeToggle';

interface SignupFormData {
  email: string;
  username: string;
  password: string;
  confirmPassword: string;
}

interface PasswordStrength {
  score: number;
  message: string;
  color: 'error' | 'warning' | 'success';
}

export const SignupForm: React.FC = () => {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const theme = useTheme();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [emailVerificationRequired, setEmailVerificationRequired] = useState(false);
  const [showResendOption, setShowResendOption] = useState(false);
  const [resendEmail, setResendEmail] = useState<string>('');
  const [passwordStrength, setPasswordStrength] = useState<PasswordStrength>({
    score: 0,
    message: '',
    color: 'error'
  });

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<SignupFormData>({
    defaultValues: {
      email: '',
      username: '',
      password: '',
      confirmPassword: '',
    },
  });

  const password = watch('password');

  // Calculate password strength
  React.useEffect(() => {
    if (!password) {
      setPasswordStrength({ score: 0, message: '', color: 'error' });
      return;
    }

    let score = 0;
    const checks = {
      length: password.length >= 8,
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      numbers: /\d/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    };

    Object.values(checks).forEach(passed => {
      if (passed) score += 20;
    });

    let message = '';
    let color: 'error' | 'warning' | 'success' = 'error';

    if (score <= 20) {
      message = 'Very Weak';
      color = 'error';
    } else if (score <= 40) {
      message = 'Weak';
      color = 'error';
    } else if (score <= 60) {
      message = 'Fair';
      color = 'warning';
    } else if (score <= 80) {
      message = 'Good';
      color = 'warning';
    } else {
      message = 'Strong';
      color = 'success';
    }

    setPasswordStrength({ score, message, color });
  }, [password]);

  const handleResendVerification = async () => {
    setError(null);
    setSuccess(null);
    setIsLoading(true);
    
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
        setSuccess('Verification email sent! Please check your inbox.');
        setShowResendOption(false);
        setEmailVerificationRequired(true);
      } else {
        setError(data.detail || 'Failed to resend verification email');
      }
    } catch (err) {
      setError('Failed to resend verification email. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmit = async (data: SignupFormData) => {
    setError(null);
    setSuccess(null);
    setIsLoading(true);
    setShowResendOption(false);

    try {
      const result = await signup(data.email, data.username, data.password);
      
      // Check if email verification is required
      if (result?.requires_email_verification) {
        setEmailVerificationRequired(true);
        setSuccess(result.message || 'Registration successful! Please check your email to verify your account.');
        setError(null);
        setResendEmail(data.email); // Store email for resend option
        // Don't navigate away - let user see the success message
      } else if (result?.success) {
        // Registration successful - navigate to success page
        navigate('/registration-success', {
          state: {
            email: data.email,
            username: data.username,
            auto_login_token: result.auto_login_token || result.access_token
          }
        });
      } else {
        // Handle unexpected response format
        setError('Registration completed but response was unexpected. Please try signing in.');
      }
    } catch (err) {
      if (err instanceof Error) {
        // Check if error is about existing unverified user
        if (err.message.includes('already registered') || 
            err.message.includes('already exists') || 
            err.message.includes('User already registered')) {
          setError('This email is already registered but not verified.');
          setShowResendOption(true);
          setResendEmail(data.email);
        } else {
          setError(err.message);
        }
      } else {
        setError('An unexpected error occurred during registration');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

  const handleToggleConfirmPassword = () => {
    setShowConfirmPassword(!showConfirmPassword);
  };

  return (
    <Container component="main" maxWidth="xs">
      {/* Theme Toggle in top-right corner */}
      <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
        <ThemeToggle />
      </Box>
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            padding: 4,
            width: '100%',
            borderRadius: 2,
            backgroundColor: theme.palette.mode === 'dark' ? 'background.paper' : 'background.default',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              mb: 3,
            }}
          >
            <Person
              sx={{
                fontSize: 40,
                color: 'primary.main',
                mb: 1,
              }}
            />
            <Typography component="h1" variant="h5">
              Sign Up
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Create your account to get started
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => {
              setError(null);
              setShowResendOption(false);
            }}>
              {error}
              {showResendOption && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    Would you like to resend the verification email?
                  </Typography>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={handleResendVerification}
                    disabled={isLoading}
                    startIcon={isLoading ? <CircularProgress size={16} /> : <Email />}
                  >
                    {isLoading ? 'Sending...' : 'Resend Verification Email'}
                  </Button>
                </Box>
              )}
            </Alert>
          )}

          {success && (
            <Alert 
              severity="success" 
              sx={{ mb: 2 }}
              icon={<CheckCircle />}
            >
              {success}
              {emailVerificationRequired && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="body2">
                    📧 Check your inbox for the verification email
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    ✅ Click the link in the email to verify your account
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    🔐 After verification, you can sign in
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    Didn't receive the email?
                  </Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleResendVerification}
                    disabled={isLoading}
                    startIcon={isLoading ? <CircularProgress size={16} /> : <Email />}
                  >
                    {isLoading ? 'Sending...' : 'Resend Verification Email'}
                  </Button>
                </Box>
              )}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
            <TextField
              {...register('email', {
                required: 'Email is required',
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: 'Invalid email address',
                },
              })}
              margin="normal"
              required
              fullWidth
              id="email"
              label="Email Address"
              name="email"
              autoComplete="email"
              autoFocus
              error={!!errors.email}
              helperText={errors.email?.message}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Email />
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              {...register('username', {
                required: 'Username is required',
                minLength: {
                  value: 3,
                  message: 'Username must be at least 3 characters',
                },
                maxLength: {
                  value: 20,
                  message: 'Username must not exceed 20 characters',
                },
                pattern: {
                  value: /^[a-zA-Z0-9_]+$/,
                  message: 'Username can only contain letters, numbers, and underscores',
                },
              })}
              margin="normal"
              required
              fullWidth
              id="username"
              label="Username"
              name="username"
              autoComplete="username"
              error={!!errors.username}
              helperText={errors.username?.message}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Person />
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 8,
                  message: 'Password must be at least 8 characters',
                },
                validate: value => {
                  if (passwordStrength.score < 40) {
                    return 'Password is too weak. Use a mix of uppercase, lowercase, numbers, and special characters';
                  }
                  return true;
                }
              })}
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type={showPassword ? 'text' : 'password'}
              id="password"
              autoComplete="new-password"
              error={!!errors.password}
              helperText={errors.password?.message}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={handleTogglePassword}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            {password && (
              <Box sx={{ mt: 1, mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <LinearProgress
                    variant="determinate"
                    value={passwordStrength.score}
                    sx={{
                      flexGrow: 1,
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: 'grey.300',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: 
                          passwordStrength.color === 'error' ? 'error.main' :
                          passwordStrength.color === 'warning' ? 'warning.main' :
                          'success.main',
                      },
                    }}
                  />
                  <Typography
                    variant="caption"
                    sx={{ 
                      ml: 2,
                      color: 
                        passwordStrength.color === 'error' ? 'error.main' :
                        passwordStrength.color === 'warning' ? 'warning.main' :
                        'success.main',
                    }}
                  >
                    {passwordStrength.message}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                  <PasswordRequirement met={password.length >= 8} text="At least 8 characters" />
                  <PasswordRequirement met={/[a-z]/.test(password)} text="One lowercase letter" />
                  <PasswordRequirement met={/[A-Z]/.test(password)} text="One uppercase letter" />
                  <PasswordRequirement met={/\d/.test(password)} text="One number" />
                  <PasswordRequirement met={/[!@#$%^&*(),.?":{}|<>]/.test(password)} text="One special character" />
                </Box>
              </Box>
            )}

            <TextField
              {...register('confirmPassword', {
                required: 'Please confirm your password',
                validate: value =>
                  value === password || 'Passwords do not match',
              })}
              margin="normal"
              required
              fullWidth
              name="confirmPassword"
              label="Confirm Password"
              type={showConfirmPassword ? 'text' : 'password'}
              id="confirmPassword"
              autoComplete="new-password"
              error={!!errors.confirmPassword}
              helperText={errors.confirmPassword?.message}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle confirm password visibility"
                      onClick={handleToggleConfirmPassword}
                      edge="end"
                    >
                      {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={isLoading || emailVerificationRequired}
            >
              {isLoading ? (
                <CircularProgress size={24} color="inherit" />
              ) : emailVerificationRequired ? (
                'Check Your Email'
              ) : (
                'Sign Up'
              )}
            </Button>

            <Divider sx={{ my: 2 }}>OR</Divider>

            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
              <Link to="/login" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" color="primary">
                  Already have an account? Sign In
                </Typography>
              </Link>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

// Password requirement indicator component
const PasswordRequirement: React.FC<{ met: boolean; text: string }> = ({ met, text }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
    {met ? (
      <CheckCircle sx={{ fontSize: 16, color: 'success.main' }} />
    ) : (
      <Cancel sx={{ fontSize: 16, color: 'text.disabled' }} />
    )}
    <Typography
      variant="caption"
      sx={{ color: met ? 'success.main' : 'text.disabled' }}
    >
      {text}
    </Typography>
  </Box>
);