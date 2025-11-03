# Phase 2: System Hook Optimization Strategy

## Current Token Consumption Analysis

### session_start.py Analysis (2327 lines)

| Component | Lines | Est. Tokens | Issue |
|-----------|-------|-------------|-------|
| **Imports & Setup** | 53 | ~200 | Standard |
| **Abstract Classes** | 84 | ~400 | Overhead for simple operations |
| **Context Providers** | 1200+ | ~8,000 | Largest offender - loads everything |
| **Formatters** | 300+ | ~2,000 | Verbose output generation |
| **Backward Compatibility** | 200+ | ~1,000 | Legacy support |
| **Session Cleanup** | 130+ | ~800 | Process scanning overhead |
| **TOTAL** | 2327 | **~15,000** | 🔴 Excessive |

### Key Problems Identified

1. **Eager Loading**: All context providers load data immediately
   - Git status with full file list (23 files)
   - Full MCP project/branch resolution
   - Complete development environment scan
   - Infrastructure detection across multiple files

2. **Verbose Output**: Detailed formatting for every session
   - Multi-line git status
   - Full project context
   - Complete environment details
   - Infrastructure breakdown

3. **No Lazy Loading**: Everything runs even if not needed
   - MCP connection for every session
   - Docker compose file parsing
   - Package.json/pyproject.toml parsing
   - Session cleanup process scanning

---

## Optimization Strategy

### Goal: Reduce from ~15,000 to ~6,000 tokens (60% reduction)

---

## 1. Lazy Git Status (Save ~3,000 tokens)

### Current Behavior (Verbose)
```python
📁 Git Status: Branch '0.0.6-agents-base'
⚠️  23 uncommitted changes

Recent commits:
3b76b3c7 ai_docs: update CHANGELOG
9add0767 fix(backend): auto-generate share_token
f351bba7 test: add unit tests for facade
da9152f1 feat(frontend): enhance marketplace dialog
```
**Token cost**: ~3,000 tokens (23 files + 5 commits + formatting)

### Optimized Behavior (Summary)
```python
📁 Git: 0.0.6-agents-base (23 changes)
💡 Use /git_status for details
```
**Token cost**: ~150 tokens (95% reduction)

### Implementation

```python
class LazyGitContextProvider(ContextProvider):
    """Provides git summary with on-demand details."""

    def get_context(self, input_data: Dict) -> Optional[Dict[str, Any]]:
        """Get minimal git summary."""
        try:
            # Only get branch and change count
            branch_result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, timeout=2
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

            # Count changes only (don't list them)
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, timeout=2
            )
            change_count = len(status_result.stdout.strip().split('\n')) if status_result.returncode == 0 else 0

            return {
                'branch': branch,
                'change_count': change_count,
                'summary_only': True
            }
        except Exception:
            return {'branch': 'unknown', 'change_count': 0}
```

---

## 2. Conditional MCP Loading (Save ~2,500 tokens)

### Current Behavior (Always Load)
```python
🌐 MCP Server: http://localhost:8000/mcp
📁 Git project: Project '4genthub' : 'd53174db-637a-4c43-b528-3b673d1b894e'
📝 Git Branch: '0.0.6-agents-base' (not yet registered in MCP)
📋 No active tasks
```
**Token cost**: ~2,500 tokens (authentication + project query + branch query + task query)

### Optimized Behavior (Load on Demand)
```python
🌐 MCP: Ready (use /mcp_status for details)
```
**Token cost**: ~100 tokens (96% reduction)

### Implementation

```python
class ConditionalMCPProvider(ContextProvider):
    """Only loads MCP if explicitly needed."""

    def get_context(self, input_data: Dict) -> Optional[Dict[str, Any]]:
        """Check MCP availability without loading full context."""
        # Check if MCP tools were used in conversation
        conversation = input_data.get('conversation_history', [])
        mcp_needed = any('mcp__' in str(msg.get('content', '')) for msg in conversation[-5:])

        if not mcp_needed:
            # Just verify connection
            try:
                from utils.mcp_client import MCPHTTPClient
                client = MCPHTTPClient()
                if client.authenticate():
                    return {'status': 'ready', 'details_available': True}
            except:
                pass
            return {'status': 'unavailable'}

        # Full MCP context only when needed
        return self._load_full_mcp_context()
```

---

## 3. Compressed Environment Context (Save ~2,000 tokens)

