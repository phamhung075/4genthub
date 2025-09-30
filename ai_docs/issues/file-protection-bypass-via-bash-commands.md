# File Protection Bypass via Bash Commands and Scripts

**Issue ID**: FILE-PROTECTION-001
**Severity**: High
**Status**: Documented
**Date Discovered**: 2025-09-30
**Category**: Security / File System Protection

## Summary

The `pre_tool_use.py` hook successfully prevents Claude from creating unauthorized files via Write/Edit tools, but **cannot prevent** files created by Bash commands, Python scripts, or test runners that use native file I/O operations.

## Evidence

Found 21 unauthorized files in project root that bypassed protection:

### Unauthorized Python Files (8)
- `debug_context_injector.py`
- `simple_pattern_test.py`
- `test_cascade_deletion.py`
- `test_glob_logic.py`
- `test_suite_verifier.py`
- `toggle_auth.py`

### Unauthorized Output Files (13)
- `context_templates_test_output.txt`
- `not_allowed_test.txt`
- `should_be_blocked.txt`
- `test_blocking.txt`
- `test_output.log`
- `test_results.log`
- `test_run_output.txt`
- `test_run_output_full.txt`
- `test_verification_110.log`
- `test_verification_report_iteration16.txt`
- `unit_test_output.txt`

### Unauthorized Shell Scripts (1)
- `check_tests.sh`

**Total**: 21 files that should have been blocked but weren't

## Root Cause Analysis

### Architecture Limitation

```
┌─────────────────────────────────────────────────────────────┐
│                   Claude Code System                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ✅ PROTECTED PATH (via pre_tool_use.py):                   │
│     Claude → Write/Edit Tool → pre_tool_use validation      │
│                                                              │
│  ❌ UNPROTECTED PATH (bypass):                              │
│     Claude → Bash Tool → Python script → open() → File      │
│     Claude → Bash Tool → test runner → file creation        │
│     Claude → Bash Tool → echo "data" > file.txt             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Why It Happens

1. **Hook Scope Limitation**: `pre_tool_use.py` only intercepts Claude's **direct** tool calls (Write, Edit, NotebookEdit)

2. **Bash Tool Opacity**: When Claude uses Bash tool:
   ```bash
   # These commands bypass hook validation:
   python test.py > output.txt        # Script creates file
   echo "test" > file.txt             # Shell redirect creates file
   pytest -v > test_results.log       # Test runner creates file
   ```

3. **Native File I/O**: Scripts use Python's `open()` or shell redirects, which operate **outside** Claude's tool system

### How Files Were Created

```python
# Example: A test script Claude ran via Bash tool
def run_tests():
    # This write bypasses pre_tool_use.py completely
    with open('test_results.log', 'w') as f:  # ❌ Not intercepted
        f.write(results)
```

## Impact Assessment

### Security Impact: **Medium**
- Files can accumulate in root directory
- Project structure becomes cluttered
- Hard to enforce organizational standards
- Test/debug files mixed with production files

### Workarounds Currently Used: **Manual Cleanup**
- Periodic manual review of root directory
- Moving files to appropriate locations after creation
- Git ignore patterns to hide unauthorized files

## Attempted Solutions (Why They Don't Work)

### ❌ Solution 1: Extend pre_tool_use.py to check Bash commands
**Problem**: Cannot parse all possible file creation patterns:
- Shell redirects: `>`, `>>`, `2>&1`
- Script outputs: Unknown what scripts will do
- Subshells and pipes: Too complex to analyze

### ❌ Solution 2: Modify post_tool_use.py to cleanup
**Problem**: Files already exist by the time hook runs (too late)

### ❌ Solution 3: Sandbox Bash execution
**Problem**: Would break legitimate development workflows

## Recommended Solutions

### ✅ Solution A: Bash Command Validation (Implemented)

Add pattern matching in `pre_tool_use.py` to detect and block dangerous Bash patterns:

```python
class BashCommandValidator(Validator):
    """Validates Bash commands for file creation attempts."""

    DANGEROUS_PATTERNS = [
        r'>\s*[^/]',              # Redirect to root file
        r'>>\s*[^/]',             # Append to root file
        r'echo.*>\s*[^/]',        # Echo redirect to root
        r'cat.*>\s*[^/]',         # Cat redirect to root
        r'python.*>\s*[^/]',      # Python output to root
        r'pytest.*>\s*[^/]',      # Pytest output to root
    ]

    def validate(self, tool_name: str, tool_input: Dict) -> Tuple[bool, Optional[str]]:
        if tool_name != 'Bash':
            return True, None

        command = tool_input.get('command', '')

        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return False, f"Blocked: Bash command attempts to create file in root directory"

        return True, None
