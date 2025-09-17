# Email Authentication Service Setup Guide

This guide explains how to set up and use the complete email authentication service for your 4genthub application.

## Overview

The email authentication service provides:
- **User Registration** with email verification
- **Password Reset** with secure tokens
- **Password Change** confirmation emails
- **Welcome Emails** after successful verification
- **HTML Email Templates** with customizable branding
- **Token Management** with expiration and validation
- **SMTP Integration** with your email provider

## Quick Setup

### 1. Environment Configuration

# Frontend URLs for email links
FRONTEND_URL=http://localhost:3800
```

### 2. Install Dependencies

The email service requires Jinja2 for templates:

```bash
# Already included in pyproject.toml
pip install jinja2>=3.1.0
```

### 3. Database Migration

Run the email tokens table migration:

```bash
cd 4genthub_main/src/fastmcp/auth/infrastructure/migrations
python migrator.py
```

Or programmatically:

```python
from fastmcp.auth.infrastructure.migrations.migrator import run_email_migrations
await run_email_migrations()
```

### 4. FastAPI Integration

```python
from fastapi import FastAPI
from fastmcp.auth.integration.email_auth_integration import include_email_auth_routes

app = FastAPI()

# Add email authentication routes
integration = include_email_auth_routes(app)
```

## API Endpoints

The email authentication service provides these enhanced endpoints:

### Enhanced Registration
```http
POST /auth/enhanced/signup
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "securepassword123",
    "username": "johndoe",
    "full_name": "John Doe",
    "send_custom_email": true
}
```

### Password Reset Request
```http
POST /auth/enhanced/password-reset
Content-Type: application/json

{
    "email": "user@example.com",
    "send_custom_email": true
}
```

### Email Verification
```http
POST /auth/enhanced/verify-email
Content-Type: application/json

{
    "token": "verification_token_here",
    "email": "user@example.com"
}
```

### Password Reset with Token
```http
POST /auth/enhanced/reset-password
Content-Type: application/json

{
    "token": "reset_token_here",
    "email": "user@example.com",
    "new_password": "newpassword123"
}
```

### Resend Verification
```http
POST /auth/enhanced/resend-verification
Content-Type: application/json

{
    "email": "user@example.com"
}
```

## Email Templates

### Default Templates

The service includes these HTML email templates:

1. **verification.html** - Email verification
2. **password_reset.html** - Password reset
3. **password_changed.html** - Password change confirmation
4. **welcome.html** - Welcome after verification
5. **base.html** - Base template with styling

### Template Customization

Templates are stored in `templates/email/` and can be customized:

```python
from fastmcp.auth.infrastructure.email_service import EmailTemplateEngine

engine = EmailTemplateEngine("path/to/custom/templates")
html = engine.render_template("verification.html", 
    user_name="John Doe",
    verification_url="https://example.com/verify?token=abc123"
)
```

### Template Variables

Common variables available in templates:

- `user_name` - User's display name
- `company_name` - Organization name (from SMTP_FROM_NAME)
- `current_year` - Current year
- `verification_url` - Email verification link
- `reset_url` - Password reset link
- `dashboard_url` - Dashboard/app URL

## Usage Examples

### Basic Email Service Usage

```python
from fastmcp.auth.infrastructure.email_service import get_email_service

# Get service instance
email_service = get_email_service()

# Test SMTP connection
result = await email_service.test_connection()
print(f"Connection: {result.success}")

# Send verification email
result = await email_service.send_verification_email(
    email="user@example.com",
    user_name="John Doe"
)
print(f"Email sent: {result.success}")
```

### Enhanced Authentication Service

```python
from fastmcp.auth.infrastructure.enhanced_auth_service import get_enhanced_auth_service

auth_service = get_enhanced_auth_service()

# Register user with custom email
result = await auth_service.register_user(
    email="user@example.com",
    password="password123",
    metadata={"username": "johndoe", "full_name": "John Doe"},
    send_custom_email=True
)

