# MCP Simple Wrapper Design
## Making MCP Usage Effortless

## 🎯 Design Goals

1. **One-function simplicity** - Primary function that handles 90% of cases
2. **Auto-detection** - Automatically detect context (project, branch, user)
3. **Sensible defaults** - Everything optional except description
4. **Session awareness** - Track work sessions, not micro-actions
5. **Zero friction** - Easier to use than not to use

## 🏗️ Core API Design

### Primary Function: `track_work()`

```python
def track_work(
    description: str,
    work_type: str = "task",
    auto_complete: bool = True,
    details: str = None
) -> str:
    """
    Single function to track any meaningful work.
    
    Args:
        description: What you're doing (required)
        work_type: Type of work (task|feature|fix|refactor)
        auto_complete: Auto-complete when session ends
        details: Additional context (optional)
    
    Returns:
        task_id: Simple reference for updates
    
    Examples:
        track_work("Fix authentication bug")
        track_work("Add user dashboard", work_type="feature")
        track_work("Investigate performance issue", auto_complete=False)
    """
    # Implementation below
```

### Supporting Functions

```python
def update_work(message: str, task_id: str = None) -> None:
    """
    Add progress update to current or specified task.
    
    Args:
        message: Progress update
        task_id: Optional task ID (uses current if not provided)
    
    Examples:
        update_work("Found the issue in auth.js")
        update_work("Applied fix", task_id="task_123")
    """

def complete_work(summary: str = None, task_id: str = None) -> None:
    """
    Mark work as complete.
    
    Args:
        summary: Completion summary (auto-generated if not provided)
        task_id: Optional task ID (uses current if not provided)
    
    Examples:
        complete_work("Fixed null check issue")
        complete_work()  # Auto-generates summary
    """
```

## 📦 Implementation Details

### Context Auto-Detection

```python
class ContextDetector:
    """Automatically detects MCP context"""
    
    @staticmethod
    def get_current_context():
        """Get all required MCP context automatically"""
        
        context = {
            'user_id': os.environ.get('USER_ID') or detect_user(),
            'project_id': cache.get('project_id') or detect_project(),
            'git_branch_id': cache.get('branch_id') or detect_branch(),
            'assignee': '@claude'  # Default self-assignment
        }
        
        return context
    
    @staticmethod
    def detect_project():
        """Detect or create project from git repo"""
        # Check git remote origin
        # Hash to create stable project_id
        # Cache for session
        
    @staticmethod  
    def detect_branch():
        """Detect or create branch from git branch"""
        # Get current git branch
        # Create MCP branch if needed
        # Cache for session
```

### Session Management

```python
class SessionTracker:
    """Tracks work sessions to avoid micro-task creation"""
    
    def __init__(self):
        self.current_task = None
        self.action_count = 0
        self.start_time = None
        self.auto_complete = True
    
    def track(self, description, work_type="task", **kwargs):
        """Track work, creating task only if needed"""
        
        if self.should_create_new_task(description):
            # Complete previous task if exists
            if self.current_task:
                self.complete_current()
            
            # Create new task
            self.current_task = self.create_task(description, work_type)
            self.start_time = time.now()
            
        return self.current_task
    
    def should_create_new_task(self, description):
        """Determine if new task needed"""
        
        # New task if:
        # - No current task
        # - Different work type
        # - Significant time gap (> 30 min)
        # - Explicit new work description
        
        if not self.current_task:
            return True
            
        if time.now() - self.start_time > timedelta(minutes=30):
            return True
            
        if is_significantly_different(description, self.current_task.description):
            return True
            
        return False
```

### Intelligent Defaults

```python
class SmartDefaults:
    """Provides intelligent defaults based on context"""
    
    @staticmethod
    def infer_work_type(description):
        """Infer work type from description"""
        
        patterns = {
            'fix': ['fix', 'bug', 'issue', 'error', 'problem'],
            'feature': ['add', 'implement', 'create', 'new'],
            'refactor': ['refactor', 'improve', 'optimize', 'clean'],
            'task': []  # Default
        }
        
        description_lower = description.lower()
        
        for work_type, keywords in patterns.items():
            if any(keyword in description_lower for keyword in keywords):
                return work_type
        
        return 'task'
    
    @staticmethod
    def generate_summary(task, actions):
        """Auto-generate completion summary"""
        
        # Analyze actions taken
        files_modified = extract_modified_files(actions)
        changes_made = summarize_changes(actions)
        
        summary = f"Completed: {task.description}"
        
        if files_modified:
            summary += f" - Modified {len(files_modified)} files"
        
        if changes_made:
            summary += f" - {changes_made}"
        
        return summary
```

