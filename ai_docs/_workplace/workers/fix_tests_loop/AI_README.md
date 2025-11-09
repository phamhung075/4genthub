# AI Test Fix Loop - Integration Guide

## Quick Start

```bash
# 1. Identify failures
./test-menu.sh  # Option 2: Run Failed Tests Only

# 2. Start optimized loop
./loop-worker_testfix_optimized.sh
```

**What It Does:**
1. Reads failed tests from `.pytest_cache/test-menu-cache.json`
2. Sends ONLY current failing test to AI (minimal context)
3. Verifies fix automatically
4. Updates JSON cache status → "passed"
5. Continues with next test

---

## Optimized vs Original

| Feature | Original | Optimized | Savings |
|---------|----------|-----------|---------|
| Context Size | Exponential growth | Constant ~200 lines | 96% |
| Token Usage | 10K+ after 5 iterations | ~2K per iteration | 80% |
| Cost (10 iterations) | ~$0.50 | ~$0.05 | 90% |
| Test Selection | Manual | Automatic from cache | - |
| Progress Tracking | Accumulated context | Separate JSON | - |
| Verification | Manual | Automatic pytest | - |
| Cache Integration | None | Full | - |

---

## Context Structure (Per Iteration)

Each iteration sends ONLY:
1. Current failing test path
2. Last 50 lines of failure output
3. First 100 lines of test file
4. Progress summary (2-3 lines)
5. Clear action items

---

## File Locations

### Test Cache
- `.pytest_cache/test-menu-cache.json` - Test status, hashes, statistics
- `.pytest_cache/test-menu-last-run.log` - Last run output

### Worker Files
- `ai_docs/_workplace/workers/fix_tests_loop/`
  - `current_context.md` - AI input (small)
  - `progress.json` - Session stats
  - `session.log` - Full log
  - `instructions.md` - Custom guidelines (optional)

---

## Custom Instructions (Optional)

Create `instructions.md` for specific guidelines:
```markdown
# Custom Test Fix Instructions
- Focus on import errors first
- Update deprecated APIs
- Follow DDD patterns
- Don't modify test logic
```

---

## For AI: Fixing Tests

When loop sends you a test:
1. Read failure output (shows exact error)
2. Apply common fixes: Import paths | API updates | Missing fixtures | Incorrect assertions
3. Use Edit tool to fix test file
4. Script verifies automatically

---

## Monitoring Progress

```bash
# Watch progress
tail -f ai_docs/_workplace/workers/fix_tests_loop/session.log

# Cache statistics
jq '.statistics' .pytest_cache/test-menu-cache.json

# List failed tests
jq -r '.tests | to_entries[] | select(.value.status == "failed") | .key' .pytest_cache/test-menu-cache.json

# Worker progress
cat ai_docs/_workplace/workers/fix_tests_loop/progress.json
```

---

## When to Use Which Script

| Script | Use When |
|--------|----------|
| **Original** (`loop-worker_testfix.sh`) | Need full history \| Complex multi-file fixes \| Manual intervention |
| **Optimized** (`loop-worker_testfix_optimized.sh`) | Many similar failures \| Automatic verification \| Minimize token costs \| Overnight runs |

---

## test-menu.sh Integration

**Workflow:**
```
test-menu.sh → JSON cache → loop-worker → fixes → test-menu.sh → verify & update
```

**Benefits:**
- Single source of truth
- Atomic updates (no race conditions)
- Rich metadata (hashes, timestamps, run counts)
- Easy querying with jq

---

## JSON Cache Queries

```bash
# Statistics
jq '.statistics' .pytest_cache/test-menu-cache.json

# Count failed
jq '[.tests[] | select(.status == "failed")] | length' .pytest_cache/test-menu-cache.json

# Tests changed since last run
jq -r '.tests | to_entries[] | select(.value.status == "failed") | "\(.key) (hash: \(.value.hash))"' .pytest_cache/test-menu-cache.json

# Test run history
jq '.runs | last' .pytest_cache/test-menu-cache.json

# Most failures (by run_count)
jq -r '.tests | to_entries | sort_by(.value.run_count) | reverse | .[] | select(.value.status == "failed") | "\(.key): \(.value.run_count) runs"' .pytest_cache/test-menu-cache.json
```

---

## Cache Structure

```json
{
  "version": "2.0",
  "last_updated": "2025-10-24T09:30:00Z",
  "statistics": {
    "total_tests": 150,
    "passed": 140,
    "failed": 10,
    "untested": 0
  },
  "tests": {
    "/full/path/test.py": {
      "status": "failed",
      "hash": "abc123...",
      "last_run": "2025-10-24T09:30:00Z",
      "run_count": 5
    }
  },
  "runs": [
    {
      "timestamp": "2025-10-24T09:30:00Z",
      "mode": "smart",
      "tests_run": 10,
      "passed": 8,
      "failed": 2,
      "duration": 45.2
    }
  ]
}
```

---

## Token Efficiency

**How optimized script saves tokens:**
- No history accumulation (independent iterations)
- Minimal context (only what's needed)
- Smart truncation (limited large outputs)
- Cache-based state (progress tracked outside)
- Focused prompts (clear, specific)
