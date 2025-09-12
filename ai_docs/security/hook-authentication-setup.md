# Hook Authentication Setup Guide

## Security Best Practices

### Environment Variables Configuration

The hook authentication system requires the following environment variables to be set in your `.env` file:

```bash
# Hook Authentication Configuration
HOOK_JWT_SECRET=<your-secure-secret-here>  # REQUIRED - Generate a strong secret key
HOOK_JWT_ALGORITHM=HS256                   # JWT signing algorithm (default: HS256)
```

### Important Security Notes

1. **Never hardcode secrets** in your source code
2. **Always use environment variables** for sensitive configuration
3. **Generate strong secrets** using a secure random generator
4. **Keep `.env` files** out of version control (add to `.gitignore`)
5. **Use `.env.sample`** or `.env.example` files to document required variables without exposing actual values

### Generating a Secure Secret

You can generate a secure secret using Python:

```python
import secrets
print(secrets.token_urlsafe(32))
```

Or using OpenSSL:

```bash
openssl rand -base64 32
```

### Configuration Files

- **`.env`** - Contains actual secrets (never commit to repository)
- **`.env.dev`** - Development environment secrets (local only)
- **`.env.sample`** - Template showing required variables without values
- **`hook_auth.py`** - Reads secrets from environment variables only

### Error Handling

If the `HOOK_JWT_SECRET` is not set, the system will raise an error:
```
ValueError: HOOK_JWT_SECRET environment variable is required for hook authentication
```

This ensures the system cannot run with hardcoded or default secrets, enforcing security best practices.

## Implementation Details

The hook authentication system (`src/fastmcp/auth/hook_auth.py`) now:

1. Reads configuration from environment variables only
2. Raises an error if required secrets are not configured
3. Uses the JWT secret to sign and validate tokens
4. Supports configurable JWT algorithms (default: HS256)

## Testing

When running tests, ensure environment variables are set:

```bash
# Set environment variables before running tests
export HOOK_JWT_SECRET="your-test-secret"
export HOOK_JWT_ALGORITHM="HS256"
python3 src/tests/test_hook_auth.py
```

Or use a `.env` file with your test configuration.