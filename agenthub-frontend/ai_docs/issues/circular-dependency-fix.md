# Circular Dependency Fix - environment.ts and logger

## Problem
There was a circular dependency between:
- `src/config/environment.ts` → imports `logger` from `src/utils/logger`
- `src/config/logger.config.ts` → imports `API_BASE_URL` from `src/config/environment.ts`
- `src/utils/logger` → imports config from `src/config/logger.config.ts`

This caused the error:
```
environment.ts:78 Uncaught ReferenceError: Cannot access 'logger' before initialization
```

## Root Cause
When fixing hardcoded URLs, we added `import { API_BASE_URL } from './environment'` to `logger.config.ts`, creating a circular dependency chain.

## Solution
Removed the logger import from `environment.ts` and replaced all logger calls with console methods:
- `logger.error()` → `console.error()`
- `logger.warn()` → `console.warn()`
- `logger.debug()` → `console.debug()`
- `logger.info()` → `console.info()`

## Files Modified
- `src/config/environment.ts` - Removed logger import, replaced with console

## Why This Works
- Environment configuration is a low-level module that should not depend on higher-level modules
- Console methods are sufficient for environment configuration warnings/errors
- Breaking the circular dependency allows proper module initialization

## Verification
- ✅ Build succeeds without errors
- ✅ Development server starts without initialization errors
- ✅ No circular dependency warnings