# Authentication API Reference

## Overview

The DhafnckMCP Authentication API provides secure user authentication and authorization using JWT tokens. This API supports user registration, login, token refresh, password reset, and email verification.

## Base URL

```
http://localhost:8000/api/auth
```

## Authentication

Most endpoints require authentication using a Bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Endpoints

### 1. User Registration

**POST** `/register`

Register a new user account.

#### Request Body

```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecurePassword123!"
}
```

#### Response

**201 Created**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "johndoe",
  "status": "pending_verification",
  "created_at": "2025-08-17T12:00:00Z"
}
```

**400 Bad Request**
```json
{
  "detail": "Email already registered"
}
```

### 2. User Login

**POST** `/login`

Authenticate user and receive access tokens.

#### Request Body

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

#### Response

**200 OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**401 Unauthorized**
```json
{
  "detail": "Invalid credentials"
}
```

**403 Forbidden**
```json
{
  "detail": "Email not verified"
}
```

### 3. Token Refresh

**POST** `/refresh`

Refresh access token using refresh token.

#### Request Body

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### Response

**200 OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**401 Unauthorized**
```json
{
  "detail": "Invalid refresh token"
}
```

### 4. Get Current User

**GET** `/me`

Get authenticated user information.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Response

**200 OK**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "johndoe",
  "roles": ["user"],
  "status": "active",
  "created_at": "2025-08-17T12:00:00Z",
  "verified_at": "2025-08-17T12:05:00Z"
}
```

**401 Unauthorized**
```json
{
  "detail": "Not authenticated"
}
```

### 5. Request Password Reset

**POST** `/password-reset/request`

Request password reset email.

#### Request Body

```json
{
  "email": "user@example.com"
}
```

#### Response

**200 OK**
```json
{
  "message": "Password reset email sent if email exists"
}
```

### 6. Confirm Password Reset

**POST** `/password-reset/confirm`

Reset password using reset token.

#### Request Body

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "new_password": "NewSecurePassword123!"
}
```

#### Response

**200 OK**
```json
{
  "message": "Password reset successful"
}
```

**400 Bad Request**
```json
{
  "detail": "Invalid or expired reset token"
}
```

### 7. Verify Email

**POST** `/verify-email`

Verify email address using verification token.

#### Request Body

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### Response

**200 OK**
```json
{
  "message": "Email verified successfully"
}
```

**400 Bad Request**
```json
{
  "detail": "Invalid or expired verification token"
}
```

### 8. Resend Verification Email

**POST** `/verify-email/resend`

Resend email verification link.

#### Request Body

```json
{
  "email": "user@example.com"
}
```

#### Response

**200 OK**
```json
{
  "message": "Verification email sent if account exists"
}
```

### 9. Logout

**POST** `/logout`

Logout user and invalidate tokens.

#### Headers

```
Authorization: Bearer <access_token>
```

#### Request Body

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### Response

**200 OK**
```json
{
  "message": "Logged out successfully"
}
```

## Token Management

### Access Token

- **Purpose**: Short-lived token for API authentication
- **Expiration**: 15 minutes
- **Usage**: Include in Authorization header for protected endpoints
- **Format**: JWT with user claims

#### Token Payload Example

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "roles": ["user"],
  "type": "access",
  "exp": 1692280800,
  "iat": 1692279900,
  "iss": "dhafnck-mcp"
}
```

### Refresh Token

- **Purpose**: Long-lived token for obtaining new access tokens
- **Expiration**: 30 days
- **Usage**: Send to `/refresh` endpoint
- **Security**: Rotated on each use (token family tracking)

## Error Responses

All error responses follow a consistent format:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2025-08-17T12:00:00Z"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `INVALID_CREDENTIALS` | Email or password incorrect |
| `EMAIL_NOT_VERIFIED` | Account email not verified |
| `ACCOUNT_LOCKED` | Account locked due to security |
| `TOKEN_EXPIRED` | JWT token has expired |
| `TOKEN_INVALID` | JWT token is malformed |
| `USER_NOT_FOUND` | User does not exist |
| `EMAIL_ALREADY_EXISTS` | Email already registered |
| `WEAK_PASSWORD` | Password doesn't meet requirements |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Registration**: 5 requests per hour per IP
- **Login**: 10 requests per hour per email
- **Password Reset**: 3 requests per hour per email
- **Token Refresh**: 30 requests per hour per user
- **Other endpoints**: 100 requests per minute per user

## Security Best Practices

1. **Always use HTTPS** in production
2. **Store tokens securely** (HttpOnly cookies recommended)
3. **Implement token refresh** before expiration
4. **Handle token expiration** gracefully in client
5. **Never log or expose** sensitive tokens
6. **Validate email addresses** before account activation
7. **Implement account lockout** after failed attempts
8. **Use strong passwords** (minimum 8 characters)

## Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

## Account Security Features

- **Email Verification**: Required before first login
- **Account Lockout**: After 5 failed login attempts
- **Password History**: Prevents reusing last 5 passwords
- **Session Management**: Multiple device support
- **Token Rotation**: Refresh tokens rotated on use
- **Rate Limiting**: Prevents brute force attacks

## Integration Examples

### JavaScript/TypeScript

```typescript
// Login
const response = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePassword123!'
  })
});

const { access_token, refresh_token } = await response.json();

// Store tokens securely
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);

// Make authenticated request
const userResponse = await fetch('http://localhost:8000/api/auth/me', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const user = await userResponse.json();
```

### Python

```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/login', json={
    'email': 'user@example.com',
    'password': 'SecurePassword123!'
})

tokens = response.json()
access_token = tokens['access_token']

# Make authenticated request
user_response = requests.get(
    'http://localhost:8000/api/auth/me',
    headers={'Authorization': f'Bearer {access_token}'}
)

user = user_response.json()
```

## Webhook Events

The authentication system can trigger webhooks for the following events:

- `user.registered` - New user registration
- `user.verified` - Email verification completed
- `user.login` - Successful login
- `user.locked` - Account locked
- `user.password_reset` - Password reset completed

## Support

For issues or questions, please contact:
- Email: support@dhafnck-mcp.com
- Documentation: https://docs.dhafnck-mcp.com
- GitHub: https://github.com/dhafnck/mcp-auth