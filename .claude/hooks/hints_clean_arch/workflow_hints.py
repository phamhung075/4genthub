"""
Workflow hint provider - Single Responsibility: Track workflow state and provide hints.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from ..core.base import HintProvider


class WorkflowHintProvider(HintProvider):
    """Tracks workflow state and provides contextual hints."""
    
    def __init__(self):
        self.task_states = {}  # task_id -> {'status', 'last_update', 'created_at'}
        self.agent_loaded = None
        self.last_tool_use = None
    
    def get_hints(self, data: Dict[str, Any]) -> Optional[List[str]]:
        """Generate workflow-based hints."""
        tool_name = data.get('tool_name', '')
        tool_input = data.get('tool_input', {})
        hints = []
        
        # Track workflow state
        self._update_state(tool_name, tool_input)
        
        # Generate state-based hints
        if tool_name == 'mcp__dhafnck_mcp_http__manage_task':
            action = tool_input.get('action', '')
            task_id = tool_input.get('task_id', '')
            
            if action == 'create':
                hints.append("🔄 WORKFLOW: Task created, delegate to appropriate agent")
            
            elif action == 'update' and task_id in self.task_states:
                last_update = self.task_states[task_id].get('last_update')
                if last_update:
                    time_since = datetime.now() - last_update
                    if time_since > timedelta(minutes=30):
                        hints.append("⏰ REMINDER: Task hasn't been updated in 30+ minutes")
            
            elif action == 'complete':
                # Check if there are incomplete subtasks
                hints.append("🔍 CHECK: Ensure all subtasks are complete")
        
        # Agent coordination hints
        if tool_name == 'mcp__dhafnck_mcp_http__call_agent':
            if self.agent_loaded:
                hints.append(f"⚠️ WARNING: Agent already loaded: {self.agent_loaded}")
            else:
                agent_name = tool_input.get('name_agent', 'unknown')
                self.agent_loaded = agent_name
                hints.append(f"✅ LOADED: {agent_name} ready for work")
        
        # General workflow hints
        if self.last_tool_use:
            time_since_last = datetime.now() - self.last_tool_use
            if time_since_last > timedelta(minutes=10):
                hints.append("💡 TIP: Consider saving progress if working on complex task")
        
        self.last_tool_use = datetime.now()
        
        return hints if hints else None
    
    def _update_state(self, tool_name: str, tool_input: Dict[str, Any]):
        """Update internal workflow state."""
        if tool_name == 'mcp__dhafnck_mcp_http__manage_task':
            action = tool_input.get('action', '')
            task_id = tool_input.get('task_id', '')
            
            if action == 'create' and 'task' in tool_input:
                task_id = tool_input['task'].get('id', '')
                if task_id:
                    self.task_states[task_id] = {
                        'status': 'created',
                        'created_at': datetime.now(),
                        'last_update': datetime.now()
                    }
            
            elif action == 'update' and task_id:
                if task_id not in self.task_states:
                    self.task_states[task_id] = {}
                self.task_states[task_id]['status'] = tool_input.get('status', 'in_progress')
                self.task_states[task_id]['last_update'] = datetime.now()
            
            elif action == 'complete' and task_id:
                if task_id in self.task_states:
                    self.task_states[task_id]['status'] = 'completed'
                    self.task_states[task_id]['last_update'] = datetime.now()