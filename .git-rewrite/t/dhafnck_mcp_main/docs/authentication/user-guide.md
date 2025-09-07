# Authentication User Guide

## Overview

This guide explains how to use the DhafnckMCP authentication system as an end user. The system provides secure email/password authentication with JWT tokens, email verification, password reset, and account security features.

## Getting Started

### Account Registration

1. **Navigate to the registration page**
   - Go to `/signup` in your application
   - Or click the "Sign Up" link from the login page

2. **Fill out the registration form**
   - **Email**: Must be a valid email address
   - **Username**: Choose a unique username (3-30 characters)
   - **Password**: Must meet security requirements (see below)

3. **Submit the form**
   - Click "Create Account" to submit
   - You'll see a success message and be redirected to login

4. **Verify your email**
   - Check your email for a verification link
   - Click the link to activate your account
   - You can now log in with your credentials

### Password Requirements

Your password must include:
- At least 8 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)
- At least one special character (!@#$%^&*)

**Examples of strong passwords:**
- `MySecure123!`
- `Coffee&Code2024`
- `Adventure#2024`

### Logging In

1. **Navigate to the login page**
   - Go to `/login` in your application
   - Or you'll be redirected here when accessing protected pages

2. **Enter your credentials**
   - **Email**: The email you registered with
   - **Password**: Your account password

3. **Optional: Remember Me**
   - Check "Remember Me" to stay logged in longer
   - Your session will persist across browser restarts

4. **Click "Sign In"**
   - You'll be redirected to the main application
   - A welcome message may appear

## Managing Your Account

### Password Reset

If you forget your password:

1. **Go to the login page**
2. **Click "Forgot Password?"**
3. **Enter your email address**
4. **Check your email for reset instructions**
5. **Click the reset link in the email**
6. **Enter your new password twice**
7. **Click "Reset Password"**
8. **Log in with your new password**

**Note:** Password reset links expire after 1 hour for security.

### Email Verification

If you haven't verified your email:

1. **Try to log in** - you'll see a verification required message
2. **Click "Resend Verification Email"**
3. **Check your email** (including spam folder)
4. **Click the verification link**
5. **You can now log in normally**

**Note:** Verification links expire after 24 hours.

### Account Security

#### Session Management

- **Automatic logout**: Sessions expire after 15 minutes of inactivity
- **Token refresh**: Your session automatically extends when you're active
- **Manual logout**: Always log out when using shared computers

#### Account Lockout

For security, your account will be temporarily locked if:
- 5 consecutive failed login attempts occur
- Suspicious activity is detected

**If locked:**
- Wait 30 minutes before trying again
- Or contact support for immediate assistance
- Use password reset if you think your password was compromised

#### Multi-Device Access

- You can be logged in on multiple devices
- Each device gets its own session
- Logging out from one device doesn't affect others
- Use "Log out from all devices" for complete security

## Troubleshooting

### Common Login Issues

#### "Invalid credentials" Error
- **Check your email**: Make sure it's exactly as registered
- **Check your password**: Passwords are case-sensitive
- **Check Caps Lock**: Ensure it's not accidentally enabled
- **Try password reset**: If you're unsure of your password

#### "Email not verified" Error
- **Check your email**: Look for the verification message
- **Check spam folder**: Verification emails might be filtered
- **Resend verification**: Click the resend link on the login page
- **Contact support**: If you're not receiving emails

#### "Account locked" Error
- **Wait 30 minutes**: Locks are temporary for security
- **Reset password**: If you think your account is compromised
- **Contact support**: For immediate assistance

#### "Session expired" Error
- **Log in again**: Your session has timed out
- **Check "Remember Me"**: To stay logged in longer
- **Clear browser cache**: If problems persist

### Browser Issues

#### Cookies Disabled
- **Enable cookies**: Required for authentication
- **Check privacy settings**: Ensure cookies are allowed
- **Try incognito mode**: To test without extensions

#### JavaScript Disabled
- **Enable JavaScript**: Required for the authentication interface
- **Check browser settings**: Ensure JavaScript is allowed
- **Update your browser**: Use a modern, supported browser

#### Browser Compatibility
**Supported browsers:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Network Issues

#### Connection Problems
- **Check internet connection**: Ensure you're online
- **Try another network**: To rule out network issues
- **Check firewall**: Ensure authentication endpoints aren't blocked

#### Slow Loading
- **Check connection speed**: Slow connections may timeout
- **Clear browser cache**: Old cached files may cause issues
- **Disable browser extensions**: Some extensions may interfere

## Security Best Practices

### Password Security

1. **Use unique passwords**: Don't reuse passwords from other sites
2. **Use a password manager**: To generate and store strong passwords
3. **Enable two-factor authentication**: When available
4. **Change passwords regularly**: Especially if compromised

### Account Safety

1. **Log out on shared computers**: Always log out completely
2. **Keep email secure**: Your email is the key to your account
3. **Monitor account activity**: Report suspicious activity
4. **Use secure networks**: Avoid public Wi-Fi for sensitive actions

### Recognizing Phishing

**Legitimate emails will:**
- Come from your application's domain
- Never ask for your password in the email
- Include your username or partial email
- Have a professional appearance

**Be suspicious of:**
- Emails asking for immediate action
- Misspelled domain names
- Requests for password or personal information
- Poor grammar or formatting

## Mobile Usage

### Mobile Browser

The authentication system works on mobile browsers:
- Use landscape mode for better form visibility
- Enable password managers for easier login
- Bookmark the login page for quick access

### Mobile Apps

If using a mobile app:
- Keep the app updated for security patches
- Use biometric login when available
- Log out if you lose your device

## Accessibility

### Screen Readers

The authentication interface supports screen readers:
- Form labels are properly associated
- Error messages are announced
- Navigation is keyboard-friendly

### Keyboard Navigation

- **Tab**: Move between form fields
- **Enter**: Submit forms
- **Escape**: Close modal dialogs
- **Space**: Toggle checkboxes

### High Contrast Mode

- The interface adapts to high contrast settings
- Text remains readable in all modes
- Focus indicators are clearly visible

## Getting Help

### Self-Service Options

1. **Check this user guide**: Most questions are answered here
2. **Try the troubleshooting steps**: Common issues and solutions
3. **Use password reset**: For password-related issues
4. **Clear browser data**: Often resolves technical issues

### Contact Support

If you need additional help:

- **Email**: support@dhafnck-mcp.com
- **Subject line**: Include "Authentication Help"
- **Include details**: 
  - Your email address (but not password)
  - What you were trying to do
  - Error messages you received
  - Your browser and operating system

**Response times:**
- General questions: 24-48 hours
- Account lockouts: 4-8 hours
- Security issues: Immediate

### Emergency Access

If you're completely locked out:
- Email support with "URGENT: Account Lockout"
- Include your registered email address
- Explain the situation briefly
- Support will verify your identity and assist

## Privacy and Data

### What We Store

- Your email address (for login and communication)
- Your username (for display purposes)
- Encrypted password (we never see your actual password)
- Login history (for security monitoring)
- Account preferences and settings

### What We Don't Store

- Your actual password (only an encrypted version)
- Sensitive personal information
- Payment information (if applicable, handled separately)
- Browsing history outside our application

### Data Protection

- All data is encrypted in transit and at rest
- We follow industry security standards
- Regular security audits are performed
- Data is backed up securely

### Account Deletion

To delete your account:
1. Contact support with your request
2. Verify your identity
3. Confirm you want to delete all data
4. Account and data will be permanently removed within 30 days

## Frequently Asked Questions

### Account Management

**Q: Can I change my email address?**
A: Contact support to change your email address. You'll need to verify both the old and new addresses.

**Q: Can I change my username?**
A: Username changes may be available. Contact support with your request.

**Q: How long do sessions last?**
A: Sessions last 15 minutes without activity, but automatically refresh when you're active.

### Security

**Q: How secure is my password?**
A: Passwords are encrypted using industry-standard bcrypt hashing. We never store your actual password.

**Q: Can I use social login (Google, Facebook, etc.)?**
A: Currently, only email/password authentication is supported. Social login may be added in the future.

**Q: Is two-factor authentication available?**
A: Two-factor authentication is not currently available but is planned for a future release.

### Technical

**Q: Why am I getting logged out frequently?**
A: This could be due to browser settings, network issues, or security policies. Contact support if it's excessive.

**Q: Can I use the same account on multiple devices?**
A: Yes, you can log in from multiple devices simultaneously. Each device maintains its own session.

**Q: What happens if I clear my browser data?**
A: You'll be logged out and need to log in again. Your account data is safely stored on our servers.

---

*Last updated: August 17, 2025*

For technical documentation, see the [API Reference](./api-reference.md).
For integration help, see the [Developer Guide](./developer-guide.md).