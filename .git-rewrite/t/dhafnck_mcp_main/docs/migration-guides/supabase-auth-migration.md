# Supabase Authentication Migration Guide

## Overview
This guide explains how to migrate from the custom authentication system to Supabase's built-in authentication with automatic email verification.

## Why Supabase Auth?
- **Built-in email verification**: No need to build custom email sending
- **Password reset flows**: Automatic password recovery emails
- **OAuth providers**: Easy integration with Google, GitHub, etc.
- **Security**: Battle-tested authentication system
- **Session management**: Automatic token refresh and session handling

## Backend Changes

### New Endpoints
The Supabase Auth endpoints are available at `/auth/supabase/*`:

| Old Endpoint | New Endpoint | Description |
|-------------|--------------|-------------|
| `/auth/register` | `/auth/supabase/signup` | User registration with auto email verification |
| `/auth/login` | `/auth/supabase/signin` | User login |
| `/auth/logout` | `/auth/supabase/signout` | User logout |
| `/auth/me` | `/auth/supabase/me` | Get current user |
| `/auth/verify-email` | Automatic via Supabase | Email verification handled by Supabase |
| `/auth/reset-password` | `/auth/supabase/password-reset` | Request password reset email |
| N/A | `/auth/supabase/update-password` | Update password with token |
| N/A | `/auth/supabase/resend-verification` | Resend verification email |
| N/A | `/auth/supabase/oauth/{provider}` | OAuth provider URLs |

### Response Format
```typescript
interface AuthResponse {
  success: boolean;
  message: string;
  user?: {
    id: string;
    email: string;
    email_confirmed: boolean;
    created_at: string;
    user_metadata: {
      username?: string;
      full_name?: string;
    };
  };
  access_token?: string;
  refresh_token?: string;
  requires_email_verification?: boolean;
}
```

## Frontend Integration

### 1. Install Supabase Client
```bash
npm install @supabase/supabase-js
```

### 2. Initialize Supabase Client
```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || 'https://pmswmvxhzdfxeqsfdgif.supabase.co'
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBtc3dtdnhoemRmeGVxc2ZkZ2lmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ1MjAzOTcsImV4cCI6MjA3MDA5NjM5N30.UyHFbWB4qRRkEFjHIrvyjk0h_l1w85dAa7pa-POC4a4'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### 3. Update Authentication Service
```typescript
// src/services/auth.ts
import { supabase } from '../lib/supabase'

