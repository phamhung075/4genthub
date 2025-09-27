# Keycloak Configuration for agenthub (Backend-as-Middleware)

## Architecture Overview
- **Frontend** → communicates only with → **Backend**
- **Backend** → authenticates with → **Keycloak**
- Frontend never directly communicates with Keycloak (backend handles all auth)

## Client Configuration

### Basic Settings
- **Client ID:** `mcp-backend`
- **Name:** MCP Backend Services
- **Description:** Backend services for agenthub platform
- **Always display in UI:** On

### Access Settings
- **Root URL:** `https://agenthub-backend.92.5.226.7.nip.io`
- **Home URL:** `https://agenthub-backend.92.5.226.7.nip.io`

### Valid Redirect URIs
Since only backend talks to Keycloak:
```
https://agenthub-backend.92.5.226.7.nip.io/*
http://localhost:8000/*
```

### Valid Post Logout Redirect URIs
```
https://agenthub-backend.92.5.226.7.nip.io/*
http://localhost:8000/*
```

### Web Origins (CORS)
Only backend origins needed (WITHOUT trailing slashes or wildcards):
```
https://agenthub-backend.92.5.226.7.nip.io
http://localhost:8000
```

## Authentication Settings
- **Client authentication:** Off (for public client)
- **Authorization:** On
- **Standard flow:** On (for authorization code flow)
- **Direct access grants:** On (for resource owner password flow)
- **Implicit flow:** Off (not recommended)
- **Service accounts:** Off (unless needed for backend-to-backend auth)

## Frontend Environment Variables
Set these in your frontend build:
```bash
VITE_KEYCLOAK_URL=https://your-keycloak-server.com
VITE_KEYCLOAK_REALM=your-realm
VITE_KEYCLOAK_CLIENT_ID=mcp-backend
```

## Backend Environment Variables
Set these in CapRover for the backend:
```bash
KEYCLOAK_URL=https://your-keycloak-server.com
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=mcp-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret  # If using confidential client
```

## Important Notes

1. **URL Consistency:** Ensure all URLs match your actual deployed services
2. **Web Origins:** Do NOT include `/*` or wildcards in Web Origins - use base URLs only
3. **Development URLs:** Keep localhost URLs for local development
4. **HTTPS Required:** Production URLs should use HTTPS for security
5. **Client Type:** 
   - Use "public" client for frontend (no client secret)
   - Use "confidential" client for backend-only authentication

## Troubleshooting

### CORS Errors
If you see CORS errors:
1. Check Web Origins includes the exact origin (no trailing slash)
2. Verify the frontend URL matches what's in the browser
3. Ensure backend CORS_ORIGINS environment variable includes frontend URL

### Authentication Failures
If authentication fails:
1. Check Valid Redirect URIs includes your callback URL
2. Verify Keycloak realm and client ID match in both frontend and backend
3. Check Keycloak server is accessible from both frontend and backend

### Token Validation Issues
If token validation fails:
1. Ensure backend can reach Keycloak server
2. Check KEYCLOAK_URL is correct in backend environment
3. Verify realm and client ID match between frontend and backend