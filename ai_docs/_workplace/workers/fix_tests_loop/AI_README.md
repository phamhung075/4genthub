# AI Test Fix Loop Integration Guide

## How to Use the Optimized Test Fix Loop

### Quick Start for AI Agents

When you need to fix failing tests automatically:

1. **Run test-menu.sh first** to identify failures:
   ```bash
   ./test-menu.sh
   # Choose option 2 (Run Failed Tests Only)
   ```

2. **Start the optimized loop worker**:
   ```bash
   ./loop-worker_testfix_optimized.sh
   ```

3. **The loop will**:
   - Read failed tests from `.test_cache/failed_tests.txt`
   - Send ONLY the current failing test to you (minimal context)
   - Verify your fix automatically
   - Move fixed tests to `.test_cache/passed_tests.txt`
   - Continue with next test

### Key Improvements Over Original Script

| Feature | Original | Optimized |
|---------|----------|-----------|
| Context Size | Grows exponentially (all history) | Constant (~200 lines max) |
| Token Usage | 10K+ after 5 iterations | ~2K per iteration |
| Test Selection | Manual in instructions | Automatic from cache |
| Progress Tracking | In accumulated context | Separate JSON file |
| Verification | Manual | Automatic with pytest |
| Cache Integration | None | Full integration |

### Context Structure (What AI Receives)

Each iteration sends ONLY:
1. Current failing test path
2. Last 50 lines of test failure output
3. First 100 lines of test file
4. Minimal progress summary (2-3 lines)
5. Clear action items

### File Locations

- **Test Cache**: `.test_cache/`
  - `failed_tests.txt` - Tests to fix
  - `passed_tests.txt` - Fixed tests
  - `test_hashes.txt` - Change detection

- **Worker Files**: `ai_docs/_workplace/workers/fix_tests_loop/`
  - `current_context.md` - What's sent to AI (small)
  - `progress.json` - Session statistics
  - `session.log` - Full execution log
  - `instructions.md` - Custom instructions (optional)

### Custom Instructions

Create `instructions.md` to add specific guidelines:

```markdown
# Custom Test Fix Instructions

- Focus on import errors first
- Update deprecated APIs to new versions
- Follow DDD patterns in all fixes
- Don't modify test logic, only fix syntax/imports
```

### For AI: Understanding Test Failures

When the loop sends you a test to fix:

1. **Read the failure output** - Usually shows the exact error
2. **Common fixes needed**:
   - Import path corrections
   - API updates (deprecated methods)
   - Missing test fixtures
   - Incorrect assertions

3. **Use the Edit tool** to fix the test file directly
4. **The script will verify** your fix automatically

### Monitoring Progress

While the loop runs, you can monitor:

```bash
# Watch progress
tail -f ai_docs/_workplace/workers/fix_tests_loop/session.log

# Check remaining failures
wc -l .test_cache/failed_tests.txt

# See fixed tests
wc -l .test_cache/passed_tests.txt

# View progress stats
cat ai_docs/_workplace/workers/fix_tests_loop/progress.json
```

### Token Efficiency Tips

The optimized script saves tokens by:
- **No history accumulation** - Each iteration is independent
- **Minimal context** - Only what's needed for current test
- **Smart truncation** - Large outputs are limited
- **Cache-based state** - Progress tracked outside context
- **Focused prompts** - Clear, specific instructions

### Comparison: Token Usage

**Original Script** (after 10 iterations):
- Context: ~50,000 tokens (accumulated)
- Cost: ~$0.50 per session

**Optimized Script** (after 10 iterations):
- Context: ~2,000 tokens per iteration
- Cost: ~$0.05 per session

### When to Use Each Script

**Use Original** (`loop-worker_testfix.sh`) when:
- Need full history context
- Complex multi-file fixes
- Manual intervention between iterations

**Use Optimized** (`loop-worker_testfix_optimized.sh`) when:
- Fixing many similar test failures
- Want automatic verification
- Need to minimize token costs
- Running overnight/unattended

### Integration with test-menu.sh

The scripts work together:

1. **test-menu.sh** - Identifies and caches test status
2. **loop-worker_testfix_optimized.sh** - Fixes failures from cache
3. **test-menu.sh** - Verifies all fixes are working

This creates an efficient workflow:
```
test-menu.sh → identify failures → loop-worker → fix tests → test-menu.sh → verify
```