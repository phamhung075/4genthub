# Claude Hooks System - Clean Architecture Refactoring Design

## Executive Summary

This document provides the comprehensive architecture design for refactoring the .claude/hooks system from a complex 55-file structure to a clean, SOLID-principle-based architecture with approximately 15-20 focused files.

## Current State Analysis

### Issues Identified
- **Massive Complexity**: 55 Python files scattered across multiple directories
- **Monolithic Design**: pre_tool_use.py with 757 lines violating Single Responsibility Principle
- **Tight Coupling**: Direct imports and no interfaces (Dependency Inversion Principle violation)
- **Mixed Responsibilities**: Validation, logging, context injection in single files
- **Extension Difficulty**: Hard to add new validators (Open/Closed Principle violation)
- **No Abstraction**: Everything hardcoded, no factory pattern

### Current File Distribution
```
Current System: 55 Python files
├── Legacy monolithic files: pre_tool_use.py (757 lines), post_tool_use.py
├── Clean architecture (partial): core_clean_arch/, validators_clean_arch/, processors_clean_arch/
├── Scattered utilities: utils/ (25+ files)
├── Multiple entry points: pre_tool_use.py, pre_tool_use_clean.py
└── Duplicate implementations across directories
```

## Target Clean Architecture Design

### SOLID Principles Application

#### Single Responsibility Principle (SRP)
- **FileValidator**: Only handles file system validation
- **SecurityValidator**: Only handles security checks (.env protection, dangerous commands)
- **PathValidator**: Only handles path structure validation
- **ContextProcessor**: Only handles context injection
- **LoggingProcessor**: Only handles audit logging

#### Open/Closed Principle (OCP)
- **Factory Pattern**: Add new validators without modifying existing code
- **Interface-based Extension**: New components implement existing interfaces
- **Configuration-driven**: Enable/disable components without code changes

#### Liskov Substitution Principle (LSP)
- All validators implement `Validator` interface consistently
- All processors implement `Processor` interface consistently
- All hint providers implement `HintProvider` interface consistently

#### Interface Segregation Principle (ISP)
- **Validator Interface**: Only validation methods
- **Processor Interface**: Only processing methods  
- **HintProvider Interface**: Only hint generation methods
- No forced dependencies on unused methods

#### Dependency Inversion Principle (DIP)
- Main class depends on abstractions (interfaces), not concrete classes
- Factory creates concrete implementations
- Components receive dependencies through constructor injection

### Target Directory Structure

```
.claude/hooks/
├── main.py                    # Single entry point (replaces pre_tool_use.py)
├── core/                      # Core interfaces and patterns
│   ├── __init__.py
│   ├── interfaces.py          # All interface definitions
│   ├── factory.py             # Component factory (SOLID OCP/DIP)
│   ├── config.py              # Centralized configuration
│   └── exceptions.py          # Custom exceptions
├── validators/                # All validation logic (SRP)
│   ├── __init__.py
│   ├── file_validator.py      # File system validation
│   ├── security_validator.py  # .env protection, dangerous commands
│   ├── path_validator.py      # Path structure validation
│   └── command_validator.py   # Bash command validation
├── processors/               # All processing logic (SRP)
│   ├── __init__.py
│   ├── context_processor.py  # Context injection
│   ├── logging_processor.py  # Audit logging
│   └── session_processor.py  # Session management
├── hints/                    # Hint generation (SRP)
│   ├── __init__.py
│   ├── mcp_hints.py          # MCP-related hints
│   ├── file_hints.py         # File operation hints
│   └── workflow_hints.py     # Workflow guidance hints
└── utils/                    # Minimal essential utilities
    ├── docs_manager.py       # Documentation enforcement
    └── env_loader.py         # Environment variable loading
```

**File Count Reduction**: From 55 files to ~15-20 focused files (73% reduction)

## Core Architecture Components

### 1. Interface Definitions (`core/interfaces.py`)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class Validator(ABC):
    """Abstract interface for all validators"""
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def get_error_message(self) -> str:
        pass

