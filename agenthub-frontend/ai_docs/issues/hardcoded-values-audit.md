# Hardcoded Values Audit Report

## Summary
This document lists all hardcoded values found in the codebase that should potentially be moved to environment variables or configuration files for better maintainability and deployment flexibility.

**Last Updated**: 2025-09-24
**Status**: ✅ FIXED - All critical hardcoded values have been resolved

## Critical Hardcoded Values ~~to Fix~~ FIXED

### 1. Backend API URLs ✅ FIXED
- **File**: `src/services/WebSocketClient.ts:72`
  - ~~Current: `'ws://localhost:8000'`~~
  - **FIXED**: Now uses `VITE_WS_URL` environment variable without fallback
  - **Change**: Added validation to fail fast if not configured

- **File**: `src/config/environment.ts:34`
  - Current: `'http://localhost:8000'`
  - **Note**: This is the default for development, properly overridden by VITE_API_URL in production
  - **Status**: Acceptable as development default

- **File**: `src/config/logger.config.ts:84`
  - ~~Current: `'http://localhost:8000/api/logs/frontend'`~~
  - **FIXED**: Now uses `${API_BASE_URL}/api/logs/frontend`
  - **Change**: Imported API_BASE_URL from environment config

### 2. Authentication Endpoints ✅ FIXED
- **File**: `src/components/auth/SignupForm.tsx:127`
  - ~~Current: `'/auth/supabase/resend-verification'` with localhost fallback~~
  - **FIXED**: Now uses `${API_BASE_URL}/auth/supabase/resend-verification`
  - **Change**: Imported API_BASE_URL from environment config

- **File**: `src/components/auth/EmailVerification.tsx:79`
  - ~~Current: `'/auth/supabase/resend-verification'` with localhost fallback~~
  - **FIXED**: Now uses `${API_BASE_URL}/auth/supabase/resend-verification`
  - **Change**: Imported API_BASE_URL from environment config

### 3. Token Management ✅ FIXED
- **File**: `src/pages/TokenManagement.tsx:776,796,879`
  - ~~Current: Multiple references to `'localhost'` and `'http://localhost:8000'`~~
  - **FIXED**: All three occurrences now use `API_BASE_URL`
  - **Changes**:
    - Line 776-777: Uses `API_BASE_URL` for host/port extraction
    - Line 796: Uses `${API_BASE_URL}/mcp`
    - Line 879: Uses `${API_BASE_URL}/mcp`

### 4. Port Numbers
- **File**: `src/config/environment.ts:97`
  - Current: `timeout: 30000` (30 seconds)
  - Issue: Hardcoded timeout value
  - Fix: Make configurable via environment

### 5. External URLs
- **File**: `src/pages/HelpSetup.tsx`
  - Lines 129, 137, 145: External documentation/support URLs
  - Current: Discord, GitHub, docs links
  - Issue: May need to be configurable for different deployments
  - Consider: Moving to configuration object

## Medium Priority Hardcoded Values

### 1. Refresh Intervals
- **File**: `src/hooks/useBranchSummaries.ts:30,150`
  - Current: `30000` (30 seconds)
  - Issue: Hardcoded refresh interval
  - Fix: Make configurable

- **File**: `src/components/PerformanceDashboard.tsx:120`
  - Current: `30000` (30 seconds)
  - Issue: Hardcoded metrics refresh interval
  - Fix: Make configurable

### 2. Animation/UI Durations
- **File**: `src/components/WebSocketToastBridge.tsx:30`
  - Current: `8000` for errors, `5000` for others
  - Issue: Hardcoded toast durations
  - Fix: Move to constants or configuration

- **File**: `src/components/NotificationSettings.tsx:67`
  - Current: `3000` (3 seconds)
  - Issue: Hardcoded notification delay
  - Fix: Move to constants

## Low Priority (Acceptable Hardcoded Values)

### 1. External CDN/Fonts
- **File**: `src/index.css:2`
  - Google Fonts URL - Acceptable for CDN resources

### 2. SVG Namespaces
- **File**: `src/components/UserProfileDropdown.tsx`
  - Multiple `xmlns="http://www.w3.org/2000/svg"` - Standard SVG namespace

### 3. Test Data
- **Files**: Various test files
  - Test-specific URLs and mock data - Acceptable in test files

### 4. Example/Demo Data
- **Files**: `src/components/ProjectContextDialog.tsx`, `src/components/BranchContextDialog.tsx`
  - Example configuration strings - Acceptable as demo data

## Fix Summary

All critical hardcoded values have been successfully fixed:

1. ✅ **WebSocket URL** (`WebSocketClient.ts`) - Now fails fast if VITE_WS_URL not configured
2. ✅ **Authentication Endpoints** (`SignupForm.tsx`, `EmailVerification.tsx`) - Using API_BASE_URL
3. ✅ **Token Management** (`TokenManagement.tsx`) - All localhost references removed
4. ✅ **Logger Config** (`logger.config.ts`) - Using API_BASE_URL for remote endpoint

### Files Modified:
- `src/services/WebSocketClient.ts` - Added proper environment validation
- `src/components/auth/SignupForm.tsx` - Imported and used API_BASE_URL
- `src/components/auth/EmailVerification.tsx` - Imported and used API_BASE_URL
- `src/pages/TokenManagement.tsx` - Imported and used API_BASE_URL (3 locations)
- `src/config/logger.config.ts` - Imported and used API_BASE_URL

## Recommendations

### ~~Immediate Actions Required:~~ COMPLETED ✅
1. ~~**Fix WebSocket URL** in `WebSocketClient.ts` - Remove hardcoded fallback~~ ✅ DONE
2. ~~**Fix API endpoints** in auth components - Use API_BASE_URL consistently~~ ✅ DONE
3. ~~**Fix Token Management** page - Remove all localhost references~~ ✅ DONE

### Configuration Strategy:
1. Create a central configuration service that:
   - Validates all required environment variables on startup
   - Provides typed access to configuration values
   - Fails fast in production if configuration is missing

2. Move all timeouts, intervals, and durations to a constants file:
   ```typescript
   export const TIMEOUTS = {
     API_REQUEST: 30000,
     METRICS_REFRESH: 30000,
     TOAST_ERROR: 8000,
     TOAST_SUCCESS: 5000,
   };
   ```

3. For external URLs (Discord, GitHub, docs):
   - Create a `links.config.ts` file with all external links
   - Makes it easier to update across the application

### Environment Variables to Add:
```env
# Required in production
VITE_WS_URL=wss://api.4genthub.com
VITE_API_URL=https://api.4genthub.com

# Optional with defaults
VITE_API_TIMEOUT=30000
VITE_METRICS_REFRESH_INTERVAL=30000
VITE_TOAST_DURATION_ERROR=8000
VITE_TOAST_DURATION_SUCCESS=5000
```

## Security Considerations
- Never commit actual API keys, secrets, or passwords
- All authentication tokens should come from secure storage (cookies/localStorage)
- Environment variables should be validated on application startup
- Production builds should fail if required configuration is missing

## Next Steps
1. Create configuration service module
2. Update all components to use configuration service
3. Add environment variable validation on startup
4. Update deployment documentation with required variables
5. Test with different environment configurations