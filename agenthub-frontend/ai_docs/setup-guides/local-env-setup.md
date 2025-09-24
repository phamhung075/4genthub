# Local Environment Setup for Frontend

## Problem
The frontend shows "Backend not connected" because there's no `.env` file with the correct environment variables.

## Solution
Create a `.env` file in the `agenthub-frontend` directory with the following content:

```bash
# Frontend Environment Variables for Local Development
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=4genthub
VITE_ENVIRONMENT=development
VITE_DEBUG_MODE=true
```

## Steps to Fix

1. Navigate to the frontend directory:
```bash
cd /home/daihungpham/__projects__/4genthub/agenthub-frontend
```

2. Create the .env file:
```bash
cat > .env << 'EOF'
# Frontend Environment Variables for Local Development
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=4genthub
VITE_ENVIRONMENT=development
VITE_DEBUG_MODE=true
EOF
```

3. Restart the frontend server:
```bash
# Kill the current process (Ctrl+C)
# Then restart:
pnpm start
```

## Why This Happens
- The code uses `VITE_API_URL` but the .env.example uses `VITE_BACKEND_URL`
- No local .env file exists by default (for security reasons)
- Without VITE_API_URL set, the frontend can't connect to the backend

## Verification
After creating the .env file and restarting:
- The login page should show "v0.0.3b - Backend v0.0.3b" (or similar)
- No more "Backend not connected" message

## Note for Production
In production, these environment variables should be set in:
- CapRover environment settings
- Docker compose files
- CI/CD pipeline

Never commit the actual .env file with real URLs to git!