class Processor(ABC):
    """Abstract interface for all processors"""
    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

class HintProvider(ABC):
    """Abstract interface for hint providers"""
    @abstractmethod
    def get_hints(self, data: Dict[str, Any]) -> Optional[List[str]]:
        pass

class HookComponent(ABC):
    """Base interface for all hook components"""
    @abstractmethod
    def initialize(self, config: 'Config') -> None:
        pass
```

### 2. Factory Pattern (`core/factory.py`)

```python
class HookComponentFactory:
    """Factory for creating hook components (OCP/DIP compliance)"""
    
    def __init__(self, config: Config):
        self.config = config
        
    def create_validators(self) -> List[Validator]:
        """Create validators based on configuration"""
        validators = []
        
        if self.config.enable_file_validation:
            validators.append(FileValidator(self.config))
            
        if self.config.enable_security_validation:
            validators.append(SecurityValidator(self.config))
            
        if self.config.enable_path_validation:
            validators.append(PathValidator(self.config))
            
        if self.config.enable_command_validation:
            validators.append(CommandValidator(self.config))
            
        return validators
        
    def create_processors(self) -> List[Processor]:
        """Create processors based on configuration"""
        processors = []
        
        if self.config.enable_context_injection:
            processors.append(ContextProcessor(self.config))
            
        if self.config.enable_audit_logging:
            processors.append(LoggingProcessor(self.config))
            
        if self.config.enable_session_management:
            processors.append(SessionProcessor(self.config))
            
        return processors
        
    def create_hint_providers(self) -> List[HintProvider]:
        """Create hint providers based on configuration"""
        providers = []
        
        if self.config.enable_mcp_hints:
            providers.append(MCPHintProvider(self.config))
            
        if self.config.enable_file_hints:
            providers.append(FileHintProvider(self.config))
            
        if self.config.enable_workflow_hints:
            providers.append(WorkflowHintProvider(self.config))
            
        return providers
```

### 3. Main Entry Point (`main.py`)

```python
#!/usr/bin/env python3
"""
Clean, modular pre-tool use hook following SOLID principles.
Single entry point replacing monolithic pre_tool_use.py
"""

import json
import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core import Config, HookComponentFactory, HookException

class PreToolUseHook:
    """Main hook class following dependency inversion principle"""
    
    def __init__(self):
        self.config = Config()
        self.factory = HookComponentFactory(self.config)
        
        # Dependency injection through factory
        self.validators = self.factory.create_validators()
        self.processors = self.factory.create_processors()
        self.hint_providers = self.factory.create_hint_providers()
    
    def execute(self, tool_data: dict) -> dict:
        """Execute hook with clean separation of concerns"""
        try:
            # Validation phase (SRP)
            for validator in self.validators:
                if not validator.validate(tool_data):
                    raise HookException(validator.get_error_message())
            
            # Processing phase (SRP)
            result_data = tool_data
            for processor in self.processors:
                result_data = processor.process(result_data)
            
            # Hint generation phase (SRP)
            hints = []
            for provider in self.hint_providers:
                provider_hints = provider.get_hints(result_data)
                if provider_hints:
                    hints.extend(provider_hints)
            
            # Add hints to result
            if hints:
                result_data['__claude_hints'] = hints
                
            return result_data
            
        except HookException as e:
            return {"error": str(e), "blocked": True}
        except Exception as e:
            return {"error": f"Hook execution failed: {e}", "blocked": True}

def main():
    """Entry point function"""
    try:
        # Read input data
        tool_data = json.loads(sys.stdin.read())
        
        # Execute hook
        hook = PreToolUseHook()
        result = hook.execute(tool_data)
        
        # Output result
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {"error": f"Hook failed: {e}", "blocked": True}
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Component Responsibilities

### Validators (SRP Compliance)

#### FileValidator
- **Single Responsibility**: File system operation validation
- **Functions**:
  - Root directory creation restrictions
  - File naming conventions
  - File type restrictions (.md files location)
  - Duplicate file prevention

