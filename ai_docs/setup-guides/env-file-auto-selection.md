# Environment File Auto-Selection

## Overview
The frontend now automatically selects between `.env.dev` and `.env` files from the project root directory.

## How It Works

The `vite.config.ts` has been modified to:

1. **Priority: `.env.dev` > `.env`** - `.env.dev` always takes priority when it exists
2. **Auto-copy** - If `.env.dev` exists, it's automatically copied to `.env` for Vite to load
3. **Fallback** - If only `.env` exists (no `.env.dev`), it uses that
4. **Transparent** - Console logs show exactly which file is being used

## File Locations
- **Project Root**: `/home/daihungpham/__projects__/4genthub/`
- **`.env.dev`**: Development environment variables (committed to git)
- **`.env`**: Active environment file (git-ignored, auto-created from `.env.dev`)

## Behavior

### Scenario 1: Only `.env.dev` exists
- Vite automatically copies `.env.dev` to `.env`
- Uses the newly created `.env` file
- Console shows: `📁 Using .env.dev (no .env file found)`

### Scenario 2: Only `.env` exists
- Uses the existing `.env` file
- Console shows: `📁 Using existing .env file (no .env.dev found)`

### Scenario 3: Both files exist
- **`.env.dev` takes priority** - copies `.env.dev` over `.env`
- Console shows: `📁 Both .env and .env.dev exist, using .env.dev priority`

### Scenario 4: No env files
- Vite continues with default values
- Console shows: `⚠️ No .env or .env.dev file found in parent directory`

## Benefits
1. **No manual copying needed** - Automatic setup for new developers
2. **Custom overrides supported** - Can create custom `.env` that won't be overwritten
3. **Git-friendly** - `.env.dev` is committed, `.env` is ignored
4. **Transparent** - Console logs show which file is being used

## Configuration
Modified file: `agenthub-frontend/vite.config.ts`

The configuration:
- Loads env files from parent directory (`envDir: '..'`)
- Checks for both `.env.dev` and `.env`
- Automatically handles copying when needed

## Testing
After any changes to env files:
1. Stop the frontend server (Ctrl+C)
2. Delete `.env` if you want to use `.env.dev`: `rm .env`
3. Restart: `cd agenthub-frontend && pnpm start`
4. Check console output for which env file was loaded

## Note
The `.env` file is automatically created and should NOT be committed to git. It's already in `.gitignore`.