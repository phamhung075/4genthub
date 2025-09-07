# Troubleshooting: Supabase Email Not Sending

## Problem
The application shows "Verification email sent!" but no email is actually received.

## Root Causes

### 1. Free Tier Rate Limits
Supabase free tier has strict email limits:
- **3-4 emails per hour** maximum
- Resets every hour
- No queuing - emails beyond limit are dropped

### 2. Email Provider Configuration
By default, Supabase uses their internal email service which has limitations.

## Solutions

### Option 1: Check Email Logs in Supabase Dashboard

1. Go to your Supabase project dashboard
2. Navigate to **Authentication** → **Logs** 
3. Look for email events to see if they're being sent or rate-limited
4. Check **Authentication** → **Email Templates** to verify templates are configured

### Option 2: Use Supabase Dashboard for Testing

1. Go to **Authentication** → **Users**
2. Click "Invite User" or manually confirm users
3. This bypasses email for development

### Option 3: Configure Custom SMTP (Recommended for Production)

1. Go to **Project Settings** → **Auth**
2. Scroll to **SMTP Settings**
3. Enable "Custom SMTP"
4. Configure with your email provider:

#### Gmail SMTP Settings
```
SMTP Host: smtp.gmail.com
SMTP Port: 587
SMTP User: your-email@gmail.com
SMTP Pass: [App Password - not regular password]
Sender Email: your-email@gmail.com
Sender Name: Your App Name
```

#### SendGrid SMTP Settings
```
SMTP Host: smtp.sendgrid.net
SMTP Port: 587
SMTP User: apikey
SMTP Pass: [Your SendGrid API Key]
Sender Email: verified-sender@yourdomain.com
Sender Name: Your App Name
```

### Option 4: Development Workaround - Inbucket

For local development, use Inbucket (email testing tool):

```bash
# Run Inbucket locally
docker run -d --name inbucket \
  -p 9000:9000 \
  -p 2500:2500 \
  -p 1100:1100 \
  inbucket/inbucket

# Access at http://localhost:9000
```

Configure Supabase to use Inbucket:
```
SMTP Host: host.docker.internal (or localhost)
SMTP Port: 2500
No authentication required
```

### Option 5: Enable Email Confirmations in Supabase

1. Go to **Authentication** → **Providers** → **Email**
2. Ensure these settings:
   - **Enable Email Signup**: ✅ Enabled
   - **Confirm Email**: ✅ Enabled (should be on by default)
   - **Secure Email Change**: ✅ Enabled
   - **Secure Password Change**: ✅ Enabled

3. Check **Authentication** → **URL Configuration**:
   - **Site URL**: `http://localhost:3800` (or your production URL)
   - **Redirect URLs**: Add `http://localhost:3800/auth/verify`

### Option 6: Manual User Confirmation (Development)

For immediate testing without email:

```sql
-- In Supabase SQL Editor
UPDATE auth.users 
SET email_confirmed_at = NOW() 
WHERE email = 'user@example.com';
```

Or use the Supabase Admin API:

```python
# In supabase_auth.py, add this method for dev testing
async def confirm_user_manually(self, email: str) -> SupabaseAuthResult:
    """Dev only: Manually confirm a user without email"""
    try:
        # This requires service role key
        response = self.admin_client.auth.admin.update_user_by_id(
            uid=user_id,  # Get from users table
            attributes={"email_confirmed_at": datetime.now().isoformat()}
        )
        return SupabaseAuthResult(success=True)
    except Exception as e:
        logger.error(f"Manual confirmation failed: {e}")
        return SupabaseAuthResult(success=False)
```

## Verification Steps

1. **Check Rate Limits**:
   ```bash
   # Check recent signups
   curl http://localhost:8000/auth/supabase/health
   ```

2. **Verify Email Templates**:
   - Go to Supabase Dashboard → Authentication → Email Templates
   - Ensure "Confirm signup" template is active

3. **Test SMTP Connection**:
   ```python
   import smtplib
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('your-email@gmail.com', 'app-password')
   server.quit()
   print("SMTP connection successful")
   ```

## Best Practices

1. **Development**: Use Inbucket or manual confirmation
2. **Staging**: Use a transactional email service (SendGrid, Mailgun)
3. **Production**: Always use custom SMTP with proper email service
4. **Rate Limiting**: Implement email queuing in your application
5. **Monitoring**: Set up email delivery monitoring

## Common Issues

### "User already registered"
- The user exists but isn't confirmed
- Check auth.users table in Supabase

### No email after multiple attempts
- Rate limit reached (3-4 per hour on free tier)
- Wait 1 hour or upgrade Supabase plan

### Email in spam folder
- Add SPF, DKIM, DMARC records for your domain
- Use a reputable email service provider

## Quick Fix for Development

Add this to your `.env`:
```bash
# Development mode - skip email verification
SKIP_EMAIL_VERIFICATION=true
```

Then modify the signup flow to auto-confirm users in development:
```python
if os.getenv("SKIP_EMAIL_VERIFICATION") == "true":
    # Auto-confirm user for development
    # Note: This requires additional implementation
    pass
```

## Need Help?

1. Check Supabase Dashboard → Logs for email events
2. Review Supabase project settings
3. Contact Supabase support if on paid plan
4. Use alternative authentication methods (OAuth, Magic Link)