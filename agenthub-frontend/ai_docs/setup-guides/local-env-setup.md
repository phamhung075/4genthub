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
cd /home/daihu/__projects__/4genthub/agenthub-frontend
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
- The code and `agenthub-frontend/.env.sample` both use **`VITE_API_URL`** (`src/config/environment.ts:38`); the old mismatch with `VITE_BACKEND_URL` is gone, and `getEnvVar` falls back to `http://localhost:8000` when it is unset
- No local .env file exists by default (for security reasons)
- Without VITE_API_URL set, the frontend can't connect to the backend

## Verification
After creating the .env file and restarting:
- The login page shows a version badge with the frontend and backend versions — the `v0.0.3b` pair recorded here on 2026-10-04 is dated: the frontend is at **`0.0.6`** (`package.json`) and the backend marker is **`0.0.20`** in the current packet
- No more "Backend not connected" message

## The one variable this recipe cannot rescue: `VITE_WS_URL` is inert outside a `.env` file

**Exporting `VITE_WS_URL` in the shell before the start command changes NOTHING in development.** Vite exposes only **`.env` files** to `import.meta.env`, never the process environment (`src/config/environment.ts:88` reads it through `getEnvVar`), so a null result from that experiment is the **tool**, not the setting — put the value in `.env`, as step 2 above does.

**Why it matters for the socket and not only the URL (measured 2026-10-06, `c69d128a`):** with `/api` proxied but **no `/ws` entry**, the dev server accepted the websocket upgrade itself, so the app reported **CONNECTED / Live** against a socket that never reached the backend — while the reported symptom looked like the opposite, a bare **Offline**. The discriminator was the **no-token** case: only the real backend answers with close **1008** and its own reason text. **A surface reporting healthy is not evidence that it reached the thing it names.**

## Note for Production
In production, these environment variables should be set in:
- CapRover environment settings
- Docker compose files
- CI/CD pipeline

Never commit the actual .env file with real URLs to git!
