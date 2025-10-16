# HMR (Hot Module Replacement) Debugging Guide

## Overview
This guide documents the HMR debugging system added to the agenthub frontend for troubleshooting hot reload issues.

## Server-Side Debugging (vite.config.ts)

### HMR Debug Plugin
A custom Vite plugin that logs detailed information about hot module replacement:

**Features:**
- **File Change Detection**: Logs which files triggered HMR updates
- **Module Graph Analysis**: Shows module connections and importers
- **Timestamp Tracking**: Precise timing for each HMR event
- **WebSocket Monitoring**: Tracks HMR WebSocket connection status
- **Error Logging**: Captures and logs HMR errors

**Output Format:**
```
🔥 [2025-10-16T06:18:04.664Z] HMR Update Triggered
   📄 File: /path/to/changed/file.tsx
   🔗 Module graph connections: 0
   ↳ Module: /path/to/module.tsx
      Invalidated: yes
      Importers: 3
```

### Server Configuration Enhancements
- **Error Overlay**: Enabled to show errors in browser
- **Verbose Logging**: Set to 'info' level for detailed output
- **Watch System**: Already using polling for reliable file detection
- **HMR Protocol**: WebSocket-based for real-time updates

## Client-Side Debugging (index.tsx)

### HMR Event Listeners
Added comprehensive event listeners for HMR lifecycle:

**Events Tracked:**
1. **vite:beforeUpdate** - Before HMR applies changes
2. **vite:afterUpdate** - After HMR successfully applies changes
3. **vite:error** - When HMR encounters errors
4. **vite:beforeFullReload** - When full page reload is required
5. **vite:ws:connect** - WebSocket connection established
6. **vite:ws:disconnect** - WebSocket connection lost

**Browser Console Output:**
```
🔥 HMR Client Initialized
⚡ HMR Update Received: { type: 'update', updates: 1, timestamp: '...' }
✅ HMR Update Applied: { type: 'update', timestamp: '...' }
🔌 HMR WebSocket Connected
```

## How to Use

### 1. Check Server Logs
Monitor `logs/frontend.log` for server-side HMR activity:
```bash
tail -f logs/frontend.log
```

Look for:
- "🚀 HMR Debug Plugin Enabled" - Plugin is active
- "🔥 HMR Update Triggered" - File changes detected
- "🔌 HMR WebSocket connection established" - Client connected

### 2. Check Browser Console
Open browser DevTools console to see client-side HMR events:
- Hot reload working: See "✅ HMR Update Applied" messages
- Connection issues: See "🔌 HMR WebSocket Disconnected" warnings
- Errors: See "❌ HMR Error" with details

### 3. Verify File Changes
Edit any frontend file and watch for:
- Server log shows file path that changed
- Module graph shows affected modules
- Browser console shows update received and applied

## Troubleshooting with Debug Info

### Issue: WebSocket connection failed (WSL2 Specific)
**Symptoms:**
- Browser console: `WebSocket connection to 'ws://0.0.0.0:3800/' failed`
- Error: `WebSocket closed without opened`
- HMR not working at all

**Root Cause:**
In WSL2, browsers cannot connect to WebSocket servers on `0.0.0.0` - they need `localhost`

**Solution:**
Configure HMR to use `localhost` for client connections while server binds to `0.0.0.0`:
```typescript
hmr: {
  protocol: 'ws',
  host: 'localhost',  // Client connects to localhost
  port: 3800,
  clientPort: 3800
}
```

**Note:** Server host remains `0.0.0.0` for broad network access, only HMR client uses `localhost`

### Issue: Files change but browser doesn't update
**Check:**
1. Server logs show "🔥 HMR Update Triggered"?
   - No: Watch system issue, check file permissions
   - Yes: Continue to step 2

2. Browser console shows "⚡ HMR Update Received"?
   - No: WebSocket connection issue (see above)
   - Yes: Continue to step 3

3. Browser console shows "✅ HMR Update Applied"?
   - No: Check for errors in console
   - Yes: Issue may be React component state

### Issue: Full page reloads instead of hot updates
**Look for:**
- "🔄 Full Page Reload Required" in browser console
- Check server logs for why module couldn't be hot-updated
- Common causes: CSS changes, config changes, certain import changes

### Issue: WebSocket disconnections
**Monitor:**
- "🔌 HMR WebSocket Disconnected" warnings
- "🔌 HMR WebSocket Connected" reconnection attempts
- Network tab in DevTools for WebSocket connections

## Configuration Details

### Vite Server Config (vite.config.ts:86-108)
```typescript
server: {
  host: '0.0.0.0',
  port: 3800,
  hmr: {
    protocol: 'ws',
    host: '0.0.0.0',
    port: 3800,
    clientPort: 3800,
    overlay: true // Error overlay enabled
  },
  watch: {
    usePolling: true,
    interval: 100,
    binaryInterval: 300,
    awaitWriteFinish: {
      stabilityThreshold: 500,
      pollInterval: 100
    }
  },
  logLevel: 'info'
}
```

### HMR Plugin Location
- File: `agenthub-frontend/vite.config.ts`
- Lines: 49-82
- Plugin name: `hmr-debug`

### Client-Side Debugging Location
- File: `agenthub-frontend/src/index.tsx`
- Lines: 47-89
- Condition: Only active when `import.meta.hot` is available (development mode)

## Performance Impact

### Development Mode
- **Minimal**: Logging operations are fast
- **Console**: Some additional console output
- **Network**: No additional overhead

### Production Mode
- **None**: All debug code is removed in production build
- Client-side: `import.meta.hot` is `undefined` in production
- Server-side: Plugin only runs in dev mode

## Future Enhancements

Potential improvements:
1. Configurable debug levels (verbose, normal, quiet)
2. File filtering to reduce noise
3. Performance metrics (HMR update duration)
4. Export debug logs to file
5. Visual overlay for HMR status in browser

## Related Documentation

- [Vite HMR API](https://vitejs.dev/guide/api-hmr.html)
- [Vite Server Options](https://vitejs.dev/config/server-options.html)
- Frontend Configuration: `agenthub-frontend/vite.config.ts`
- Hot Reload Issues: `ai_docs/issues/`

## Changelog

**2025-10-16**: Initial HMR debugging system implementation
- Added HMR debug plugin to vite.config.ts
- Added client-side HMR event listeners to index.tsx
- Enabled error overlay and verbose logging
- Documentation created
