# Supabase Email Configuration - Quick Reference

## 🚀 Quick Access Links

- **Dashboard**: https://supabase.com/dashboard/project/pmswmvxhzdfxeqsfdgif
- **Email Templates**: https://supabase.com/dashboard/project/pmswmvxhzdfxeqsfdgif/auth/templates
- **Auth Settings**: https://supabase.com/dashboard/project/pmswmvxhzdfxeqsfdgif/auth/providers
- **SMTP Settings**: https://supabase.com/dashboard/project/pmswmvxhzdfxeqsfdgif/settings/auth
- **URL Config**: https://supabase.com/dashboard/project/pmswmvxhzdfxeqsfdgif/auth/url-configuration
- **Auth Logs**: https://supabase.com/dashboard/project/pmswmvxhzdfxeqsfdgif/logs/auth-logs

## 📋 Configuration Checklist

### Essential Steps
- [ ] Access Supabase Dashboard
- [ ] Configure "Confirm signup" email template
- [ ] Configure "Reset Password" email template
- [ ] Enable email confirmations in Auth settings
- [ ] Set Site URL to `http://localhost:3800`
- [ ] Add redirect URLs for callbacks
- [ ] Test email sending

### Optional Steps
- [ ] Configure "Magic Link" template
- [ ] Configure "Invite User" template
- [ ] Set up custom SMTP for production
- [ ] Customize email branding
- [ ] Configure email expiry times

## 📝 Template Variables

| Variable | Description | Used In |
|----------|-------------|---------|
| `{{ .ConfirmationURL }}` | Action link (verify, reset, etc.) | All templates |
| `{{ .Email }}` | Recipient's email address | All templates |
| `{{ .TokenHash }}` | Security token hash | Advanced use |
| `{{ .RedirectTo }}` | Redirect URL after action | OAuth templates |

## 🔧 Key Settings

### Email Provider Settings
```
☑️ Enable email confirmations
☑️ Enable secure email change
☐ Enable double confirm email (optional)
Confirmation expiry: 86400 (24 hours)
```

### Development URLs
```
Site URL: http://localhost:3800

Redirect URLs:
- http://localhost:3800/auth/callback
- http://localhost:3800/auth/verify
- http://localhost:3800/auth/reset-password
```

### Production URLs
```
Site URL: https://yourdomain.com

Redirect URLs:
- https://yourdomain.com/auth/callback
- https://yourdomain.com/auth/verify
- https://yourdomain.com/auth/reset-password
```

## 🎨 Email Template Structure

### Basic HTML Template
```html
<!DOCTYPE html>
<html>
<head>
  <style>
    /* Your CSS styles */
  </style>
</head>
<body>
  <div class="container">
    <h2>Email Title</h2>
    <p>Message content</p>
    <a href="{{ .ConfirmationURL }}" class="button">
      Call to Action
    </a>
    <p>Fallback link: {{ .ConfirmationURL }}</p>
  </div>
</body>
</html>
```

## 📧 SMTP Providers

| Provider | Host | Port | Notes |
|----------|------|------|-------|
| SendGrid | smtp.sendgrid.net | 587 | Popular, reliable |
| Mailgun | smtp.mailgun.org | 587 | Good for high volume |
| AWS SES | email-smtp.[region].amazonaws.com | 587 | Cost-effective |
| Gmail | smtp.gmail.com | 587 | App password required |
| Outlook | smtp-mail.outlook.com | 587 | Microsoft accounts |

## 🐛 Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| Emails not sending | Check SMTP settings, verify credentials |
| Emails in spam | Configure custom SMTP, add SPF/DKIM records |
| Links not working | Verify redirect URLs are configured |
| Template not updating | Clear cache, save and refresh |
| Variables not replaced | Use correct syntax: `{{ .Variable }}` |

## 📊 Testing Checklist

### Verification Email Test
1. Register new user
2. Check inbox (and spam)
3. Verify email renders correctly
4. Click verification link
5. Confirm redirect works

### Password Reset Test
1. Request password reset
2. Check inbox for email
3. Verify email appearance
4. Click reset link
5. Complete password reset

### Magic Link Test (if enabled)
1. Request magic link
2. Check inbox
3. Click login link
4. Verify instant login

## 🔍 Monitoring

### Check Email Status
```sql
-- In Supabase SQL Editor
SELECT 
  created_at,
  email,
  event_message,
  status
FROM auth.audit_log_entries
WHERE action = 'user.email.send'
ORDER BY created_at DESC
LIMIT 20;
```

### Email Metrics to Track
- Send success rate
- Open rates (if tracking enabled)
- Click rates on verification links
- Time to verify after signup
- Bounce rates

## 🚨 Emergency Contacts

### If Emails Stop Working:
1. Check Supabase Status: https://status.supabase.com
2. Verify SMTP credentials haven't expired
3. Check auth logs for errors
4. Test with default Supabase SMTP
5. Contact Supabase Support if needed

## 💡 Pro Tips

1. **Always test in development first** before changing production templates
2. **Keep templates simple** - complex HTML may not render in all clients
3. **Include text fallbacks** for all links
4. **Use inline CSS** - many email clients strip `<style>` tags
5. **Test across email clients** - Gmail, Outlook, Apple Mail, etc.
6. **Monitor delivery rates** regularly
7. **Set up SPF/DKIM** for custom domains
8. **Keep subject lines under 50 characters**
9. **Use preheader text** for better inbox preview
10. **Include unsubscribe links** where legally required

## 📚 Resources

- [Supabase Auth Docs](https://supabase.com/docs/guides/auth)
- [Email Template Best Practices](https://supabase.com/docs/guides/auth/auth-email-templates)
- [SMTP Configuration Guide](https://supabase.com/docs/guides/auth/auth-smtp)
- [Email Testing Tools](https://www.mail-tester.com/)
- [HTML Email Validators](https://www.htmlemailcheck.com/)