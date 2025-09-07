# Quick Guide: Manual User Confirmation for Development

## Problem
Supabase email verification not working due to:
- Free tier rate limits (3-4 emails/hour)
- No SMTP configuration

## Quick Solution for Development

### Option 1: Use Supabase Dashboard (Easiest)

1. Go to your [Supabase Dashboard](https://app.supabase.com)
2. Navigate to **Authentication** → **Users**
3. Find the user by email
4. Click on the user row
5. Click **"Confirm Email"** button

### Option 2: Use SQL Editor in Supabase

1. Go to Supabase Dashboard → **SQL Editor**
2. Run this query:

```sql
-- Replace with actual email
UPDATE auth.users 
SET email_confirmed_at = NOW(),
    confirmed_at = NOW()
WHERE email = 'daihung.pham@yahoo.fr';

-- Verify it worked
SELECT id, email, email_confirmed_at, confirmed_at 
FROM auth.users 
WHERE email = 'daihung.pham@yahoo.fr';
```

### Option 3: Direct Database Access

If you have direct database access:

```bash
# Connect to Supabase database
psql postgresql://[connection-string]

# Run the confirmation query
UPDATE auth.users 
SET email_confirmed_at = NOW() 
WHERE email = 'your-email@example.com';
```

## After Confirmation

Once the user is confirmed manually:
1. Go to http://localhost:3800/login
2. Sign in with the email and password
3. You should be redirected to the dashboard

## Long-term Solutions

### For Development:
- Use Inbucket for local email testing
- Create a development bypass flag

### For Production:
1. Configure SMTP in Supabase:
   - Go to **Project Settings** → **Auth** → **SMTP Settings**
   - Enable custom SMTP
   - Add your email provider credentials

2. Recommended providers:
   - SendGrid (10,000 emails/month free)
   - Mailgun (5,000 emails/month free)
   - Amazon SES (62,000 emails/month free)

## Checking Email Status

To see if emails are being sent:
1. Supabase Dashboard → **Authentication** → **Logs**
2. Look for email events
3. Check for rate limit errors

## Rate Limit Reset

If you've hit the rate limit:
- Wait 1 hour for the limit to reset
- Or use manual confirmation methods above

## Testing Multiple Users

For testing with multiple users quickly:

```sql
-- Confirm all unconfirmed users (DEV ONLY!)
UPDATE auth.users 
SET email_confirmed_at = NOW() 
WHERE email_confirmed_at IS NULL;
```

⚠️ **WARNING**: Never run this in production!