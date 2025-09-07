# Supabase Email Template Configuration Guide

## Step-by-Step Instructions for Email Template Setup

### Prerequisites
- Access to Supabase Dashboard
- Project: `pmswmvxhzdfxeqsfdgif` (DhafnckMCP)
- Admin access to Authentication settings

## Step 1: Access Supabase Dashboard

1. **Open Supabase Dashboard**
   - Go to: https://supabase.com/dashboard
   - Sign in with your credentials

2. **Select Your Project**
   - Project name: `mcp_ai_notebook` or `pmswmvxhzdfxeqsfdgif`
   - URL: https://supabase.com/dashboard/project/pmswmvxhzdfxeqsfdgif

## Step 2: Navigate to Email Templates

1. **Go to Authentication Section**
   - In the left sidebar, click on **"Authentication"** icon (🔐)
   - Or direct link: https://supabase.com/dashboard/project/pmswmvxhzdfxeqsfdgif/auth/templates

2. **Select Email Templates**
   - Under Authentication, click on **"Email Templates"**
   - You'll see a list of available email templates

## Step 3: Configure Email Verification Template

### 3.1 Select "Confirm signup" Template
This template is sent when users register.

1. **Click on "Confirm signup"** in the template list

2. **Configure Template Settings:**
   ```
   Subject: Verify your email for DhafnckMCP
   ```

3. **Edit Email Body (HTML):**
   ```html
   <!DOCTYPE html>
   <html>
   <head>
     <style>
       body {
         font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
         line-height: 1.6;
         color: #333;
         max-width: 600px;
         margin: 0 auto;
         padding: 20px;
       }
       .container {
         background: #ffffff;
         border-radius: 10px;
         box-shadow: 0 2px 10px rgba(0,0,0,0.1);
         padding: 30px;
       }
       .header {
         text-align: center;
         margin-bottom: 30px;
       }
       .logo {
         font-size: 28px;
         font-weight: bold;
         color: #4F46E5;
       }
       .content {
         margin-bottom: 30px;
       }
       .button {
         display: inline-block;
         padding: 14px 30px;
         background-color: #4F46E5;
         color: white !important;
         text-decoration: none;
         border-radius: 6px;
         font-weight: 600;
         margin: 20px 0;
       }
       .button:hover {
         background-color: #4338CA;
       }
       .footer {
         margin-top: 30px;
         padding-top: 20px;
         border-top: 1px solid #e5e5e5;
         text-align: center;
         font-size: 14px;
         color: #666;
       }
       .warning {
         background-color: #FEF3C7;
         border-left: 4px solid #F59E0B;
         padding: 12px;
         margin: 20px 0;
       }
     </style>
   </head>
   <body>
     <div class="container">
       <div class="header">
         <div class="logo">🚀 DhafnckMCP</div>
         <h2>Verify Your Email Address</h2>
       </div>
       
       <div class="content">
         <p>Hi there,</p>
         
         <p>Welcome to <strong>DhafnckMCP</strong> - Your AI Agent Orchestration Platform!</p>
         
         <p>Please verify your email address by clicking the button below:</p>
         
         <div style="text-align: center;">
           <a href="{{ .ConfirmationURL }}" class="button">
             Verify Email Address
           </a>
         </div>
         
         <div class="warning">
           <strong>⚠️ Important:</strong> This verification link will expire in 24 hours.
         </div>
         
         <p>If you didn't create an account with DhafnckMCP, you can safely ignore this email.</p>
         
         <p>If the button doesn't work, copy and paste this link into your browser:</p>
         <p style="word-break: break-all; color: #4F46E5;">
           {{ .ConfirmationURL }}
         </p>
       </div>
       
       <div class="footer">
         <p>© 2025 DhafnckMCP. All rights reserved.</p>
         <p>This is an automated email. Please do not reply.</p>
       </div>
     </div>
   </body>
   </html>
   ```

4. **Save the Template**
   - Click **"Save"** button at the bottom

## Step 4: Configure Password Reset Template

### 4.1 Select "Reset Password" Template

1. **Click on "Reset Password"** in the template list

2. **Configure Template Settings:**
   ```
   Subject: Reset your DhafnckMCP password
   ```