print(f"Registration: {result.success}")
print(f"Email sent: {result.email_sent}")
```

### Token Management

```python
from fastmcp.auth.infrastructure.repositories.email_token_repository import get_email_token_repository

token_repo = get_email_token_repository()

# Get token statistics
stats = token_repo.get_token_stats()
print(f"Total tokens: {stats['total_tokens']}")
print(f"Used tokens: {stats['used_tokens']}")

# Cleanup expired tokens
deleted = token_repo.cleanup_expired_tokens(older_than_days=7)
print(f"Cleaned up {deleted} tokens")
```

## Testing

### Unit Tests

Run the email service tests:

```bash
cd 4genthub_main
python -m pytest src/tests/auth/test_email_service_integration.py -v
```

### Manual Testing

Test SMTP connection:

```bash
curl http://localhost:8000/auth/enhanced/test-email
```

Check service health:

```bash
curl http://localhost:8000/auth/enhanced/health
```

Get email statistics:

```bash
curl http://localhost:8000/auth/enhanced/email-stats
```

## Email Workflows

### User Registration Flow

1. User submits registration form
2. System creates Supabase user account
3. System generates verification token
4. System sends custom HTML verification email
5. User clicks verification link
6. System validates token and marks email as verified
7. System sends welcome email

### Password Reset Flow

1. User requests password reset
2. System generates reset token (1-hour expiry)
3. System sends password reset email
4. User clicks reset link
5. User enters new password
6. System validates token and updates password
7. System sends password change confirmation email

### Security Features

- **Secure tokens** using cryptographically secure random generation
- **Token expiration** (24 hours for verification, 1 hour for password reset)
- **One-time use** tokens are invalidated after use
- **Email validation** prevents token replay attacks
- **Rate limiting** protection against spam
- **SSL/TLS support** for secure SMTP connections

## Cloud Integration

The service works with cloud authentication providers through standard protocols.

## Troubleshooting

### Common Issues

**SMTP Connection Failed**
- Check SMTP credentials and firewall settings
- Verify TLS/SSL configuration
- Test with `curl telnet smtp.host.com 587`

**Templates Not Found**
- Ensure templates directory exists
- Check template file permissions
- Verify Jinja2 template syntax

**Token Validation Failed**
- Check token expiration
- Verify email matches exactly
- Ensure token hasn't been used

**Database Migration Failed**
- Check database connection
- Verify table creation permissions
- Check for existing table conflicts

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("fastmcp.auth").setLevel(logging.DEBUG)
```

### Health Check

Monitor service health:

```python
from fastmcp.auth.integration.email_auth_integration import get_email_auth_integration

integration = get_email_auth_integration()
health = await integration.health_check()
print(health)
```

## Production Considerations

### Security
- Use strong SMTP passwords
- Enable SSL/TLS for SMTP connections
- Set appropriate token expiration times
- Monitor for suspicious activity

### Performance
- Use connection pooling for database
- Implement rate limiting
- Cache email templates
- Monitor email queue length

### Monitoring
- Log all email operations
- Track delivery success rates
- Monitor token usage patterns
- Alert on authentication failures

### Backup
- Backup email token database
- Store email templates in version control
- Document SMTP configuration

## Integration with Frontend

### React Example

```typescript
// Registration
const response = await fetch('/auth/enhanced/signup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
    username: 'johndoe',
    send_custom_email: true
  })
});

const result = await response.json();
if (result.email_sent) {
  showMessage('Please check your email to verify your account');
}
```

### Email Verification Handling

```typescript
// Handle verification link click
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');
const email = urlParams.get('email');

if (token && email) {
  const response = await fetch('/auth/enhanced/verify-email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, email })
  });
  
  const result = await response.json();
  if (result.success) {
    showMessage('Email verified successfully! Welcome!');
    redirectToLogin();
  }
}
```

This completes the email authentication service setup. The system provides a robust, secure, and scalable solution for authentication workflows with professional HTML email templates and comprehensive token management.