### Current Behavior (Detailed)
```python
🔧 Development Environment:

📦 Frontend (agenthub-frontend/)
   • Framework: React 19.x + TypeScript 4.x
   • Build: Vite 7.x
   • UI: Tailwind CSS, shadcn/ui
   • Key files: package.json, vite.config.ts, tsconfig.json
   • Port: 3800

🐍 Backend (agenthub_main/)
   • Framework: FastMCP + FastAPI
   • Architecture: DDD (Domain-Driven Design)
   • Language: Python 3.14.0
   • ORM: SQLAlchemy
   • Key files: pyproject.toml
   • Port: 8000

🪝 Hook System (.claude/hooks/)
   • Type: Python-based enforcement
   • Pre-tool: File system protection
   • Post-tool: Documentation indexing
   • Session: 2-hour tracking
   • Key files: pre_tool_use.py, post_tool_use.py

🐳 Infrastructure:
   • Container: Docker + docker-compose
   • Database: PostgreSQL (Docker)
   • Auth: Keycloak
   • Config: .env, docker-system/docker-menu.sh
```
**Token cost**: ~2,000 tokens

### Optimized Behavior (Compact)
```python
🔧 Dev: React 19 + Python 3.14 | Ports: 3800, 8000
💡 Use /dev_env for full details
```
**Token cost**: ~100 tokens (95% reduction)

### Implementation

```python
class CompactEnvironmentProvider(ContextProvider):
    """Provides compact environment summary."""

    def get_context(self, input_data: Dict) -> Optional[Dict[str, Any]]:
        """Get minimal environment info."""
        try:
            project_root = get_project_root()

            # Detect only essential info
            info = {
                'frontend_exists': (project_root / 'agenthub-frontend').exists(),
                'backend_exists': (project_root / 'agenthub_main').exists(),
                'python_version': sys.version.split()[0],
                'compact_mode': True
            }

            # Quick version detection (no full parsing)
            package_json = project_root / 'agenthub-frontend' / 'package.json'
            if package_json.exists():
                try:
                    with open(package_json, 'r') as f:
                        data = json.load(f)
                        react_v = data.get('dependencies', {}).get('react', '')
                        info['react_version'] = react_v.split('.')[0].replace('^', '') if react_v else 'detected'
                except:
                    pass

            return info
        except:
            return None
```

---

## 4. Remove Session Cleanup Overhead (Save ~800 tokens)

### Current Behavior (Process Scanning)
```python
class ClaudeSessionCleanup:
    """130+ lines of process scanning code."""

    def find_claude_processes(self):
        """Scans all processes using psutil."""
        # Iterates through ALL system processes
        # Checks command lines
        # Calculates CPU usage
        # Tracks creation times
```
**Token cost**: ~800 tokens (entire class loaded)

### Optimized Behavior (Disabled by Default)
```python
# Only load if explicitly enabled
CLEANUP_ENABLED = os.getenv('CLAUDE_AUTO_CLEANUP', 'false').lower() == 'true'

if CLEANUP_ENABLED:
    from .session_cleanup import ClaudeSessionCleanup
    # ... cleanup logic
```
**Token cost**: ~50 tokens (98% reduction)

---

## 5. Simplified Output Formatting (Save ~1,000 tokens)

### Current Behavior (Multi-line Sections)
```python
class ContextFormatterProcessor:
    """300+ lines of detailed formatting logic."""

    def _format_context(self, context_data: Dict) -> str:
        """Complex nested formatting with emoji icons."""
        # Separate sections for each component
        # Multi-line breakdowns
        # Detailed lists
        # Icon prefixes
```
**Token cost**: ~1,000 tokens

### Optimized Behavior (Single-line Summaries)
```python
class CompactFormatter:
    """Minimal formatting with inline data."""

    def format(self, context: Dict) -> str:
        """Single-line summaries."""
        parts = []
        if context.get('git'):
            parts.append(f"Git: {context['git']['branch']} ({context['git']['change_count']} changes)")
        if context.get('mcp'):
            parts.append(f"MCP: {context['mcp']['status']}")
        return " | ".join(parts)
```
**Token cost**: ~200 tokens (80% reduction)

---

## Implementation Plan

### Step 1: Create Optimized Providers (1 hour)

```bash
# Create new optimized providers
.claude/hooks/providers/
├── lazy_git.py          # LazyGitContextProvider
├── conditional_mcp.py   # ConditionalMCPProvider
├── compact_env.py       # CompactEnvironmentProvider
└── simple_formatter.py  # CompactFormatter
```

### Step 2: Create Mode Switcher (30 min)

