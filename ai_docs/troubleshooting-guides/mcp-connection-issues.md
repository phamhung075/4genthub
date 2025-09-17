# MCP Connection Troubleshooting Guide

## Common Connection Issues and Solutions

### Issue 1: "Failed to reconnect to 4genthub_http"

#### Symptoms
- Claude Code shows connection error
- `/mcp` command fails
- Tools not available in Claude

#### Diagnosis Steps
1. Check Docker container status:
   ```bash
   docker ps | grep 4genthub
   ```

2. Verify server health:
   ```bash
   curl http://localhost:8000/health
   ```

3. Test MCP endpoint:
   ```bash
   curl -X POST http://localhost:8000/mcp/ \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <YOUR_TOKEN>" \
     -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
   ```

#### Solutions

##### Solution A: Fix MCP Configuration
1. Open `.mcp.json` in your project root
2. Ensure URL points to `/mcp/` (with trailing slash):
   ```json
   "url": "http://localhost:8000/mcp/"
   ```
3. Verify token is valid and not expired

##### Solution B: Generate New Token
```python
# Quick token generation script
import jwt
from datetime import datetime, timedelta

secret = 'dGhpcyBpcyBhIGR1bW15IGp3dCBzZWNyZXQgZm9yIGRldmVsb3BtZW50'
payload = {
    'sub': 'test-user',
    'user_id': 'test-user',
    'type': 'access',
    'scopes': ['execute:mcp'],
    'exp': datetime.utcnow() + timedelta(days=30),
    'iat': datetime.utcnow()
}

token = jwt.encode(payload, secret, algorithm='HS256')
print(f'New token: {token}')
```

##### Solution C: Restart Docker Container
```bash
cd /path/to/4genthub_main
docker-compose restart
```

---

### Issue 2: "invalid_token" Authentication Error

#### Symptoms
- Server responds with 401 Unauthorized
- Error message: "Authentication required"
- Token validation fails

#### Root Causes
1. ✅ **RESOLVED** - **Token type mismatch**: Frontend generates `api_token`, backend expects `access` - Fixed in authentication refactor
2. ✅ **RESOLVED** - **User ID field mismatch**: Token has `user_id`, backend checks `sub` - Unified authentication implemented
3. **JWT secret mismatch**: Token signed with different secret
4. **Token expired**: Check `exp` field in token

#### Solutions

##### Check Token Content
```bash
# Decode token to inspect claims
echo 'YOUR_TOKEN' | cut -d. -f2 | base64 -d | python -m json.tool
```

##### Verify JWT Secret
```bash
# Check Docker container secret
docker exec 4genthub-server env | grep JWT_SECRET

# Should match .env file
cat .env | grep JWT_SECRET_KEY
```

##### ✅ Token Compatibility Status - SECURED
✅ **AUTHENTICATION SECURED**: As of 2025-08-25, all authentication bypass mechanisms have been removed. Proper authentication is now enforced with:
- Strict JWT validation with no fallback to default users
- Unified user ID handling across all system components
- No compatibility modes that compromise security

---

### Issue 3: Node.js Client 404 on /register

#### Symptoms
- Node.js MCP client gets 404
- Logs show: "POST /register 404"
- Client expects registration endpoint

#### Root Cause
Some MCP clients expect a `/register` endpoint instead of direct MCP protocol

#### Solution
The server now provides proper `/register` endpoint that returns:
```json
{
  "success": true,
  "session_id": "uuid",
  "server": {...},
  "endpoints": {...},
  "authentication": {...}
}
```

---

### Issue 4: MCP Bridge Connection Failed

#### Symptoms
- Bridge script fails to connect
- Error: "Connection refused"
- `/tmp/mcp_bridge.log` shows errors

#### Diagnosis
```bash
# Check bridge log
tail -f /tmp/mcp_bridge.log

# Test bridge manually
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}' | python3 src/mcp_bridge.py
```

#### Solutions

1. **Ensure server is running**:
   ```bash
   docker ps | grep 4genthub-server
   ```

2. **Check port availability**:
   ```bash
   ss -tuln | grep 8000
   ```

3. **Restart bridge with correct path**:
   ```bash
   cd /path/to/4genthub_main
   python3 src/mcp_bridge.py
   ```

---

### Issue 5: CORS Errors in Browser

#### Symptoms
- Browser console shows CORS errors
- Preflight requests fail
- Cross-origin requests blocked

#### Solution
The registration endpoint now includes proper CORS headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Methods: GET, POST, OPTIONS
```

---

## Quick Diagnostic Commands

### 1. Full System Check
```bash
# Check all components
echo "=== Docker Status ==="
docker ps | grep 4genthub

echo "=== Server Health ==="
curl -s http://localhost:8000/health | python -m json.tool

echo "=== MCP Config ==="
cat .mcp.json | grep -A5 4genthub_http

echo "=== Recent Logs ==="
docker logs 4genthub-server --tail 10
```

### 2. Token Validation
```bash
# Test token directly
TOKEN="your-token-here"
curl -X POST http://localhost:8000/mcp/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' \
  | python -m json.tool | head -20
```

### 3. Registration Test
```bash
# Test registration endpoint
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"client_info":{"name":"test","version":"1.0"}}' \
  | python -m json.tool
```

---

## Environment Variables

### Required for Authentication
```bash
# .env file
JWT_SECRET_KEY=dGhpcyBpcyBhIGR1bW15IGp3dCBzZWNyZXQgZm9yIGRldmVsb3BtZW50
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=43200  # 30 days
```

### Docker Environment
```bash
# Check current values
docker exec 4genthub-server env | grep -E "JWT|MCP|AUTH"
```

---

## Log File Locations

1. **MCP Bridge Logs**: `/tmp/mcp_bridge.log`
2. **Docker Container Logs**: `docker logs 4genthub-server`
3. **Frontend Logs**: `docker logs 4genthub-frontend`

---

## Recovery Procedures

### Complete Reset
```bash
# 1. Stop containers
docker-compose down

# 2. Clear any cached data
rm -f /tmp/mcp_bridge.log

# 3. Rebuild and start
docker-compose build
docker-compose up -d

# 4. Generate new token
python3 scripts/generate_token.py

# 5. Update .mcp.json with new token

# 6. Restart Claude Code
```

### Verify Recovery
```bash
# Check all services
curl http://localhost:8000/health  # Backend
curl http://localhost:3800          # Frontend
```

---

## Prevention Tips

1. **Keep tokens fresh**: Regenerate tokens periodically
2. **Monitor logs**: Check logs regularly for early warning signs
3. **Version control**: Keep .mcp.json in sync with server changes
4. **Documentation**: Update this guide when new issues are discovered
5. **Test changes**: Always test MCP connection after configuration changes

---

## Contact for Help

If issues persist after trying these solutions:
1. Check GitHub issues: https://github.com/anthropics/claude-code/issues
2. Review server logs for specific error messages
3. Verify all prerequisites are installed and configured