3. **Edit Email Body (HTML):**
   ```html
   <!DOCTYPE html>
   <html>
   <head>
     <style>
       body {
         font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
         line-height: 1.6;
         color: #333;
         max-width: 600px;
         margin: 0 auto;
         padding: 20px;
       }
       .container {
         background: #ffffff;
         border-radius: 10px;
         box-shadow: 0 2px 10px rgba(0,0,0,0.1);
         padding: 30px;
       }
       .header {
         text-align: center;
         margin-bottom: 30px;
       }
       .logo {
         font-size: 28px;
         font-weight: bold;
         color: #4F46E5;
       }
       .content {
         margin-bottom: 30px;
       }
       .button {
         display: inline-block;
         padding: 14px 30px;
         background-color: #DC2626;
         color: white !important;
         text-decoration: none;
         border-radius: 6px;
         font-weight: 600;
         margin: 20px 0;
       }
       .button:hover {
         background-color: #B91C1C;
       }
       .footer {
         margin-top: 30px;
         padding-top: 20px;
         border-top: 1px solid #e5e5e5;
         text-align: center;
         font-size: 14px;
         color: #666;
       }
       .security-notice {
         background-color: #FEE2E2;
         border-left: 4px solid #DC2626;
         padding: 12px;
         margin: 20px 0;
       }
       .info-box {
         background-color: #EFF6FF;
         border-left: 4px solid #3B82F6;
         padding: 12px;
         margin: 20px 0;
       }
     </style>
   </head>
   <body>
     <div class="container">
       <div class="header">
         <div class="logo">🔐 DhafnckMCP</div>
         <h2>Password Reset Request</h2>
       </div>
       
       <div class="content">
         <p>Hi there,</p>
         
         <p>We received a request to reset your password for your DhafnckMCP account.</p>
         
         <div style="text-align: center;">
           <a href="{{ .ConfirmationURL }}" class="button">
             Reset Password
           </a>
         </div>
         
         <div class="security-notice">
           <strong>🔒 Security Notice:</strong> This link will expire in 1 hour for your security.
         </div>
         
         <div class="info-box">
           <strong>ℹ️ Didn't request this?</strong><br>
           If you didn't request a password reset, you can safely ignore this email. 
           Your password won't be changed unless you click the link above and create a new one.
         </div>
         
         <p>If the button doesn't work, copy and paste this link into your browser:</p>
         <p style="word-break: break-all; color: #DC2626;">
           {{ .ConfirmationURL }}
         </p>
       </div>
       
       <div class="footer">
         <p>© 2025 DhafnckMCP. All rights reserved.</p>
         <p>This is an automated security email. Please do not reply.</p>
         <p style="font-size: 12px; color: #999;">
           For security reasons, we never include your password in emails.
         </p>
       </div>
     </div>
   </body>
   </html>
   ```

4. **Save the Template**
   - Click **"Save"** button

## Step 5: Configure Magic Link Template (Optional)

### 5.1 Select "Magic Link" Template
For passwordless authentication.

1. **Click on "Magic Link"** in the template list

2. **Configure Template Settings:**
   ```
   Subject: Your DhafnckMCP login link
   ```

3. **Edit Email Body (HTML):**
   ```html
   <!DOCTYPE html>
   <html>
   <head>
     <style>
       body {
         font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
         line-height: 1.6;
         color: #333;
         max-width: 600px;
         margin: 0 auto;
         padding: 20px;
       }
       .container {
         background: #ffffff;
         border-radius: 10px;
         box-shadow: 0 2px 10px rgba(0,0,0,0.1);
         padding: 30px;
       }
       .header {
         text-align: center;
         margin-bottom: 30px;
       }
       .logo {
         font-size: 28px;
         font-weight: bold;
         color: #4F46E5;
       }
       .button {
         display: inline-block;
         padding: 14px 30px;
         background-color: #10B981;
         color: white !important;
         text-decoration: none;
         border-radius: 6px;
         font-weight: 600;
         margin: 20px 0;
       }
       .button:hover {
         background-color: #059669;
       }
       .footer {
         margin-top: 30px;
         padding-top: 20px;
         border-top: 1px solid #e5e5e5;
         text-align: center;
         font-size: 14px;
         color: #666;
       }
       .warning {
         background-color: #FEF3C7;
         border-left: 4px solid #F59E0B;
         padding: 12px;
         margin: 20px 0;
       }
     </style>
   </head>
   <body>
     <div class="container">
       <div class="header">
         <div class="logo">✨ DhafnckMCP</div>
         <h2>Your Magic Login Link</h2>
       </div>
       
       <div class="content">
         <p>Hi there,</p>
         
         <p>Click the button below to instantly sign in to your DhafnckMCP account:</p>
         
         <div style="text-align: center;">
           <a href="{{ .ConfirmationURL }}" class="button">
             Sign In to DhafnckMCP
           </a>
         </div>
         
         <div class="warning">
           <strong>⏰ Time Sensitive:</strong> This magic link expires in 15 minutes.
         </div>
         
         <p>If you didn't request this login link, please ignore this email.</p>
         
         <p>Having trouble? Copy and paste this link:</p>
         <p style="word-break: break-all; color: #10B981;">
           {{ .ConfirmationURL }}
         </p>
       </div>
       
       <div class="footer">
         <p>© 2025 DhafnckMCP. All rights reserved.</p>
         <p>Secure passwordless authentication powered by Supabase.</p>
       </div>
     </div>
   </body>
   </html>
   ```

