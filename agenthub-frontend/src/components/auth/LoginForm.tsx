import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, Link } from 'react-router-dom';
import logger from '../../utils/logger';
import {
  Box,
  Button,
  TextField,
  Typography,
  Alert,
  Paper,
  FormControlLabel,
  Checkbox,
  IconButton,
  InputAdornment,
  CircularProgress,
  Divider,
  useTheme
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Email,
  Lock
} from '@mui/icons-material';
import { useAuth } from '../../hooks/useAuth';
import { ThemeToggle } from '../ThemeToggle';
import FallingGlitch from '../effects/FallingGlitch';
import VersionDisplay from '../VersionDisplay';
import { API_BASE_URL } from '../../config/environment';

interface LoginFormData {
  email: string;
  password: string;
  rememberMe: boolean;
}

export const LoginForm: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const theme = useTheme();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [backendVersion, setBackendVersion] = useState<string | undefined>(undefined);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  });

  // Fetch backend version on component mount to verify connection
  useEffect(() => {
    const fetchBackendVersion = async () => {
      try {
        // Use the configured API URL from environment
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.version) {
            setBackendVersion(data.version);
          }
        } else {
          // Backend is not responding properly
          setBackendVersion(undefined);
        }
      } catch (err) {
        // Backend is not reachable
        logger.debug('Backend not connected:', err);
        setBackendVersion(undefined);
      }
    };

    fetchBackendVersion();
  }, []);

  const onSubmit = async (data: LoginFormData) => {
    setError(null);
    setIsLoading(true);

    try {
      await login(data.email, data.password);
      navigate('/dashboard');
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred during login');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

  return (
    <Box sx={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden' }}>
      <FallingGlitch
        glitchColors={theme.palette.mode === 'dark' 
          ? ["#ff7cce", "#7cf0ff", "#fcf07c", "#8E44AD", "#3498DB"]
          : ["#ff5fa3", "#5cd9ff", "#ffd85c", "#9B59B6", "#5DADE2"]
        }
        backgroundColor={theme.palette.mode === 'dark' ? "#080A12" : "#0f1419"}
        fontSize={12}
        glitchSpeed={60}
        glitchIntensity={0.03}
        fallSpeed={0.5}
        outerVignette={true}
      >
        {/* Theme Toggle in top-right corner */}
        <Box sx={{ position: 'absolute', top: 16, right: 16, zIndex: 20 }}>
          <ThemeToggle />
        </Box>
        
        <Box
          sx={{
            width: '100%',
            maxWidth: 420,
            px: 2,
          }}
        >
          <Paper
            elevation={6}
            sx={{
              padding: 4,
              width: '100%',
              borderRadius: 3,
              backgroundColor: theme.palette.mode === 'dark' 
                ? 'rgba(18, 18, 18, 0.95)' 
                : 'rgba(255, 255, 255, 0.98)',
              backdropFilter: 'blur(10px)',
              border: theme.palette.mode === 'dark'
                ? '1px solid rgba(255, 255, 255, 0.1)'
                : '1px solid rgba(0, 0, 0, 0.05)',
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
            <Lock
              sx={{
                fontSize: 40,
                color: 'primary.main',
                mb: 1,
              }}
            />
            <Typography component="h1" variant="h5">
              Sign In
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Welcome back! Please sign in to continue.
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
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
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 8,
                  message: 'Password must be at least 8 characters',
                },
              })}
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type={showPassword ? 'text' : 'password'}
              id="password"
              autoComplete="current-password"
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

            <FormControlLabel
              control={
                <Checkbox
                  {...register('rememberMe')}
                  value="remember"
                  color="primary"
                />
              }
              label="Remember me"
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={isLoading}
            >
              {isLoading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                'Sign In'
              )}
            </Button>

            <Divider sx={{ my: 2 }}>OR</Divider>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
              <Link to="/forgot-password" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" color="primary">
                  Forgot password?
                </Typography>
              </Link>
              <Link to="/signup" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" color="primary">
                  Don't have an account? Sign Up
                </Typography>
              </Link>
            </Box>
          </Box>
          </Paper>
        </Box>
      </FallingGlitch>
      
      {/* Version display in bottom right */}
      <VersionDisplay backendVersion={backendVersion} />
    </Box>
  );
};