export const authService = {
  async signUp(email: string, password: string, metadata?: any) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: metadata,
        emailRedirectTo: `${window.location.origin}/auth/verify`
      }
    })
    
    if (error) throw error
    
    // Check if email verification is required
    if (data.user && !data.user.confirmed_at) {
      return {
        success: true,
        user: data.user,
        requires_email_verification: true,
        message: 'Please check your email to verify your account'
      }
    }
    
    return { success: true, user: data.user, session: data.session }
  },

  async signIn(email: string, password: string) {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    })
    
    if (error) {
      if (error.message.includes('Email not confirmed')) {
        throw new Error('Please verify your email before signing in')
      }
      throw error
    }
    
    return { success: true, user: data.user, session: data.session }
  },

  async signOut() {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
    return { success: true }
  },

  async resetPassword(email: string) {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`
    })
    
    if (error) throw error
    return { success: true, message: 'Password reset email sent' }
  },

  async updatePassword(newPassword: string) {
    const { error } = await supabase.auth.updateUser({
      password: newPassword
    })
    
    if (error) throw error
    return { success: true }
  },

  async getUser() {
    const { data: { user } } = await supabase.auth.getUser()
    return user
  },

  onAuthStateChange(callback: (event: string, session: any) => void) {
    return supabase.auth.onAuthStateChange(callback)
  }
}
```

### 4. Update Login Component
```tsx
// src/components/Login.tsx
import { useState } from 'react'
import { authService } from '../services/auth'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    
    try {
      const result = await authService.signIn(email, password)
      
      if (result.success) {
        // Redirect to dashboard or home
        window.location.href = '/dashboard'
      }
    } catch (err: any) {
      if (err.message.includes('verify your email')) {
        setMessage('Please check your email for verification link')
        // Optionally show resend verification button
      } else {
        setError(err.message || 'Login failed')
      }
    }
  }

  const handleResendVerification = async () => {
    try {
      // Call backend endpoint to resend verification
      const response = await fetch('/auth/supabase/resend-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      })
      
      if (response.ok) {
        setMessage('Verification email sent! Please check your inbox.')
      }
    } catch (err) {
      setError('Failed to resend verification email')
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="error">{error}</div>}
      {message && (
        <div className="info">
          {message}
          <button type="button" onClick={handleResendVerification}>
            Resend Verification Email
          </button>
        </div>
      )}
      
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      
      <button type="submit">Sign In</button>
    </form>
  )
}
```

### 5. Handle Email Verification Callback
```tsx
// src/pages/auth/verify.tsx
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

export function EmailVerification() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying')

  useEffect(() => {
    // Supabase will redirect here with tokens in URL
    const error = searchParams.get('error')
    const errorDescription = searchParams.get('error_description')
    
    if (error) {
      setStatus('error')
      console.error('Verification error:', errorDescription)
    } else {
      setStatus('success')
      // Redirect to login after 3 seconds
      setTimeout(() => {
        window.location.href = '/login'
      }, 3000)
    }
  }, [searchParams])

  return (
    <div>
      {status === 'verifying' && <p>Verifying your email...</p>}
      {status === 'success' && (
        <div>
          <p>✅ Email verified successfully!</p>
          <p>Redirecting to login...</p>
        </div>
      )}
      {status === 'error' && (
        <div>
          <p>❌ Email verification failed</p>
          <p>Please try again or contact support</p>
        </div>
      )}
    </div>
  )
}
```

### 6. Setup Auth State Listener
```tsx
// src/App.tsx
import { useEffect, useState } from 'react'
import { authService } from './services/auth'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Get initial user
    authService.getUser().then(setUser).finally(() => setLoading(false))
    
    // Listen for auth changes
    const { data: { subscription } } = authService.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN') {
        setUser(session?.user ?? null)
      } else if (event === 'SIGNED_OUT') {
        setUser(null)
      } else if (event === 'USER_UPDATED') {
        setUser(session?.user ?? null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div>
      {user ? <AuthenticatedApp user={user} /> : <UnauthenticatedApp />}
    </div>
  )
}
```

## Environment Variables

Add these to your frontend `.env` file:
```env
REACT_APP_SUPABASE_URL=https://pmswmvxhzdfxeqsfdgif.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBtc3dtdnhoemRmeGVxc2ZkZ2lmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ1MjAzOTcsImV4cCI6MjA3MDA5NjM5N30.UyHFbWB4qRRkEFjHIrvyjk0h_l1w85dAa7pa-POC4a4
```

## Supabase Dashboard Configuration

1. **Email Templates**: 
   - Go to Authentication > Email Templates in Supabase dashboard
   - Customize verification email template
   - Customize password reset email template

2. **URL Configuration**:
   - Set Site URL to your frontend URL (e.g., `http://localhost:3800`)
   - Add redirect URLs for email callbacks

3. **Email Settings**:
   - Configure SMTP settings for production
   - Enable email verification requirement

## Testing the Migration

1. **Test Registration**:
   - Register a new user
   - Check email for verification link
   - Click link and verify redirect works

2. **Test Login**:
   - Try login before verification (should fail)
   - Login after verification (should succeed)
   - Check tokens are stored correctly

3. **Test Password Reset**:
   - Request password reset
   - Check email for reset link
   - Complete password reset flow

4. **Test Session Management**:
   - Verify tokens refresh automatically
   - Check user stays logged in on page refresh
   - Verify logout clears session

## Rollback Plan

If issues arise, you can temporarily use both systems:
1. Keep old endpoints active as `/auth/legacy/*`
2. Use feature flag to switch between systems
3. Gradually migrate users to new system

## Common Issues

### Email Not Sending
- Check Supabase email settings
- Verify SMTP configuration for production
- Check spam folder

### Verification Link Not Working
- Ensure redirect URLs are configured in Supabase
- Check frontend routing for `/auth/verify` page
- Verify tokens are being parsed correctly

### Session Not Persisting
- Check localStorage for Supabase session
- Verify auth state listener is set up
- Ensure tokens are being refreshed

## Benefits After Migration

✅ **Automatic email verification** - No custom email service needed
✅ **Password reset flows** - Built-in forgot password functionality  
✅ **OAuth providers** - Easy social login integration
✅ **Session management** - Automatic token refresh
✅ **Security** - Battle-tested authentication system
✅ **User management** - Admin panel in Supabase dashboard
✅ **Audit logs** - Authentication events tracked automatically

## Next Steps

1. Configure email templates in Supabase dashboard
2. Update frontend components to use Supabase client
3. Test all authentication flows
4. Deploy and monitor for issues
5. Consider adding OAuth providers (Google, GitHub, etc.)