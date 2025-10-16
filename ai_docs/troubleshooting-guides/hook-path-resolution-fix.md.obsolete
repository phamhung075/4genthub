# Hook Path Resolution Fix for Subdirectories

## Problem

Claude Code invokes hooks using relative paths from the current working directory. When working in subdirectories like `agenthub-frontend`, the hook invocation fails with:

```
Error: Bash operation blocked by hook:
- [python3 ./.claude/hooks/pre_tool_use.py]: python3: can't open file '/home/daihungpham/__projects__/4genthub/agenthub-frontend/./.claude/hooks/pre_tool_use.py': [Errno 2] No such file or directory
```

The issue occurs because:
1. Claude Code looks for `./.claude/hooks/pre_tool_use.py` relative to the current working directory
2. When working in `agenthub-frontend/`, this resolves to `agenthub-frontend/.claude/hooks/pre_tool_use.py`
3. But the hook only exists at the project root: `/path/to/project/.claude/hooks/pre_tool_use.py`

## Solution: Hook Proxy System

The solution is to create lightweight hook proxy files in subdirectories that delegate to the main hook at the project root.

### Implementation

#### 1. Hook Proxy Files

Created proxy files in `agenthub-frontend/.claude/hooks/`:
- `pre_tool_use.py` - Proxy for the pre-tool hook
- `post_tool_use.py` - Proxy for the post-tool hook

Each proxy:
1. Finds the project root by looking for `CLAUDE.md` file
2. Locates the real hook at the project root
3. Executes it with all original arguments
4. Preserves exit codes and output

#### 2. Proxy Logic

```python
def find_project_root(start_path=None):
    """Find project root by looking for CLAUDE.md file."""
    current = Path(start_path or os.getcwd()).resolve()
    while current != current.parent:
        if (current / 'CLAUDE.md').exists():
            return current
        current = current.parent
    return None

def main():
    """Locate and execute the real hook."""
    project_root = find_project_root()
    real_hook_path = project_root / '.claude' / 'hooks' / 'pre_tool_use.py'
    result = subprocess.run([sys.executable, str(real_hook_path)] + sys.argv[1:])
    sys.exit(result.returncode)
```

### Tools Created

#### 1. Hook Proxy Creator (`scripts/create_hook_proxies.py`)

Automates creation of hook proxies for any subdirectory:

```bash
# Create proxies in default locations (agenthub-frontend)
python scripts/create_hook_proxies.py

# Create proxies in specific directory
python scripts/create_hook_proxies.py path/to/subdirectory
```

#### 2. Hook Proxy Tester (`scripts/test_hook_proxies.py`)

Tests that hook proxies work correctly:

```bash
python scripts/test_hook_proxies.py
```

### Verification

```bash
# Test from frontend directory
cd agenthub-frontend
python3 ./.claude/hooks/pre_tool_use.py --help  # Should work now

# Run comprehensive tests
python scripts/test_hook_proxies.py
```

## Benefits

1. **Minimal Impact**: Only adds small proxy files in subdirectories
2. **Maintainable**: Main hook logic stays in one place at project root
3. **Scalable**: Can be applied to any subdirectory that needs it
4. **Robust**: Uses the same project root finding logic as the main hook
5. **Transparent**: Preserves all hook behavior, arguments, and exit codes

## Files Created

- `agenthub-frontend/.claude/hooks/pre_tool_use.py` - Pre-tool hook proxy
- `agenthub-frontend/.claude/hooks/post_tool_use.py` - Post-tool hook proxy
- `scripts/create_hook_proxies.py` - Tool to create proxies in new subdirectories
- `scripts/test_hook_proxies.py` - Tool to test proxy functionality

## Future Maintenance

When creating new subdirectories that Claude Code will work from:

1. Run the hook proxy creator:
   ```bash
   python scripts/create_hook_proxies.py path/to/new/subdirectory
   ```

2. Test the proxies:
   ```bash
   python scripts/test_hook_proxies.py
   ```

The main hook at the project root (`/.claude/hooks/pre_tool_use.py`) remains unchanged and continues to contain all the actual hook logic.