4. **Save the Template**

## Step 6: Configure Invite User Template

### 6.1 Select "Invite User" Template

1. **Click on "Invite User"** in the template list

2. **Configure Template Settings:**
   ```
   Subject: You've been invited to DhafnckMCP
   ```

3. **Edit Email Body (HTML):**
   ```html
   <!DOCTYPE html>
   <html>
   <head>
     <style>
       body {
         font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
         line-height: 1.6;
         color: #333;
         max-width: 600px;
         margin: 0 auto;
         padding: 20px;
       }
       .container {
         background: #ffffff;
         border-radius: 10px;
         box-shadow: 0 2px 10px rgba(0,0,0,0.1);
         padding: 30px;
       }
       .header {
         text-align: center;
         margin-bottom: 30px;
       }
       .logo {
         font-size: 28px;
         font-weight: bold;
         color: #4F46E5;
       }
       .button {
         display: inline-block;
         padding: 14px 30px;
         background-color: #8B5CF6;
         color: white !important;
         text-decoration: none;
         border-radius: 6px;
         font-weight: 600;
         margin: 20px 0;
       }
       .button:hover {
         background-color: #7C3AED;
       }
       .feature-list {
         background-color: #F9FAFB;
         border-radius: 8px;
         padding: 20px;
         margin: 20px 0;
       }
       .feature-list ul {
         margin: 10px 0;
         padding-left: 20px;
       }
       .feature-list li {
         margin: 8px 0;
       }
       .footer {
         margin-top: 30px;
         padding-top: 20px;
         border-top: 1px solid #e5e5e5;
         text-align: center;
         font-size: 14px;
         color: #666;
       }
     </style>
   </head>
   <body>
     <div class="container">
       <div class="header">
         <div class="logo">🎉 DhafnckMCP</div>
         <h2>Welcome to the Team!</h2>
       </div>
       
       <div class="content">
         <p>Hi there,</p>
         
         <p>You've been invited to join <strong>DhafnckMCP</strong> - the AI Agent Orchestration Platform!</p>
         
         <div class="feature-list">
           <strong>What you can do with DhafnckMCP:</strong>
           <ul>
             <li>🤖 Orchestrate multiple AI agents</li>
             <li>📋 Manage tasks and projects</li>
             <li>🔄 Automate workflows</li>
             <li>📊 Track progress and analytics</li>
             <li>👥 Collaborate with your team</li>
           </ul>
         </div>
         
         <p>Click the button below to accept your invitation and set up your account:</p>
         
         <div style="text-align: center;">
           <a href="{{ .ConfirmationURL }}" class="button">
             Accept Invitation
           </a>
         </div>
         
         <p>If the button doesn't work, copy and paste this link:</p>
         <p style="word-break: break-all; color: #8B5CF6;">
           {{ .ConfirmationURL }}
         </p>
       </div>
       
       <div class="footer">
         <p>© 2025 DhafnckMCP. All rights reserved.</p>
         <p>Questions? Contact your administrator.</p>
       </div>
     </div>
   </body>
   </html>
   ```

4. **Save the Template**

## Step 7: Configure Email Settings

### 7.1 Navigate to Auth Settings
1. Go to **Authentication → Providers**
2. Scroll down to **Email** section

### 7.2 Configure Email Provider Settings

1. **Enable Email Provider**
   - Toggle: **ON** ✅

2. **Configure Settings:**
   ```
   ☑️ Enable email confirmations
   ☑️ Enable secure email change (requires confirmation from both emails)
   ☐ Enable double confirm email changes (optional)
   ```

3. **Set Confirmation Expiry:**
   ```
   Confirmation expiry: 86400 (24 hours in seconds)
   ```

4. **Save Settings**

## Step 8: Configure SMTP (For Production)

