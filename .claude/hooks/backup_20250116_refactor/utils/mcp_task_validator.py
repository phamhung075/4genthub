#!/usr/bin/env python3
"""
MCP Task Lifecycle Validator - Ensures proper task management workflow.

This module validates and provides hints for:
1. Task lifecycle (create → update → complete)
2. Context management throughout workflow
3. Subtask decomposition for complex work
4. Progress tracking and transparency
5. Common mistakes and how to avoid them
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class MCPTaskValidator:
    """Validates MCP task operations and provides lifecycle hints."""
    
    def __init__(self):
        self.task_cache_file = Path.cwd() / '.claude' / 'hooks' / 'data' / 'mcp_tasks.json'
        self.task_cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_task_cache()
    
    def load_task_cache(self):
        """Load cached task states from file."""
        if self.task_cache_file.exists():
            try:
                with open(self.task_cache_file, 'r') as f:
                    self.task_cache = json.load(f)
            except:
                self.task_cache = {}
        else:
            self.task_cache = {}
    
    def save_task_cache(self):
        """Save task cache to file."""
        with open(self.task_cache_file, 'w') as f:
            json.dump(self.task_cache, f, indent=2)
    
    def validate_task_operation(self, tool_name: str, tool_input: Dict) -> Optional[str]:
        """
        Validate MCP task operations and generate hints.
        
        Returns:
            Optional[str]: Hint message to inject, or None if no hint needed
        """
        if not tool_name.startswith('mcp__dhafnck_mcp_http__manage'):
            return None
        
        hints = []
        
        # Check for task management operations
        if 'manage_task' in tool_name:
            action = tool_input.get('action', '')
            task_id = tool_input.get('task_id', '')
            
            if action == 'create':
                hints.append(self._hint_task_creation(tool_input))
                
            elif action == 'update':
                hints.append(self._hint_task_update(task_id, tool_input))
                
            elif action == 'complete':
                hints.append(self._hint_task_completion(task_id, tool_input))
                
            elif action == 'get' or action == 'list':
                hints.append(self._hint_task_review(task_id))
        
        # Check for subtask operations
        elif 'manage_subtask' in tool_name:
            action = tool_input.get('action', '')
            parent_id = tool_input.get('task_id', '')
            
            if action == 'create':
                hints.append(self._hint_subtask_creation(parent_id, tool_input))
                
            elif action == 'complete':
                hints.append(self._hint_subtask_completion(parent_id, tool_input))
        
        # Check for context operations
        elif 'manage_context' in tool_name:
            action = tool_input.get('action', '')
            
            if action == 'update':
                hints.append(self._hint_context_update(tool_input))
        
        # Filter out None hints and join
        valid_hints = [h for h in hints if h]
        if valid_hints:
            return "\n\n".join(valid_hints)
        
        return None
    
    def _hint_task_creation(self, tool_input: Dict) -> Optional[str]:
        """Generate hints for task creation."""
        hints = []
        
        # Check for missing critical fields
        if not tool_input.get('details'):
            hints.append("⚠️ REMINDER: Include detailed 'details' field with full requirements and context")
        
        if not tool_input.get('assignees'):
            hints.append("⚠️ REMINDER: Tasks MUST have at least one assignee (e.g., 'coding-agent')")
        
        if not tool_input.get('git_branch_id'):
            hints.append("⚠️ REMINDER: Include 'git_branch_id' for proper task organization")
        
        # Suggest decomposition for complex titles
        title = tool_input.get('title', '')
        if any(word in title.lower() for word in ['implement', 'build', 'create system', 'full']):
            hints.append("💡 HINT: Consider breaking this into subtasks for better management")
        
        if hints:
            return "🎯 TASK CREATION HINTS:\n" + "\n".join(hints)
        
        # Cache the new task
        if tool_input.get('title'):
            task_key = f"temp_{datetime.now().isoformat()}"
            self.task_cache[task_key] = {
                'status': 'created',
                'title': tool_input.get('title'),
                'created_at': datetime.now().isoformat(),
                'last_update': None
            }
            self.save_task_cache()
        
        return None
    
    def _hint_task_update(self, task_id: str, tool_input: Dict) -> Optional[str]:
        """Generate hints for task updates."""
        hints = []
        
        # Check if task exists in cache
        if task_id in self.task_cache:
            task_data = self.task_cache[task_id]
            
            # Check time since last update
            if task_data.get('last_update'):
                last_update = datetime.fromisoformat(task_data['last_update'])
                time_diff = datetime.now() - last_update
                
                if time_diff > timedelta(hours=1):
                    hints.append("⏰ REMINDER: It's been over an hour since last update")
            
            # Update cache
            task_data['last_update'] = datetime.now().isoformat()
            task_data['status'] = tool_input.get('status', task_data.get('status', 'in_progress'))
            self.save_task_cache()
        
        # Check for progress tracking
        if not tool_input.get('progress_notes') and not tool_input.get('details'):
            hints.append("📝 REMINDER: Include 'progress_notes' to track what you've done")
        
        # Suggest progress percentage
        if 'progress_percentage' not in tool_input and 'status' in tool_input:
            status = tool_input['status']
            if status == 'in_progress':
                hints.append("💡 HINT: Consider adding 'progress_percentage' (0-100) for better tracking")
        
        if hints:
            return "📊 TASK UPDATE HINTS:\n" + "\n".join(hints)
        
        return None
    
    def _hint_task_completion(self, task_id: str, tool_input: Dict) -> Optional[str]:
        """Generate hints for task completion."""
        hints = []
        
        # Critical reminders for completion
        if not tool_input.get('completion_summary'):
            hints.append("🚨 CRITICAL: Add 'completion_summary' with detailed accomplishments")
        
        if not tool_input.get('testing_notes'):
            hints.append("🔍 REMINDER: Include 'testing_notes' about verification performed")
        
        # Check if task has subtasks that should be completed
        if task_id in self.task_cache:
            task_data = self.task_cache[task_id]
            
            # Check if task was updated recently
            if not task_data.get('last_update'):
                hints.append("⚠️ WARNING: Completing task without any progress updates")
            
            # Mark as completed in cache
            task_data['status'] = 'completed'
            task_data['completed_at'] = datetime.now().isoformat()
            self.save_task_cache()
        
        # Remind about context preservation
        hints.append("💾 REMINDER: Update context with learnings before completion")
        
        if hints:
            return "✅ TASK COMPLETION CHECKLIST:\n" + "\n".join(hints)
        
        return None
    
    def _hint_subtask_creation(self, parent_id: str, tool_input: Dict) -> Optional[str]:
        """Generate hints for subtask creation."""
        hints = []
        
        # Suggest inheriting assignees
        if not tool_input.get('assignees'):
            hints.append("💡 HINT: Subtasks auto-inherit parent's assignees if not specified")
        
        # Suggest progress tracking
        hints.append("📈 TIP: Use 'progress_percentage' for automatic status mapping")
        
        return "📋 SUBTASK HINTS:\n" + "\n".join(hints) if hints else None
    
    def _hint_subtask_completion(self, parent_id: str, tool_input: Dict) -> Optional[str]:
        """Generate hints for subtask completion."""
        hints = []
        
        if not tool_input.get('completion_summary'):
            hints.append("📝 REQUIRED: Add 'completion_summary' for subtask")
        
        if not tool_input.get('impact_on_parent'):
            hints.append("🔗 REMINDER: Describe 'impact_on_parent' task")
        
        if tool_input.get('insights_found'):
            hints.append("✨ EXCELLENT: Sharing insights for future work!")
        
        return "✔️ SUBTASK COMPLETION:\n" + "\n".join(hints) if hints else None
    
    def _hint_context_update(self, tool_input: Dict) -> Optional[str]:
        """Generate hints for context updates."""
        hints = []
        
        level = tool_input.get('level', '')
        
        if level == 'task':
            hints.append("📌 REMINDER: Task context should include progress and discoveries")
        elif level == 'branch':
            hints.append("🌿 TIP: Branch context affects all tasks in this branch")
        elif level == 'project':
            hints.append("🏗️ NOTE: Project context is shared across all branches")
        
        return "🔄 CONTEXT UPDATE:\n" + "\n".join(hints) if hints else None
    
    def _hint_task_review(self, task_id: str) -> Optional[str]:
        """Generate hints when reviewing tasks."""
        if task_id and task_id in self.task_cache:
            task_data = self.task_cache[task_id]
            
            if task_data.get('status') == 'in_progress':
                last_update = task_data.get('last_update')
                if last_update:
                    time_diff = datetime.now() - datetime.fromisoformat(last_update)
                    if time_diff > timedelta(minutes=30):
                        return "⏰ REMINDER: Task in progress - consider updating with current status"
        
        return None
    
    def get_workflow_reminder(self, tool_name: str) -> Optional[str]:
        """Get general workflow reminders based on tool usage patterns."""
        if 'manage_task' in tool_name:
            return """
