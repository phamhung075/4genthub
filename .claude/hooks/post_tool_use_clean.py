#!/usr/bin/env python3
"""
Clean, modular post-tool use hook following SOLID principles.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import core components
from core import Config, Logger, ToolHook
from core.config import get_config

# Import hint providers
from hints import (
    MCPHintProvider,
    WorkflowHintProvider
)

# Import processors
from processors import (
    HintStorageProcessor,
    LoggingProcessor
)


class PostToolUseHook(ToolHook):
    """Post-tool use hook with clean architecture."""
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.logger = Logger('post_tool_use', self.config.logs_dir)
        
        # Initialize components
        self._setup_hint_providers()
        self._setup_processors()
    
    def _setup_hint_providers(self):
        """Setup hint providers for post-execution."""
        if self.config.enable_mcp_hints:
            self.add_hint_provider(MCPHintProvider())
            self.add_hint_provider(WorkflowHintProvider())
    
    def _setup_processors(self):
        """Setup processors."""
        if self.config.enable_logging:
            self.add_processor(LoggingProcessor('post_tool_use'))
        
        self.add_processor(HintStorageProcessor())
    
    def execute(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute the post-tool use hook."""
        try:
            tool_name = data.get('tool_name', 'unknown')
            tool_input = data.get('tool_input', {})
            result = data.get('result', {})
            
            # Log the operation
            self.logger.info(f"Post-processing tool: {tool_name}")
            
            # Check if operation was successful
            is_success = self._check_success(result)
            
            if not is_success:
                self.logger.info(f"Operation failed, skipping hints for {tool_name}")
                return data
            
            # Process data (logging, etc.)
            data = self.process(data)
            
            # Generate hints based on the operation result
            hints = self.get_hints(data)
            
            if hints:
                # Format hints for storage
                hint_message = '\n'.join(hints)
                
                # Store hints for display in next pre_tool_use
                hint_processor = HintStorageProcessor()
                action = tool_input.get('action', 'default')
                hint_processor.store_hint(hint_message, tool_name, action)
                
                # Log hint generation
                self.logger.info(
                    f"Generated hints for {tool_name}:{action}",
                    {
                        'tool_name': tool_name,
                        'action': action,
                        'hint_preview': hint_message[:100]
                    }
                )
                
                # Also create detailed log entry
                self._log_detailed_hints(tool_name, tool_input, hint_message)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Hook execution failed: {str(e)}")
            # Don't block on internal errors
            return data
    
    def _check_success(self, result: Any) -> bool:
        """Check if the operation was successful."""
        if result and isinstance(result, dict):
            # Check for explicit success field
            if 'success' in result:
                return result['success']
            
            # Check for error indicators
            if 'error' in result or 'errors' in result:
                return False
        
        # Default to success if no error indicators
        return True
    
    def _log_detailed_hints(self, tool_name: str, tool_input: Dict, hint_message: str):
        """Create detailed hint log entry."""
        detailed_logger = Logger('mcp_post_hints_detailed', self.config.logs_dir)
        
        # Extract key fields for summary
        summary = {}
        for field in ['task_id', 'title', 'status', 'completion_summary']:
            if field in tool_input:
                value = tool_input[field]
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100]  # Truncate long strings
                summary[field] = value
            else:
                summary[field] = None
        
        detailed_logger.info(
            "Hint generated",
            {
                'tool_name': tool_name,
                'action': tool_input.get('action', 'default'),
                'tool_input_summary': summary,
                'hint_generated': hint_message,
                'hint_stored': True,
                'hint_displayed': False  # Will be displayed in next pre_tool_use
            }
        )


def main():
    """Main entry point for post-tool use hook."""
    # Read input
    input_line = sys.stdin.readline()
    if not input_line:
        return
    
    try:
        data = json.loads(input_line)
    except json.JSONDecodeError:
        # Invalid JSON, let it pass through
        print(input_line, end='')
        return
    
    # Create and execute hook
    hook = PostToolUseHook()
    result = hook.execute(data)
    
    # Output the original data (hooks don't modify input)
    print(json.dumps(data))


if __name__ == '__main__':
    main()