### 8.1 Navigate to Project Settings
1. Go to **Settings → Auth**
2. Find **SMTP Settings** section

### 8.2 Configure Custom SMTP (Optional but Recommended)

For production, configure custom SMTP to ensure reliable email delivery:

1. **Enable Custom SMTP:**
   - Toggle: **Enable Custom SMTP** ✅

2. **Enter SMTP Details:**
   ```
   Host: smtp.gmail.com (example)
   Port: 587
   Username: your-email@gmail.com
   Password: your-app-specific-password
   Sender email: noreply@yourdomain.com
   Sender name: DhafnckMCP
   ```

3. **Popular SMTP Providers:**
   - **SendGrid**: smtp.sendgrid.net (Port 587)
   - **Mailgun**: smtp.mailgun.org (Port 587)
   - **AWS SES**: email-smtp.region.amazonaws.com (Port 587)
   - **Gmail**: smtp.gmail.com (Port 587)
   - **Outlook**: smtp-mail.outlook.com (Port 587)

4. **Test SMTP Configuration:**
   - Click **"Send Test Email"**
   - Enter test email address
   - Verify email is received

## Step 9: Configure Site URL and Redirect URLs

### 9.1 Navigate to URL Configuration
1. Go to **Authentication → URL Configuration**

### 9.2 Set Site URL
```
Site URL: http://localhost:3800
```
For production: `https://yourdomain.com`

### 9.3 Add Redirect URLs
Add allowed redirect URLs (one per line):
```
http://localhost:3800/auth/callback
http://localhost:3800/auth/verify
http://localhost:3800/auth/reset-password
http://localhost:3000/auth/callback
http://localhost:3000/auth/verify
http://localhost:3000/auth/reset-password
```

For production, add:
```
https://yourdomain.com/auth/callback
https://yourdomain.com/auth/verify
https://yourdomain.com/auth/reset-password
```

## Step 10: Test Email Templates

### 10.1 Test Email Verification
1. Register a new user via API or frontend
2. Check email inbox for verification email
3. Verify email renders correctly
4. Click verification link and confirm it works

### 10.2 Test Password Reset
1. Request password reset for existing user
2. Check email for reset link
3. Verify email renders correctly
4. Click reset link and confirm it works

### 10.3 Test Magic Link (if enabled)
1. Request magic link login
2. Check email for login link
3. Verify email renders correctly
4. Click link and confirm login works

## Troubleshooting

### Emails Not Sending
1. **Check Supabase Dashboard Logs:**
   - Go to **Logs → Auth Logs**
   - Look for email sending errors

2. **Verify SMTP Settings:**
   - Test SMTP connection
   - Check credentials are correct
   - Ensure firewall allows SMTP port

3. **Check Spam Folder:**
   - Emails might be marked as spam
   - Add sender to whitelist

### Template Variables Not Working
- Ensure you're using correct variables:
  - `{{ .ConfirmationURL }}` - The action URL
  - `{{ .Email }}` - Recipient email
  - `{{ .TokenHash }}` - Token hash (rarely needed)

### Links Not Working
1. Verify redirect URLs are configured
2. Check Site URL is correct
3. Ensure frontend routes exist for callbacks

## Best Practices

1. **Test in Development First:**
   - Use Supabase's default SMTP for development
   - Test all flows before production

2. **Brand Consistency:**
   - Use your brand colors and logo
   - Keep messaging consistent
   - Include company information

3. **Security:**
   - Always use HTTPS URLs in production
   - Set appropriate expiry times
   - Include security notices in emails

4. **User Experience:**
   - Keep emails concise and clear
   - Make CTA buttons prominent
   - Include text-only fallback links
   - Add help/support contact information

5. **Compliance:**
   - Include unsubscribe information where required
   - Add privacy policy links
   - Follow GDPR/CCPA requirements

## Monitoring

### Check Email Metrics
1. Go to **Authentication → Logs**
2. Filter by event type: `user.email.send`
3. Monitor:
   - Email send success rate
   - Bounce rates
   - Verification completion rates

### Set Up Alerts (Optional)
1. Use Supabase webhooks
2. Monitor for:
   - Failed email sends
   - High bounce rates
   - Unusual activity patterns

## Summary

Your email templates are now configured! Users will receive:
- ✅ Professional verification emails on signup
- ✅ Secure password reset emails
- ✅ Optional magic link login emails
- ✅ Team invitation emails

Remember to:
1. Test all email flows thoroughly
2. Configure custom SMTP for production
3. Monitor email delivery metrics
4. Keep templates updated with your branding