#### SecurityValidator  
- **Single Responsibility**: Security threat prevention
- **Functions**:
  - .env file access protection
  - Dangerous command detection (rm -rf, etc.)
  - Path traversal prevention
  - Malicious pattern detection

#### PathValidator
- **Single Responsibility**: Path structure enforcement
- **Functions**:
  - ai_docs folder structure validation
  - Test file location enforcement
  - Kebab-case folder naming
  - Project structure compliance

#### CommandValidator
- **Single Responsibility**: Bash command validation
- **Functions**:
  - Command safety verification
  - Parameter validation
  - Execution context checking
  - Command whitelist/blacklist

### Processors (SRP Compliance)

#### ContextProcessor
- **Single Responsibility**: Context injection and management
- **Functions**:
  - MCP context injection
  - Tool metadata enrichment
  - Context synchronization
  - Context validation

#### LoggingProcessor
- **Single Responsibility**: Audit trail and logging
- **Functions**:
  - Operation logging
  - Audit trail maintenance
  - Security event logging
  - Performance metrics

#### SessionProcessor
- **Single Responsibility**: Session management
- **Functions**:
  - Session tracking
  - State management
  - Session cleanup
  - Multi-session coordination

### Hint Providers (SRP Compliance)

#### MCPHintProvider
- **Single Responsibility**: MCP-specific guidance
- **Functions**:
  - MCP usage hints
  - Tool-specific guidance
  - Integration suggestions
  - Best practice recommendations

#### FileHintProvider
- **Single Responsibility**: File operation guidance
- **Functions**:
  - File creation suggestions
  - Location recommendations
  - Naming convention hints
  - Structure guidance

#### WorkflowHintProvider
- **Single Responsibility**: Workflow optimization hints
- **Functions**:
  - Process improvement suggestions
  - Efficiency recommendations
  - Pattern recognition
  - Automation opportunities

## Configuration Management

### Environment-Based Configuration (`core/config.py`)

```python
class Config:
    """Centralized configuration management"""
    
    def __init__(self):
        self.load_from_environment()
    
    def load_from_environment(self):
        """Load configuration from environment variables"""
        self.enable_file_validation = self._get_bool_env('CLAUDE_ENABLE_FILE_VALIDATION', True)
        self.enable_security_validation = self._get_bool_env('CLAUDE_ENABLE_SECURITY_VALIDATION', True)
        self.enable_path_validation = self._get_bool_env('CLAUDE_ENABLE_PATH_VALIDATION', True)
        self.enable_command_validation = self._get_bool_env('CLAUDE_ENABLE_COMMAND_VALIDATION', True)
        
        self.enable_context_injection = self._get_bool_env('CLAUDE_ENABLE_CONTEXT_INJECTION', True)
        self.enable_audit_logging = self._get_bool_env('CLAUDE_ENABLE_AUDIT_LOGGING', True)
        self.enable_session_management = self._get_bool_env('CLAUDE_ENABLE_SESSION_MANAGEMENT', True)
        
        self.enable_mcp_hints = self._get_bool_env('CLAUDE_ENABLE_MCP_HINTS', True)
        self.enable_file_hints = self._get_bool_env('CLAUDE_ENABLE_FILE_HINTS', True)
        self.enable_workflow_hints = self._get_bool_env('CLAUDE_ENABLE_WORKFLOW_HINTS', True)
        
        # Load component-specific configurations
        self.allowed_root_files = self._load_allowed_files()
        self.valid_test_paths = self._load_test_paths()
        self.ai_docs_path = self._get_env('AI_DOCS_PATH', 'ai_docs')
```

## Migration Strategy

### Phase 1: Consolidation (Immediate Priority)

1. **Rename Directories** (Remove _clean_arch suffixes)
   ```bash
   mv core_clean_arch/ core/
   mv validators_clean_arch/ validators/
   mv processors_clean_arch/ processors/
   mv hints_clean_arch/ hints/
   ```

