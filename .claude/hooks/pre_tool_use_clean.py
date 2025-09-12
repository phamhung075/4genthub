#!/usr/bin/env python3
"""
Clean, modular pre-tool use hook following SOLID principles.
"""
import json
import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import core components
from core import Config, Logger, HookException, ToolHook
from core.config import get_config

# Import validators
from validators import (
    FileValidator,
    PathValidator,
    CommandValidator,
    MCPValidator
)

# Import hint providers
from hints import (
    MCPHintProvider,
    FileHintProvider,
    WorkflowHintProvider
)

# Import processors
from processors import (
    HintStorageProcessor,
    LoggingProcessor
)


class PreToolUseHook(ToolHook):
    """Pre-tool use hook with clean architecture."""
    
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.logger = Logger('pre_tool_use', self.config.logs_dir)
        
        # Initialize components based on configuration
        self._setup_validators()
        self._setup_hint_providers()
        self._setup_processors()
    
    def _setup_validators(self):
        """Setup validators based on configuration."""
        if self.config.enable_file_protection:
            self.add_validator(FileValidator())
            self.add_validator(PathValidator())
            self.add_validator(CommandValidator())
        
        if self.config.enable_mcp_hints:
            self.add_validator(MCPValidator())
    
    def _setup_hint_providers(self):
        """Setup hint providers based on configuration."""
        if self.config.enable_mcp_hints:
            self.add_hint_provider(MCPHintProvider())
            self.add_hint_provider(WorkflowHintProvider())
        
        self.add_hint_provider(FileHintProvider())
    
    def _setup_processors(self):
        """Setup processors."""
        if self.config.enable_logging:
            self.add_processor(LoggingProcessor('pre_tool_use'))
        
        self.add_processor(HintStorageProcessor())
    
    def execute(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute the pre-tool use hook."""
        try:
            # Log the operation
            self.logger.info(f"Processing tool: {data.get('tool_name', 'unknown')}")
            
            # Run validation
            if not self.validate(data):
                # Get error messages from validators
                errors = []
                for validator in self.validators:
                    if hasattr(validator, 'error_message') and validator.error_message:
                        errors.append(validator.error_message)
                
                if errors:
                    # Block the operation
                    error_msg = '\n'.join(errors)
                    print(error_msg, file=sys.stderr)
                    self.logger.error("Validation failed", {'errors': errors})
                    sys.exit(1)
            
            # Process data (logging, etc.)
            data = self.process(data)
            
            # Get and display any pending hints from previous operations
            hint_processor = HintStorageProcessor()
            pending_hints = hint_processor.get_pending_hints()
            if pending_hints:
                print(pending_hints, file=sys.stderr)
            
            # Collect hints for current operation (pre-execution hints)
            hints = self.get_hints(data)
            if hints:
                hint_message = '\n'.join(hints)
                print(f"<system-reminder>\n{hint_message}\n</system-reminder>", file=sys.stderr)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Hook execution failed: {str(e)}")
            # Don't block on internal errors
            return data


def main():
    """Main entry point for pre-tool use hook."""
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
    hook = PreToolUseHook()
    result = hook.execute(data)
    
    # Output the original data (hooks don't modify input)
    print(json.dumps(data))


if __name__ == '__main__':
    main()