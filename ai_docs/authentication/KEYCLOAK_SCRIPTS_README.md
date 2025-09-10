# Keycloak Configuration Scripts - Security Guide

## ⚠️ IMPORTANT SECURITY NOTICE

These scripts have been updated to **NEVER store passwords in code**. All sensitive credentials must be provided via:
1. Command-line arguments
2. Environment variables
3. Secure configuration files (never committed to git)

## 📋 Available Scripts

### 1. `fix_keycloak_complete.sh`
Complete Keycloak configuration for EMAIL_VERIFIED_AUTO feature.

**Usage:**
```bash
# Via command-line argument
./fix_keycloak_complete.sh "your_admin_password"

# Via environment variable
export KEYCLOAK_ADMIN_PASSWORD="your_admin_password"
./fix_keycloak_complete.sh
```

### 2. `fix_user_account.sh`
Fix specific user account issues in Keycloak.

**Usage:**
```bash
# Via command-line arguments
./fix_user_account.sh "admin_password" "user@email.com"

# Via environment variables
export KEYCLOAK_ADMIN_PASSWORD="your_admin_password"
export USER_EMAIL="user@email.com"
./fix_user_account.sh
```

### 3. `disable_all_required_actions.sh`
Disable all required actions that might block login.

**Usage:**
```bash
# Via command-line argument
./disable_all_required_actions.sh "your_admin_password"

# Via environment variable
export KEYCLOAK_ADMIN_PASSWORD="your_admin_password"
./disable_all_required_actions.sh
```

### 4. `fix_client_permissions.sh`
Fix client permissions for user management.

**Usage:**
```bash
# Via command-line argument
./fix_client_permissions.sh "your_admin_password"

# Via environment variable
export KEYCLOAK_ADMIN_PASSWORD="your_admin_password"
./fix_client_permissions.sh
```

### 5. `check_keycloak_config.sh`
Check current Keycloak configuration and suggest fixes.

**Usage:**
```bash
# Check configuration only
./check_keycloak_config.sh "your_admin_password"

# Check and apply fixes
./check_keycloak_config.sh "your_admin_password" --apply-fixes
```

## 🔐 Secure Configuration

### Method 1: Environment File (Recommended)

1. Copy the example file:
```bash
cp .env.keycloak.example .env.keycloak
```

2. Edit `.env.keycloak` with your actual values:
```bash
# NEVER commit this file to git!
KEYCLOAK_ADMIN_PASSWORD=your_actual_password
KEYCLOAK_CLIENT_SECRET=your_actual_secret
```

3. Source the file before running scripts:
```bash
source .env.keycloak
./fix_keycloak_complete.sh
```

### Method 2: Direct Environment Variables

```bash
export KEYCLOAK_ADMIN_PASSWORD="your_password"
export KEYCLOAK_URL="https://keycloak.92.5.226.7.nip.io"
export KEYCLOAK_REALM="mcp"
export KEYCLOAK_CLIENT_ID="mcp-api"

./fix_keycloak_complete.sh
```

### Method 3: Command-Line Arguments

```bash
# Most direct but visible in process list
./fix_keycloak_complete.sh "your_admin_password"
```

## 🚨 Security Best Practices

1. **NEVER hardcode passwords in scripts**
2. **NEVER commit `.env.keycloak` or any file with real passwords**
3. **Always use `.gitignore` to exclude sensitive files**
4. **Clear shell history after using passwords in commands:**
   ```bash
   history -c
   ```
5. **Use environment variables in CI/CD pipelines**
6. **Rotate passwords regularly**
7. **Use strong, unique passwords**

## 📝 Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `KEYCLOAK_ADMIN_USER` | Admin username | `admin` |
| `KEYCLOAK_ADMIN_PASSWORD` | Admin password | *(required)* |
| `KEYCLOAK_URL` | Keycloak server URL | `https://keycloak.92.5.226.7.nip.io` |
| `KEYCLOAK_REALM` | Realm name | `mcp` |
| `KEYCLOAK_CLIENT_ID` | Client ID | `mcp-api` |
| `KEYCLOAK_CLIENT_SECRET` | Client secret | *(required for some operations)* |
| `EMAIL_VERIFIED_AUTO` | Auto-verify emails | `true` |

## 🧹 Cache Cleaning

To clean all cache files that might contain sensitive data:

```bash
# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete

# Clean pytest cache
rm -rf .pytest_cache

# Clear shell history
history -c
```

## 📌 Git Safety Checklist

Before pushing to GitHub:

- [ ] No hardcoded passwords in any script
- [ ] `.env.keycloak` is in `.gitignore`
- [ ] Only `.env.keycloak.example` with placeholder values exists
- [ ] Cache directories are cleaned
- [ ] Shell history is cleared
- [ ] No sensitive data in commit messages

## 🔄 Migration from Old Scripts

If you have old scripts with hardcoded passwords:

1. Pull the latest changes
2. Create your `.env.keycloak` file with actual values
3. Delete any local scripts with hardcoded passwords
4. Use the new secure scripts with environment variables

## ❓ Troubleshooting

**Error: "Admin password required!"**
- Provide password via argument or environment variable

**Error: "Failed to authenticate as admin"**
- Check your admin password is correct
- Verify Keycloak is running and accessible

**Scripts not working after update?**
- Make sure you're providing credentials (no longer hardcoded)
- Check `.env.keycloak.example` for required variables