```python
# .claude/hooks/utils/context_mode.py

CONTEXT_MODE = os.getenv('CLAUDE_CONTEXT_MODE', 'compact')  # 'compact' or 'full'

def get_context_providers():
    """Return appropriate providers based on mode."""
    if CONTEXT_MODE == 'full':
        from providers.full import FullProviders
        return FullProviders()
    else:
        from providers.lazy import LazyProviders
        return LazyProviders()
```

### Step 3: Update session_start.py (30 min)

```python
# Minimal changes to existing file
from utils.context_mode import get_context_providers

class SessionStartHook:
    def __init__(self):
        # Use mode-based providers
        self.context_providers = get_context_providers()
        # Rest stays the same
```

### Step 4: Add Slash Commands (30 min)

```bash
# .claude/commands/git_status.md
Get detailed git status with file list

# .claude/commands/mcp_status.md
Get full MCP project, branch, and task context

# .claude/commands/dev_env.md
Get complete development environment details
```

---

## Expected Results

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| **Git Context** | 3,000 | 150 | 2,850 (95%) |
| **MCP Context** | 2,500 | 100 | 2,400 (96%) |
| **Dev Environment** | 2,000 | 100 | 1,900 (95%) |
| **Session Cleanup** | 800 | 50 | 750 (94%) |
| **Output Formatting** | 1,000 | 200 | 800 (80%) |
| **Other** | 5,700 | 5,400 | 300 (5%) |
| **TOTAL** | **15,000** | **6,000** | **9,000 (60%)** |

---

## Backward Compatibility

### Environment Variable Control

```bash
# Default (optimized)
CLAUDE_CONTEXT_MODE=compact  # Default, loads minimal context

# Full context (old behavior)
CLAUDE_CONTEXT_MODE=full  # Loads everything as before
```

### Slash Commands for On-Demand Details

```
/git_status    → Full git status with file list
/mcp_status    → Complete MCP context
/dev_env       → Full environment details
/all_context   → Everything (original behavior)
```

---

## Testing Strategy

### 1. Compare Token Usage

```python
# Before optimization
session_start_tokens = count_tokens(original_output)  # ~15,000

# After optimization
session_start_tokens = count_tokens(optimized_output)  # ~6,000

# Verify savings
assert session_start_tokens < 7000, "Optimization failed"
```

### 2. Verify Information Preserved

```python
# Ensure all critical information accessible
assert can_access_git_status()
assert can_access_mcp_context()
assert can_access_dev_environment()
```

### 3. Test Slash Commands

```bash
# Verify on-demand loading works
/git_status  → Should show full 23-file list
/mcp_status  → Should show complete project/branch/tasks
/dev_env     → Should show full 2000-token environment
```

---

## Rollback Plan

If optimization causes issues:

1. **Immediate Rollback**:
   ```bash
   export CLAUDE_CONTEXT_MODE=full
   # Returns to original behavior
   ```

2. **Selective Rollback**:
   ```bash
   export CLAUDE_LAZY_GIT=false       # Restore full git status
   export CLAUDE_LAZY_MCP=false       # Restore full MCP context
   export CLAUDE_COMPACT_ENV=false    # Restore full environment
   ```

3. **Complete Rollback**:
   ```bash
   git checkout .claude/hooks/session_start.py
   # Restores original file
   ```

---

## Next Steps

1. **Review this strategy** with the team
2. **Create providers/** directory with optimized implementations
3. **Test in development** environment
4. **Monitor token usage** after deployment
5. **Gather feedback** from users
6. **Iterate** based on results

---

## Additional Optimizations (Future)

### Phase 3: Smart Caching
- Cache git status for 30 seconds
- Cache MCP project/branch for 5 minutes
- Cache environment detection for session duration

### Phase 4: Progressive Loading
- Load immediately: Session ID only
- Load after 1s: Git summary
- Load after 2s: MCP summary (if needed)
- Load on demand: Full details via slash commands

### Phase 5: User Preferences
- Allow users to configure what they want at startup
- Save preferences in `.claude/user_preferences.json`
- Smart defaults based on usage patterns

---

## Conclusion

This optimization strategy reduces session start token consumption by **60% (15k → 6k tokens)** while:

✅ Preserving all information (accessible on demand)
✅ Maintaining backward compatibility (environment variable)
✅ Improving startup speed (less processing)
✅ Enabling user customization (preferences)
✅ Providing rollback options (safety net)

**Total Project Token Savings** (combined with Phase 1):
- CLAUDE.md: 20k saved
- System Hooks: 9k saved
- **Total: 29k tokens saved (44% reduction from 66k to 37k)**
