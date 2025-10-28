# Frontend Response Validation System

## Overview

This system automatically validates all API responses and WebSocket messages against expected TypeScript type definitions to catch discrepancies between backend responses and frontend expectations.

## Features

### 1. API Response Validation
- Validates all HTTP API responses from `apiV2.ts`
- Checks response structure against TypeScript types
- Validates field types, null/undefined values, and data consistency
- Logs errors and warnings for investigation

### 2. WebSocket Message Validation
- Validates all WebSocket messages received via `useWebSocketV2` hook
- Checks message structure and payload integrity
- Validates cascade data and entity updates
- Tracks validation statistics

### 3. Validation Statistics
- Tracks total validations, failures, and warnings
- Groups errors by field name and endpoint
- Calculates failure rates
- Provides exportable reports

## Usage

### Enable Validation

**Development Mode (Automatic):**
```bash
# Validation is ENABLED by default in development mode
npm run dev
```

**Production Mode (Manual):**
```bash
# Set environment variable to enable in production
VITE_VALIDATE_RESPONSES=true npm run build
```

### View Validation Results

**Console Logs:**
All validation results are logged to the browser console:
- ✅ Green checkmarks for successful validations
- ⚠️ Yellow warnings for non-critical issues
- 🚨 Red errors for validation failures

**Statistics Summary:**
Every 30 seconds in development, statistics are logged automatically:
```javascript
// Console output example:
📊 [Response Validation] Statistics Summary
{
  totalValidations: 150,
  failedValidations: 3,
  failureRate: "2%",
  errorsByField: { "subtask_count": 2, "assignees": 1 },
  errorsByEndpoint: { "/api/v2/tasks/123": 3 }
}
```

### Export Validation Reports

**Using Browser Console:**
```javascript
// Access global validation utilities
window.__validationUtils

// Generate full report
window.__validationUtils.getReport()

// Log report to console
window.__validationUtils.log()

// Export as JSON
window.__validationUtils.exportJSON()

// Export as Markdown
window.__validationUtils.exportMarkdown()

// Download report file
window.__validationUtils.download('markdown') // or 'json'

// Reset statistics
window.__validationUtils.reset()
```

## What is Validated

### Task Responses
- **Required UUID fields:** `id`, `git_branch_id`, `project_id`
- **Required string fields:** `title`
- **Array fields:** `assignees` (must be array, not null)
- **Timestamp fields:** `created_at`, `updated_at` (ISO 8601 format)
- **Subtask counts:** `subtask_count` matches `subtasks.length`
- **Completed counts:** `completed_subtasks` matches actual completed count
- **Progress:** `progress_percentage` in range 0-100
- **Context:** `context_data` is object, not null
- **Assignee format:** Each assignee has `@` prefix

### Subtask Responses
- **Required UUID fields:** `id`, `parent_task_id` or `task_id`
- **Required string fields:** `title`
- **Timestamp fields:** `created_at`, `updated_at`
- **Progress:** `progress_percentage` in range 0-100
- **Assignees:** Array format if present

### Project Responses
- **Required UUID field:** `id`
- **Required string field:** `name`
- **Timestamp format:** ISO 8601

### Branch Responses
- **Required UUID fields:** `id`, `project_id`
- **Required string field:** `git_branch_name`

### WebSocket Messages
- **Message structure:** `type`, `payload`, `metadata`
- **Payload structure:** `entity`, `action`, `data`
- **Data validation:** `primary` data validated against entity type
- **Cascade validation:** Cascade structure and entity consistency

## Common Issues Detected

### 1. Null vs Empty Array
**Problem:** Backend returns `null` instead of `[]`
```javascript
// ❌ BAD
{ assignees: null }

// ✅ GOOD
{ assignees: [] }
```

### 2. Count Mismatches
**Problem:** Count fields don't match actual array length
```javascript
// ❌ BAD
{
  subtasks: [{...}, {...}],
  subtask_count: 3  // WRONG!
}

// ✅ GOOD
{
  subtasks: [{...}, {...}],
  subtask_count: 2  // Matches length
}
```

### 3. Missing @ Prefix
**Problem:** Assignees missing `@` prefix
```javascript
// ❌ BAD
{ assignees: ["coding-agent"] }

// ✅ GOOD
{ assignees: ["@coding-agent"] }
```

### 4. Invalid UUIDs
**Problem:** ID fields are null, empty, or malformed
```javascript
// ❌ BAD
{ id: "" }
{ id: null }
{ id: "abc123" }

// ✅ GOOD
{ id: "550e8400-e29b-41d4-a716-446655440000" }
```

## Files Modified

### New Files Created:
1. `src/utils/responseValidator.ts` - Core response validation logic
2. `src/utils/websocketValidator.ts` - WebSocket message validation
3. `src/utils/validationStatsExporter.ts` - Statistics and reporting

### Modified Files:
1. `src/services/apiV2.ts` - Added response validation interceptor
2. `src/hooks/useWebSocketV2.ts` - Added WebSocket message validation

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  API Response Flow                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. fetch(endpoint) → Response                           │
│  2. response.json() → data                               │
│  3. validateResponse(data, type, endpoint)               │
│     ├── Check field types                                │
│     ├── Check null/undefined values                      │
│     ├── Check data consistency                           │
│     └── Log errors/warnings                              │
│  4. Record statistics                                    │
│  5. Return data to caller                                │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                WebSocket Message Flow                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. WebSocket.onmessage(message)                         │
│  2. validateWebSocketMessage(message)                    │
│     ├── Check message structure                          │
│     ├── Check payload structure                          │
│     ├── Validate primary data                            │
│     ├── Validate cascade data                            │
│     └── Log errors/warnings                              │
│  3. Record statistics                                    │
│  4. Dispatch to Redux                                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Performance Impact

- **Development:** Minimal impact (~1-2ms per validation)
- **Production:** Disabled by default (zero impact)
- **Statistics:** Logged every 30 seconds (low overhead)

## Debugging Tips

### 1. Check Console for Errors
All validation failures are logged with full details:
```javascript
🚨 [Response Validation] FAILED
{
  endpoint: "/api/v2/tasks/123",
  errors: [{field: "subtask_count", expected: "2", actual: "3"}],
  receivedData: {...}
}
```

### 2. Export Reports Regularly
Download validation reports during testing:
```javascript
window.__validationUtils.download('markdown')
```

### 3. Monitor Statistics
Check failure rates to identify patterns:
```javascript
window.__validationUtils.log()
```

### 4. Reset Between Tests
Clear statistics between test runs:
```javascript
window.__validationUtils.reset()
```

## Integration with Phase 1A

This frontend validation (Phase 1B) complements the backend middleware validation (Phase 1A):

- **Backend (Phase 1A):** Validates responses before sending
- **Frontend (Phase 1B):** Validates responses after receiving
- **Together:** Complete coverage of the entire request/response cycle

Both systems log to the same investigation report format for comprehensive analysis.

## Next Steps

After validation data is collected:
1. **Phase 2:** Create E2E tests based on discovered issues
2. **Phase 3:** Test critical scenarios (subtask counts, WebSocket cascades)
3. **Phase 4:** Generate fix tasks for each validated issue

## Environment Variables

```bash
# Enable validation in production (optional)
VITE_VALIDATE_RESPONSES=true

# Validation is automatically enabled in development
NODE_ENV=development
```

## Support

For questions or issues with the validation system:
1. Check browser console for validation logs
2. Export validation report for analysis
3. Review this documentation
4. Check related files in `src/utils/`