2. **Create Missing Components**
   - `core/interfaces.py` - Centralized interface definitions
   - `core/factory.py` - Component factory implementation
   - `validators/security_validator.py` - Extract security logic from monolithic file
   - `main.py` - Unified entry point

3. **Update Existing Components**
   - Enhance `core/config.py` with environment-based configuration
   - Update existing validators to use standardized interfaces
   - Standardize error handling and logging

### Phase 2: Migration (Next Priority)

1. **Extract Functionality from Monolithic Files**
   - Migrate validation logic from `pre_tool_use.py` to appropriate validators
   - Migrate processing logic to appropriate processors
   - Extract hint logic to hint providers

2. **Consolidate Utilities**
   - Review utils/ directory (25+ files)
   - Migrate essential functionality to core components
   - Eliminate duplicate implementations
   - Keep only necessary utilities (docs_manager.py, env_loader.py)

3. **Update Dependencies and Imports**
   - Update all import statements to use new structure
   - Ensure backward compatibility during transition
   - Update component registration in factory

### Phase 3: Cleanup (Final Priority)

1. **Remove Legacy Files**
   - Delete `pre_tool_use.py` (757 lines → replaced by main.py)
   - Delete `pre_tool_use_clean.py` (superseded by main.py)
   - Remove duplicate implementations
   - Clean up backup directories

2. **Update Hook Configuration**
   - Update Claude configuration to use `main.py` as entry point
   - Test all functionality with new entry point
   - Validate performance improvements

3. **Documentation and Testing**
   - Update documentation to reflect new architecture
   - Create unit tests for all components
   - Validate SOLID principle compliance

## Benefits of Clean Architecture

### Immediate Benefits
- **Reduced Complexity**: 73% reduction in file count (55 → 15-20)
- **Single Entry Point**: main.py replaces monolithic pre_tool_use.py
- **Clear Separation**: Each component has single responsibility
- **Easy Testing**: Interface-based design enables easy mocking

### Long-term Benefits
- **Easy Extension**: Add new validators/processors without modifying existing code
- **Configuration-driven**: Enable/disable features without code changes
- **Loose Coupling**: Components depend on interfaces, not implementations
- **Better Performance**: Lazy loading and reduced import overhead

### Maintainability Improvements
- **Predictable Structure**: Clear location for each type of functionality
- **Consistent Patterns**: All components follow same interface patterns
- **Error Handling**: Centralized exception handling and logging
- **Documentation**: Clear component responsibilities and interactions

## Performance Considerations

### Lazy Loading
- Factory creates components only when needed
- Configuration-driven component instantiation
- Reduced memory footprint

### Import Optimization
- Single entry point reduces import overhead
- Eliminated circular import dependencies
- Streamlined module loading

### Caching Strategy
- Component instances cached after creation
- Configuration loaded once at startup
- Session state managed efficiently

## Testing Strategy

### Unit Testing
- Each validator/processor/hint provider tested independently
- Interface-based mocking for dependencies
- Configuration-driven test scenarios
- Edge case coverage for all components

### Integration Testing
- Factory component creation testing
- End-to-end hook execution testing
- Configuration change testing
- Performance benchmarking

### Quality Assurance
- SOLID principle compliance verification
- Code coverage requirements (>90%)
- Performance regression testing
- Backward compatibility validation

## Conclusion

This clean architecture refactoring transforms the .claude/hooks system from a complex, tightly-coupled collection of 55 files into a maintainable, extensible, and testable system following SOLID principles. The new design provides:

1. **Significant Complexity Reduction**: 73% fewer files
2. **SOLID Principle Compliance**: All five principles implemented
3. **Easy Extension**: Factory pattern enables adding components without modifying existing code
4. **Better Performance**: Lazy loading and optimized imports
5. **Improved Maintainability**: Clear separation of concerns and consistent patterns

The migration can be executed in three phases, maintaining backward compatibility throughout the transition, and results in a robust foundation for future development.