🔄 MCP TASK LIFECYCLE REMINDER:
1. CREATE with full context → Store once
2. UPDATE regularly (every 25%) → Show progress  
3. COMPLETE with summary → Preserve knowledge
4. Use task_id for references → Save tokens

Remember: Transparency > Speed | Understanding > Completion
"""
        return None


def inject_mcp_hints(tool_name: str, tool_input: Dict) -> Optional[str]:
    """
    Main entry point for MCP task hint injection.
    
    Args:
        tool_name: Name of the tool being called
        tool_input: Parameters passed to the tool
        
    Returns:
        Optional[str]: Hint message to inject as system reminder
    """
    if not tool_name.startswith('mcp__dhafnck_mcp_http'):
        return None
    
    validator = MCPTaskValidator()
    
    # Get specific operation hints
    operation_hints = validator.validate_task_operation(tool_name, tool_input)
    
    # Get general workflow reminder (less frequently)
    import random
    workflow_reminder = None
    if random.random() < 0.1:  # 10% chance to show general reminder
        workflow_reminder = validator.get_workflow_reminder(tool_name)
    
    # Combine hints
    hints = []
    if operation_hints:
        hints.append(operation_hints)
    if workflow_reminder:
        hints.append(workflow_reminder)
    
    if hints:
        return "<system-reminder>\n" + "\n\n".join(hints) + "\n</system-reminder>"
    
    return None


if __name__ == "__main__":
    # Test the validator
    test_cases = [
        {
            "tool_name": "mcp__dhafnck_mcp_http__manage_task",
            "tool_input": {
                "action": "create",
                "title": "Implement authentication system",
                "details": ""  # Missing details
            }
        },
        {
            "tool_name": "mcp__dhafnck_mcp_http__manage_task",
            "tool_input": {
                "action": "complete",
                "task_id": "task_123"
                # Missing completion_summary
            }
        },
        {
            "tool_name": "mcp__dhafnck_mcp_http__manage_subtask",
            "tool_input": {
                "action": "create",
                "task_id": "parent_123",
                "title": "Design database schema"
            }
        }
    ]
    
    for test in test_cases:
        hint = inject_mcp_hints(test["tool_name"], test["tool_input"])
        if hint:
            print(f"Tool: {test['tool_name']}")
            print(f"Action: {test['tool_input'].get('action')}")
            print(hint)
            print("-" * 50)