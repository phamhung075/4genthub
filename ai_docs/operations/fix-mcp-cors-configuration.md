# Fix MCP CORS Configuration for Claude Code

## Problem
Claude Code cannot connect to the MCP server because CORS is blocking the connection. The server returns specific allowed origins instead of wildcard, preventing MCP connections.

## Solution

### 1. Update Backend Code (Completed)
Modified `4genthub_main/src/fastmcp/config/cors_factory.py` to:
- Allow wildcard (`*`) origins for MCP compatibility
- Automatically disable credentials when wildcard is used (browser security requirement)
- Default to wildcard when CORS_ORIGINS is not set

### 2. Update CapRover Environment Variables

In CapRover, update the backend app configuration:

```bash
# Set CORS_ORIGINS to wildcard for MCP compatibility
CORS_ORIGINS=*
```

### 3. Deploy the Updated Backend

1. Commit the changes:
```bash
git add 4genthub_main/src/fastmcp/config/cors_factory.py
git commit -m "fix: allow wildcard CORS for MCP/Claude Code compatibility"
git push origin client
```

2. In CapRover:
   - Navigate to your backend app
   - Go to "Deployment" tab
   - Deploy from the `client` branch
   - Or trigger automatic deployment if configured

### 4. Verify the Fix

1. Check the health endpoint:
```bash
curl https://api.92.5.226.7.nip.io/health
```

The response should show:
```json
{
  "cors": {
    "allowed_origins": ["*"],
    "allow_credentials": false
  }
}
```

2. Update Claude Code configuration:
```json
"4genthub_http": {
  "type": "http",
  "url": "https://api.92.5.226.7.nip.io/mcp",
  "headers": {
    "Accept": "application/json, text/event-stream",
    "Authorization": "Bearer YOUR_TOKEN_HERE"
  }
}
```

3. Restart Claude Code and test the MCP connection

## Technical Details

### Why This Fix Works
- MCP/Claude Code requires wildcard CORS to connect from various origins
- Browser security requires `allow_credentials: false` when using wildcard
- The backend now properly handles this configuration

### Security Considerations
- Using wildcard CORS is safe because:
  - Authentication is handled via Bearer tokens (not cookies)
  - Each request must include a valid JWT token
  - The API validates tokens on every request
  - No sensitive cookies are exposed

### Rollback Plan
If issues occur, revert to specific origins:
```bash
# In CapRover, set:
CORS_ORIGINS=https://api.92.5.226.7.nip.io,https://webapp.92.5.226.7.nip.io
```

## Testing Checklist
- [ ] Backend deployed with updated CORS configuration
- [ ] CORS_ORIGINS environment variable set to `*`
- [ ] Health endpoint shows wildcard origins
- [ ] Claude Code can connect to MCP server
- [ ] Frontend still works properly
- [ ] Token authentication still functions

## References
- [MDN: CORS and credentials](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS#requests_with_credentials)
- [FastAPI CORS Middleware](https://fastapi.tiangolo.com/tutorial/cors/)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)