```

**Pros**:
- Catches common file creation patterns
- Non-intrusive to legitimate commands
- Easy to extend with more patterns

**Cons**:
- Cannot catch all possible patterns (complex scripts)
- May have false positives
- Scripts can still create files internally

### ✅ Solution B: Test Output Redirection (Recommended)

Configure test runners and scripts to output to designated directories:

```python
# In test configuration (pytest.ini, pyproject.toml):
[tool.pytest.ini_options]
log_file = "logs/test_results.log"
junit_family = "xunit2"
```

```bash
# In shell scripts:
OUTPUT_DIR="logs/test_output"
mkdir -p "$OUTPUT_DIR"
python test.py > "$OUTPUT_DIR/results.txt"
```

**Pros**:
- Addresses root cause (improper output configuration)
- Works for all file types
- Maintainable and clear

**Cons**:
- Requires updating existing scripts
- Developers must remember to use proper paths

### ✅ Solution C: Post-Execution Monitoring (Detective Control)

Add a periodic check that alerts when unauthorized files appear:

```python
# In post_tool_use.py or separate monitor:
def check_root_files():
    """Alert on unauthorized files in project root."""
    allowed_files = load_allowed_files()
    actual_files = list(PROJECT_ROOT.glob('*'))

    unauthorized = [
        f for f in actual_files
        if f.is_file() and f.name not in allowed_files
    ]

    if unauthorized:
        print(f"⚠️  Warning: {len(unauthorized)} unauthorized files in root:")
        for f in unauthorized:
            print(f"   - {f.name}")
```

**Pros**:
- Catches all bypass methods
- Provides visibility
- Non-blocking (doesn't break workflows)

**Cons**:
- Reactive, not preventive
- Requires manual cleanup
- Files exist before detection

## Implementation Status

### ✅ Completed
- [x] Documented the issue
- [x] Moved 21 unauthorized files to `logs/legacy_test_files/`
- [x] Verified allowed files remain in root

### 🔄 Recommended Next Steps
1. Implement Bash command validation (Solution A) - Partial protection
2. Update test configurations to redirect output (Solution B) - Primary fix
3. Add post-execution monitoring (Solution C) - Detective control
4. Document proper file creation patterns in CLAUDE.md

## Testing Verification

### Test Case 1: Bash Redirect to Root
```bash
# Should be BLOCKED:
echo "test" > test_file.txt

# Expected: Hook blocks with error message
```

### Test Case 2: Bash Redirect to Logs
```bash
# Should be ALLOWED:
echo "test" > logs/test_file.txt

# Expected: Hook allows, file created in logs/
```

### Test Case 3: Script Output Redirect
```bash
# Should be BLOCKED:
python test.py > output.txt

# Expected: Hook detects pattern and blocks
```

### Test Case 4: Test Runner Output
```bash
# Should be CONFIGURED to use logs/:
pytest -v --log-file=logs/test.log

# Expected: Output goes to logs/, not root
```

## Conclusion

The file protection system works correctly for **direct** file operations via Claude's tools, but has an **architectural limitation** for operations performed by Bash commands and scripts.

**The best solution is a layered approach**:
1. **Preventive**: Bash command validation (catches common patterns)
2. **Corrective**: Test configuration updates (fixes root cause)
3. **Detective**: Post-execution monitoring (catches remaining cases)

This provides defense-in-depth while maintaining development workflow flexibility.

## References

- Configuration: `.claude/hooks/config/__claude_hook__allowed_root_files`
- Pre-tool hook: `.claude/hooks/pre_tool_use.py`
- Post-tool hook: `.claude/hooks/post_tool_use.py`
- Cleanup location: `logs/legacy_test_files/`

## Related Issues

- DOCS-PROTECTION-001: Documentation enforcement system
- ENV-PROTECTION-001: Environment file access protection