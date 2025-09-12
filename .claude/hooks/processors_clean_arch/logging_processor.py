"""
Logging processor - Single Responsibility: Log operations.
"""
from typing import Dict, Any
from datetime import datetime
from ..core.base import Processor
from ..core.logger import Logger
from ..core.config import get_config


class LoggingProcessor(Processor):
    """Handles logging of hook operations."""
    
    def __init__(self, log_name: str = 'hook_operations'):
        self.config = get_config()
        self.logger = Logger(log_name, self.config.logs_dir)
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Log operation details."""
        tool_name = data.get('tool_name', 'unknown')
        tool_input = data.get('tool_input', {})
        
        # Create log entry
        log_data = {
            'tool_name': tool_name,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add relevant details based on tool
        if tool_name.startswith('mcp__'):
            log_data['action'] = tool_input.get('action', 'default')
            log_data['mcp_operation'] = True
            
            # Log key fields
            if 'task_id' in tool_input:
                log_data['task_id'] = tool_input['task_id']
            if 'title' in tool_input:
                log_data['title'] = tool_input['title'][:100]  # Truncate long titles
        
        elif tool_name in ['Write', 'Edit', 'MultiEdit']:
            log_data['file_path'] = tool_input.get('file_path', '')
            log_data['file_operation'] = True
        
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            log_data['command'] = command[:200]  # Truncate long commands
            log_data['bash_operation'] = True
        
        # Log the operation
        self.logger.info(f"Tool operation: {tool_name}", log_data)
        
        # Add log reference to data for other processors
        data['logged'] = True
        data['log_timestamp'] = log_data['timestamp']
        
        return data