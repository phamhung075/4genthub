# Local Environment Setup for Frontend

## Problem
The frontend shows "Backend not connected" when the environment file Vite actually reads is missing or incomplete — the **REPO ROOT `.env`**, not one inside `agenthub-frontend` (see the correction under Solution).

## Solution
Create (or edit) the **PARENT `.env` — the repository root** — with the following content. **`agenthub-frontend/vite.config.ts:201` sets `envDir: '..'`, so the file Vite actually loads is the ROOT `.env`, not one inside `agenthub-frontend`** (corrected 2026-10-06; the earlier version of this page said the frontend directory, which Vite never reads):

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

2. Create the .env file **at the repository root** (with `envDir: '..'`, a `.env` inside `agenthub-frontend` is never read):
```bash
cd /home/daihu/__projects__/4genthub && cat > .env << 'EOF'
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
- **The file that matters is the ROOT `.env`** (`envDir: '..'`), and in this checkout the root `.env` already exists with `VITE_WS_URL` set — so the value IS in force; the earlier claim that no local `.env` exists applies to the frontend directory, which Vite does not read
- Without VITE_API_URL set, the frontend can't connect to the backend

## Verification
After creating the .env file and restarting:
- The login page shows a version badge with the frontend and backend versions — the `v0.0.3b` pair recorded here on 2026-10-04 is dated: the frontend is at **`0.0.6`** (`package.json`) and the backend marker is **`0.0.20`** in the current packet
- No more "Backend not connected" message

## The knob that looks wired and is not — CORRECTED TWICE, AND THIS SECOND PASS REVERSES THE FIRST (2026-10-06)

**A SHELL EXPORT WINS, and this section said the opposite an hour ago.** Vite's loader writes the **file** values first and then **overwrites them from the process environment** (`vite/dist/node/chunks/dep-Bm2ujbhY.js:12563` reads the parsed files into the env object, and `:12564` then runs `for (const key in process.env)` over the same prefix namespace) — and that precedence is documented — so **exporting `VITE_WS_URL` before the start command DOES take effect.**

**WHAT STANDS FROM THE FIRST PASS:** the config's env directory is the **PARENT** (`vite.config.ts:201`, `envDir: '..'`), so the file Vite reads is the **REPO ROOT `.env`**, and a `.env` inside `agenthub-frontend` is not read at all.

**WHAT THIS PASS RETRACTS:** the sentence *"an export in the shell changes nothing"* — written to replace the ORIGINAL wrong claim and itself wrong, in the opposite direction. **The shape is therefore the stricter one: a configuration LOAD PATH was documented without reading the configuration that decides it, and then a CORRECTION to it was written without reading the LOADER that decides the precedence.**

**AND THE LIVE QUESTION, which the false trap had been covering: why the original export experiment returned nothing, given that the export wins.** That gap is **open and assigned**, not explained by this section.

**Why it matters for the socket and not only the URL (measured 2026-10-06, `c69d128a`):** with `/api` proxied but **no `/ws` entry**, the dev server accepted the websocket upgrade itself, so the app reported **CONNECTED / Live** against a socket that never reached the backend — while the reported symptom looked like the opposite, a bare **Offline**. The discriminator was the **no-token** case: only the real backend answers with close **1008** and its own reason text. **A surface reporting healthy is not evidence that it reached the thing it names.**

## Note for Production
In production, these environment variables should be set in:
- CapRover environment settings
- Docker compose files
- CI/CD pipeline

Never commit the actual .env file with real URLs to git!
