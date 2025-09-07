# Supabase Redirect URL Configuration

## Overview
This document explains how to configure redirect URLs in Supabase Dashboard for email verification and OAuth flows to work correctly with the DhafnckMCP frontend.

## Required Redirect URLs

### Development Environment
```
http://localhost:3800/auth/verify
```

### Production Environment
```
https://yourdomain.com/auth/verify
```

## Configuration Steps

### 1. Access Supabase Dashboard
1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Navigate to **Authentication** → **URL Configuration**

### 2. Update Site URL
Set the Site URL to your frontend URL:
- Development: `http://localhost:3800`
- Production: `https://yourdomain.com`

### 3. Update Redirect URLs
In the **Redirect URLs** section, add the following URLs:

#### For Development:
```
http://localhost:3800/auth/verify
http://localhost:3800/dashboard
http://localhost:3800/reset-password
```

#### For Production:
```
https://yourdomain.com/auth/verify
https://yourdomain.com/dashboard
https://yourdomain.com/reset-password
```

### 4. Email Template Variables
Ensure your email templates use the correct redirect URL variable:

In your email templates, use:
```
{{ .SiteURL }}/auth/verify#access_token={{ .Token }}&type={{ .Type }}
```

Or if using the confirmation URL directly:
```
{{ .ConfirmationURL }}
```

## Important Notes

### Port Configuration
- The frontend runs on port **3800** (not 3000)
- The backend API runs on port **8000**
- Ensure all redirect URLs use the correct port

### URL Hash vs Query Parameters
- Supabase returns tokens as URL hash fragments (`#access_token=...`)
- The EmailVerification component parses these from `window.location.hash`
- This is more secure as hash fragments are not sent to the server

### CORS Configuration
The backend already includes CORS configuration for:
- `http://localhost:3800`
- `http://localhost:3000` (legacy)

## Verification Flow

1. User signs up → Supabase sends verification email
2. User clicks link → Redirected to `http://localhost:3800/auth/verify#access_token=...`
3. EmailVerification component:
   - Extracts tokens from URL hash
   - Stores tokens in cookies/context
   - Redirects to dashboard

## Testing

### Test Email Verification:
1. Sign up with a real email address
2. Check inbox for verification email
3. Click the link
4. Verify redirect to `http://localhost:3800/auth/verify`
5. Confirm automatic redirect to dashboard after token storage

### Test Password Reset:
1. Request password reset
2. Check email for reset link
3. Click link and verify redirect
4. Confirm password reset form appears

## Troubleshooting

### "Invalid redirect URL" Error
- Ensure the exact URL is added to Redirect URLs in Supabase
- Check for trailing slashes (should not have them)
- Verify the protocol (http vs https)

### Tokens Not Being Captured
- Check browser console for errors
- Verify the EmailVerification component is mounted at `/auth/verify`
- Ensure the URL hash is properly formatted

### CORS Errors
- Verify backend CORS configuration includes your frontend URL
- Check that credentials are included in requests

## Security Considerations

1. **Production URLs**: Always use HTTPS in production
2. **Allowed Domains**: Only add trusted domains to redirect URLs
3. **Token Expiry**: Tokens expire after 1 hour by default
4. **One-time Use**: Verification tokens can only be used once

## Related Documentation
- [Supabase Email Templates](./supabase-email-template-configuration.md)
- [Authentication Migration Guide](../migration-guides/supabase-auth-migration.md)