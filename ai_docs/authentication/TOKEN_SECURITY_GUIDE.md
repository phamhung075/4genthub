# Token Security Management Guide

## 🚨 Security Alert Response

**Date**: 2025-09-02  
**Issue**: GitGuardian detected exposed high entropy secrets in repository  
**Status**: RESOLVED ✅  

### Exposed Tokens (Now Invalidated)

The following tokens were found hardcoded in configuration files and have been removed:

1. **AGENTHUB_TOKEN**: `vzsRAvDwKbjIOmTvCaJMS5G7FBr4mH59` (in `mcp.json`)
2. **API Token**: JWT token in `mcp-config-fix.json`

### Remediation Actions Taken

- ✅ Removed hardcoded tokens from configuration files
- ✅ Replaced with environment variable placeholders
- ✅ Updated `.gitignore` to prevent future exposure
- ✅ Generated new secure replacement tokens
- ✅ Created token generation utility

## 🔐 Secure Token Management

### Environment Variables Setup

Add these variables to your `.env` file:

```bash
# agenthub Tokens (generate new ones for production)
AGENTHUB_TOKEN=your-secure-agenthub-token-here
AGENTHUB_API_TOKEN=your-secure-api-token-here
JWT_SECRET_KEY=your-secure-jwt-secret-here

# Keycloak Configuration
KEYCLOAK_SERVER_URL=your-keycloak-url
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=your-client-id
KEYCLOAK_CLIENT_SECRET=your-client-secret

# Supabase Configuration (if used)
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key
```

### Token Generation

Use the provided generator script:

```bash
python3 generate-secure-tokens.py
```

This generates cryptographically secure tokens:
- **AGENTHUB_TOKEN**: 32-character alphanumeric token
- **API_TOKEN**: 32-character API token  
- **JWT_SECRET**: 64-byte base64-encoded secret

### Configuration Files

**✅ Correct - Using Environment Variables:**

```json
{
  "mcpServers": {
    "agenthub": {
      "env": {
        "AGENTHUB_TOKEN": "${AGENTHUB_TOKEN}"
      }
    }
  }
}
```

**❌ NEVER DO - Hardcoded Tokens:**

```json
{
  "mcpServers": {
    "agenthub": {
      "env": {
        "AGENTHUB_TOKEN": "vzsRAvDwKbjIOmTvCaJMS5G7FBr4mH59"
      }
    }
  }
}
```

## 🛡️ Security Best Practices

### Token Storage

1. **Use Environment Variables**: Never hardcode tokens in source code
2. **Use Secret Managers**: For production, use AWS Secrets Manager, Azure Key Vault, etc.
3. **Local Development**: Use `.env` files (excluded from git)
4. **Docker**: Use Docker secrets or environment variables

### Token Rotation

1. **Regular Rotation**: Rotate tokens every 90 days
2. **Compromise Response**: Immediate rotation if exposure suspected
3. **Documentation**: Keep track of token creation dates
4. **Automation**: Automate token rotation where possible

### Access Control

1. **Principle of Least Privilege**: Tokens should have minimal required permissions
2. **Scoped Tokens**: Use different tokens for different services
3. **Time-Limited**: Use tokens with expiration when possible
4. **Audit Logs**: Monitor token usage

## 🔍 Detection and Monitoring

### Git Hooks

Set up pre-commit hooks to scan for secrets:

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -E '\.(json|js|ts|py)$' | xargs grep -l '[A-Za-z0-9]{32,}'; then
    echo "❌ Potential secret detected!"
    exit 1
fi
```

### GitGuardian Integration

- Monitor repository for secret exposure
- Set up alerts for new secrets
- Review and remediate findings promptly

### Regular Audits

1. **Monthly**: Review all configuration files for hardcoded secrets
2. **Quarterly**: Rotate all tokens and secrets
3. **Annual**: Full security audit of token management practices

## 🚨 Incident Response

### If Tokens Are Exposed

1. **Immediate Actions**:
   - Revoke exposed tokens immediately
   - Generate new tokens using secure methods
   - Update all systems using the tokens
   - Remove tokens from version control history if needed

2. **Investigation**:
   - Identify how tokens were exposed
   - Review access logs for unauthorized usage
   - Assess potential impact and data exposure

3. **Prevention**:
   - Update processes to prevent recurrence
   - Improve automation and detection
   - Train team on secure practices

### Emergency Contacts

- **Security Team**: security@yourdomain.com
- **DevOps Lead**: devops@yourdomain.com
- **Project Lead**: lead@yourdomain.com

## 📚 Resources

### Tools

- [Git-secrets](https://github.com/awslabs/git-secrets)
- [GitGuardian](https://gitguardian.com/)
- [TruffleHog](https://github.com/trufflesecurity/trufflehog)
- [detect-secrets](https://github.com/Yelp/detect-secrets)

### Documentation

- [OWASP Secret Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [GitHub Security Best Practices](https://ai_docs.github.com/en/code-security)

---

**Last Updated**: 2025-09-02  
**Next Review**: 2025-12-02  
**Owner**: Security Team