## 🔧 Simple Wrapper Implementation

```python
# mcp_simple.py - The complete simple wrapper

import os
import time
from typing import Optional

# Global session tracker
_session = SessionTracker()

def track_work(
    description: str,
    work_type: Optional[str] = None,
    auto_complete: bool = True,
    details: Optional[str] = None
) -> str:
    """Track any meaningful work with one function"""
    
    # Infer work type if not provided
    if not work_type:
        work_type = SmartDefaults.infer_work_type(description)
    
    # Get or create task
    task_id = _session.track(
        description=description,
        work_type=work_type,
        auto_complete=auto_complete,
        details=details
    )
    
    return task_id

def update_work(message: str, task_id: Optional[str] = None) -> None:
    """Add progress update"""
    
    task_id = task_id or _session.current_task
    
    if not task_id:
        return  # No task to update
    
    try:
        mcp__dhafnck_mcp_http__manage_task(
            action="update",
            task_id=task_id,
            details=append_to_details(message)
        )
    except:
        pass  # Fail silently

def complete_work(summary: Optional[str] = None, task_id: Optional[str] = None) -> None:
    """Mark work complete"""
    
    task_id = task_id or _session.current_task
    
    if not task_id:
        return  # No task to complete
    
    if not summary:
        summary = SmartDefaults.generate_summary(task_id, _session.actions)
    
    try:
        mcp__dhafnck_mcp_http__manage_task(
            action="complete",
            task_id=task_id,
            completion_summary=summary
        )
        
        if task_id == _session.current_task:
            _session.current_task = None
    except:
        pass  # Fail silently

# Auto-cleanup on session end
import atexit
atexit.register(lambda: complete_work() if _session.current_task else None)
```

## 🎯 Usage Examples

### Simple Cases

```python
# Basic tracking
track_work("Fix login bug")
# ... do work ...
complete_work("Fixed null check in auth.js")

# Auto-detection
track_work("Add user dashboard")  # Detects as 'feature'
# ... do work ...
# Auto-completes on session end

# With progress updates
task = track_work("Refactor database module")
update_work("Analyzing current structure")
update_work("Applying new pattern")
complete_work("Refactored to repository pattern")
```

### Natural Integration

```python
# In Claude's workflow
def handle_user_request(request):
    # Track if meaningful
    if is_meaningful_work(request):
        track_work(request)
    
    # Do the actual work
    perform_work()
    
    # Auto-completes on session end
```

## 📊 Granularity Rules

### Track These (Meaningful Work)

```python
TRACK_PATTERNS = {
    'feature': lambda desc, stats: stats['lines_added'] > 50,
    'fix': lambda desc, stats: 'bug' in desc.lower() or 'fix' in desc.lower(),
    'refactor': lambda desc, stats: stats['files_modified'] > 2,
    'investigation': lambda desc, stats: stats['time_spent'] > 300,  # 5 minutes
    'explicit': lambda desc, stats: any(word in desc.lower() for word in ['track', 'task', 'ticket'])
}
```

### Skip These (Trivial Operations)

```python
SKIP_PATTERNS = {
    'reading': lambda action: action.tool == 'Read',
    'status': lambda action: action.tool == 'Bash' and action.command in ['ls', 'pwd', 'git status'],
    'micro_edit': lambda action: action.lines_changed < 5,
    'formatting': lambda action: action.is_formatting_only(),
    'quick': lambda desc: desc.lower().startswith(('just', 'quick', 'check'))
}
```

## 🚀 Integration Strategy

### Phase 1: Core Implementation
1. Implement `track_work()` function
2. Test with manual calls
3. Verify auto-detection works

### Phase 2: Hook Integration
```python
# In pre_tool_use hook
if is_meaningful_action(tool, params):
    if not session.has_task():
        track_work(f"Working on {extract_description(params)}")
```

### Phase 3: Natural Language
```python
# Detect from user message
if should_track_from_message(user_message):
    track_work(extract_task_description(user_message))
```

## 💡 Why This Works

### 1. Extreme Simplicity
- One function to remember
- Everything else is optional
- Auto-detection handles complexity

### 2. Natural Flow
- Tracks sessions, not micro-actions
- Auto-completes on session end
- Fails silently (doesn't break workflow)

### 3. Intelligent Behavior
- Infers work type from description
- Generates summaries automatically
- Detects context without asking

### 4. Zero Friction
- Easier to use than not to use
- No complex parameters
- No UUID management

## 📝 Summary

The simple wrapper reduces MCP from 10+ complex functions to:

```python
track_work("What you're doing")  # That's it
```

Everything else is automated, inferred, or optional. This makes MCP usage natural rather than forced.