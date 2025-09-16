# Hook System Architecture & Testing Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Hook Types & Lifecycle](#hook-types--lifecycle)
4. [Testing Strategy](#testing-strategy)
5. [Test Implementation Guide](#test-implementation-guide)
6. [Mock Patterns](#mock-patterns)
7. [Integration Testing](#integration-testing)
8. [Performance Testing](#performance-testing)

## System Overview

The Claude Hook System is a modular, event-driven architecture that intercepts and enhances Claude's tool usage. It provides validation, context injection, hints, and logging capabilities.

### Core Design Principles
- **Factory Pattern**: Component creation through centralized factories
- **Single Responsibility**: Each component has one clear purpose
- **Dependency Injection**: Components receive dependencies through constructors
- **Abstract Base Classes**: Define contracts for validators, processors, and loggers
- **Configuration-Driven**: YAML configurations for messages and settings

### System Flow
```
User Input → Pre-Hook → Tool Execution → Post-Hook → User Output
                ↓                           ↓
          Validation/Hints            Logging/Reminders
```

## Architecture Components

### 1. Abstract Base Classes

```python
# Core interfaces that all components implement
class Validator(ABC):
    """Validates tool calls before execution"""
    @abstractmethod
    def validate(self, tool_name: str, tool_input: Dict) -> Tuple[bool, Optional[str]]:
        pass

class Processor(ABC):
    """Processes and enriches tool calls"""
    @abstractmethod
    def process(self, tool_name: str, tool_input: Dict) -> Optional[str]:
        pass

class Logger(ABC):
    """Handles logging operations"""
    @abstractmethod
    def log(self, level: str, message: str, data: Optional[Dict] = None):
        pass

class ContextProvider(ABC):
    """Provides context information"""
    @abstractmethod
    def get_context(self, input_data: Dict) -> Optional[Dict[str, Any]]:
        pass
```

### 2. Component Implementations

#### Validators
- **RootFileValidator**: Prevents unauthorized root file creation
- **EnvFileValidator**: Blocks access to sensitive .env files
- **CommandValidator**: Prevents dangerous bash commands
- **DocumentationValidator**: Enforces documentation requirements
- **PermissionValidator**: Checks agent-specific tool permissions

#### Processors
- **ContextProcessor**: Injects MCP context into tool calls
- **HintProcessor**: Provides contextual hints
- **MCPProcessor**: Handles MCP task operations
- **SessionStartProcessor**: Initializes session context
- **ContextFormatterProcessor**: Formats context for display

#### Context Providers
- **GitContextProvider**: Git repository status
- **MCPContextProvider**: MCP tasks and project info
- **DevelopmentContextProvider**: Development environment
- **IssueContextProvider**: Recent errors and issues
- **AgentMessageProvider**: Agent-specific messages

### 3. Configuration System

```yaml
# config/error_messages.yaml
root_file_blocked:
  message: "BLOCKED: File '{filename}' is not allowed in project root"
  hint: "Allowed root files: {allowed_files}"

# config/warning_messages.yaml
documentation_required:
  message: "WARNING: Documentation update required"
  hint: "Update docs before modifying this file"

# config/hint_messages.yaml
task_creation:
  pre_action: "Consider task requirements and dependencies"
  post_action: "Task created successfully. Next: assign to agents"
```

### 4. Utility Components

- **ConfigFactory**: Centralized configuration loading with caching
- **UnifiedHintSystem**: Consolidated hint generation
- **SessionTracker**: 2-hour session management
- **DocsIndexer**: Documentation indexing and requirements
- **EnvLoader**: Safe environment variable loading
- **MCPClient**: MCP server communication

## Hook Types & Lifecycle

### 1. Session Start Hook (`session_start.py`)

**Purpose**: Initialize session with context and agent recommendations

**Execution Flow**:
```python
1. Load configuration
2. Detect session type (principal/sub-agent)
3. Gather context from all providers
4. Format and display context
5. Recommend agent initialization
```

**Key Components**:
- SessionStartHook (main class)
- ComponentFactory (creates providers/processors)
- Multiple ContextProviders
- ContextFormatterProcessor

### 2. Pre-Tool Use Hook (`pre_tool_use.py`)

**Purpose**: Validate and enhance tool calls before execution

**Execution Flow**:
```python
1. Extract tool_name and tool_input
2. Run all validators sequentially
3. If validation fails: block with error message
4. Run processors for hints/context
5. Return success/failure code
```

**Key Components**:
- PreToolUseHook (main class)
- Multiple Validators (5 types)
- Multiple Processors (3 types)
- ComponentFactory

### 3. Post-Tool Use Hook (`post_tool_use.py`)

**Purpose**: Process results and provide feedback after tool execution

**Execution Flow**:
```python
1. Extract tool results
2. Update documentation index if needed
3. Track session files
4. Generate post-action hints
5. Log tool usage
```

**Key Components**:
- PostToolUseHook (main class)
- HintProcessor (post-action hints)
- DocumentationProcessor
- SessionTracker

## Testing Strategy

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Test individual components in isolation
   - Mock all dependencies
   - Focus on single responsibility

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - Use real configurations
   - Test complete workflows

3. **End-to-End Tests** (`tests/e2e/`)
   - Test complete hook execution
   - Simulate real tool calls
   - Verify output formatting

4. **Performance Tests** (`tests/performance/`)
   - Test response times
   - Memory usage
   - Configuration caching

## Test Implementation Guide

### 1. Unit Test Structure

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

class TestRootFileValidator:
    """Test root file validation logic"""

    def setup_method(self):
        """Setup test fixtures"""
        self.validator = RootFileValidator()
        self.validator.allowed_files = ['README.md', 'CHANGELOG.md']

    def test_allows_permitted_root_files(self):
        """Test that allowed files pass validation"""
        # Arrange
        tool_name = 'Write'
        tool_input = {'file_path': 'README.md', 'content': 'test'}

        # Act
        is_valid, error = self.validator.validate(tool_name, tool_input)

        # Assert
        assert is_valid is True
        assert error is None

    def test_blocks_unpermitted_root_files(self):
        """Test that non-allowed files are blocked"""
        # Arrange
        tool_name = 'Write'
        tool_input = {'file_path': 'test.txt', 'content': 'test'}

        # Act
        with patch('utils.config_factory.get_error_message') as mock_get_error:
            mock_get_error.return_value = "BLOCKED: File not allowed"
            is_valid, error = self.validator.validate(tool_name, tool_input)

        # Assert
        assert is_valid is False
        assert "BLOCKED" in error

    @pytest.mark.parametrize("file_path,should_block", [
        ('README.md', False),
        ('CHANGELOG.md', False),
        ('test.txt', True),
        ('src/test.py', False),  # Not in root
        ('./README.md', False),
    ])
    def test_various_file_paths(self, file_path, should_block):
        """Test validation with various file paths"""
        tool_input = {'file_path': file_path}
        is_valid, _ = self.validator.validate('Write', tool_input)
        assert is_valid != should_block
```

### 2. Integration Test Structure

```python
class TestPreToolUseHookIntegration:
    """Test complete pre-tool use hook flow"""

    @pytest.fixture
    def hook(self):
        """Create hook instance with real components"""
        return PreToolUseHook()

    def test_complete_validation_flow(self, hook, tmp_path):
        """Test validation through all validators"""
        # Arrange
        data = {
            'tool_name': 'Write',
            'tool_input': {
                'file_path': str(tmp_path / 'test.txt'),
                'content': 'test content'
            }
        }

        # Act
        exit_code = hook.execute(data)

        # Assert
        assert exit_code == 0  # Should pass for non-root file

    def test_blocking_dangerous_command(self, hook):
        """Test that dangerous commands are blocked"""
        # Arrange
        data = {
            'tool_name': 'Bash',
            'tool_input': {'command': 'rm -rf /'}
        }

        # Act
        exit_code = hook.execute(data)

        # Assert
        assert exit_code == 1  # Should be blocked
```

### 3. Mock Patterns

```python
# Mock MCP Client
@patch('utils.mcp_client.MCPClient')
def test_with_mcp_client(mock_mcp_class):
    mock_client = Mock()
    mock_client.is_authenticated = True
    mock_client.get_task_status.return_value = {
        'active_tasks': 2,
        'pending_tasks': 3
    }
    mock_mcp_class.return_value = mock_client

    # Test code here

# Mock File System
@patch('pathlib.Path.exists')
@patch('builtins.open', new_callable=mock_open, read_data='content')
def test_file_operations(mock_file, mock_exists):
    mock_exists.return_value = True
    # Test code here

# Mock Subprocess
@patch('subprocess.run')
def test_git_operations(mock_run):
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "main\n"
    # Test code here

# Mock Environment Variables
@patch.dict(os.environ, {'AI_DATA': '/custom/path'})
def test_with_env_vars():
    # Test code here
```

### 4. Fixture Patterns

```python
@pytest.fixture
def sample_tool_input():
    """Provide sample tool input data"""
    return {
        'tool_name': 'Write',
        'tool_input': {
            'file_path': '/test/file.py',
            'content': 'test content'
        }
    }

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory with YAML files"""
    config_dir = tmp_path / 'config'
    config_dir.mkdir()

    # Create error_messages.yaml
    error_config = config_dir / 'error_messages.yaml'
    error_config.write_text('''
root_file_blocked:
  message: "BLOCKED: File not allowed"
  hint: "Use allowed files only"
    ''')

    return config_dir

@pytest.fixture
def mock_logger():
    """Provide mock logger"""
    logger = Mock(spec=Logger)
    logger.log = Mock()
    return logger
```

## Integration Testing

### Testing Hook Chain

```python
class TestHookChain:
    """Test complete hook execution chain"""

    def test_session_start_to_tool_use_flow(self):
        """Test flow from session start through tool use"""
        # 1. Session Start
        session_data = {}
        session_hook = SessionStartHook()
        session_result = session_hook.execute(session_data)
        assert session_result == 0

        # 2. Pre-Tool Use
        tool_data = {
            'tool_name': 'Read',
            'tool_input': {'file_path': 'README.md'}
        }
        pre_hook = PreToolUseHook()
        pre_result = pre_hook.execute(tool_data)
        assert pre_result == 0

        # 3. Post-Tool Use
        result_data = {
            'tool_name': 'Read',
            'tool_input': {'file_path': 'README.md'},
            'tool_output': 'file contents'
        }
        post_hook = PostToolUseHook()
        post_result = post_hook.execute(result_data)
        assert post_result == 0
```

### Testing Configuration Loading

```python
class TestConfigurationSystem:
    """Test configuration loading and caching"""

    def test_config_factory_caching(self):
        """Test that configurations are cached properly"""
        from utils.config_factory import ConfigFactory

        factory = ConfigFactory()

        # First load
        config1 = factory.get_config('error_messages')

        # Second load (should be cached)
        config2 = factory.get_config('error_messages')

        assert config1 is config2  # Same object reference

    def test_error_message_formatting(self):
        """Test error message parameter substitution"""
        from utils.config_factory import get_error_message

        message = get_error_message(
            'root_file_blocked',
            filename='test.txt',
            allowed_files='README.md, CHANGELOG.md'
        )

        assert 'test.txt' in message
        assert 'README.md, CHANGELOG.md' in message
```

## Performance Testing

### Response Time Testing

```python
import time
import pytest

class TestHookPerformance:
    """Test hook execution performance"""

    @pytest.mark.performance
    def test_pre_hook_response_time(self):
        """Test that pre-hook executes within acceptable time"""
        hook = PreToolUseHook()
        data = {
            'tool_name': 'Read',
            'tool_input': {'file_path': 'test.py'}
        }

        start = time.time()
        hook.execute(data)
        duration = time.time() - start

        assert duration < 0.1  # Should complete in under 100ms

    @pytest.mark.performance
    def test_config_loading_performance(self):
        """Test configuration loading performance"""
        from utils.config_factory import ConfigFactory

        factory = ConfigFactory()

        start = time.time()
        for _ in range(100):
            factory.get_config('error_messages')
        duration = time.time() - start

        assert duration < 0.1  # 100 loads should be under 100ms (cached)
```

### Memory Usage Testing

```python
import tracemalloc

class TestMemoryUsage:
    """Test memory usage of hook components"""

    def test_hook_memory_usage(self):
        """Test that hooks don't leak memory"""
        tracemalloc.start()

        # Create and execute hooks multiple times
        for _ in range(100):
            hook = PreToolUseHook()
            data = {'tool_name': 'Read', 'tool_input': {}}
            hook.execute(data)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should use less than 10MB for 100 executions
        assert peak < 10 * 1024 * 1024
```

## Test Execution Commands

```bash
# Run all tests
pytest .claude/hooks/tests/

# Run with coverage
pytest .claude/hooks/tests/ --cov=.claude/hooks --cov-report=html

# Run specific test category
pytest .claude/hooks/tests/unit/
pytest .claude/hooks/tests/integration/
pytest .claude/hooks/tests/e2e/

# Run with verbose output
pytest .claude/hooks/tests/ -v

# Run specific test file
pytest .claude/hooks/tests/unit/test_pre_tool_use.py

# Run specific test
pytest .claude/hooks/tests/unit/test_pre_tool_use.py::TestRootFileValidator::test_allows_permitted_root_files

# Run performance tests
pytest .claude/hooks/tests/ -m performance

# Run parallel tests
pytest .claude/hooks/tests/ -n auto
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Mock external dependencies
- Clean up resources after tests

### 2. Test Naming
- Use descriptive test names
- Follow pattern: `test_[what]_[condition]_[expected]`
- Group related tests in classes

### 3. Assertion Patterns
```python
# Be specific with assertions
assert result is True  # Not just assert result
assert error is None
assert "BLOCKED" in error_message
assert len(results) == 3

# Use pytest features
with pytest.raises(ValueError):
    validator.validate(None, {})

# Parametrize for multiple cases
@pytest.mark.parametrize("input,expected", [...])
```

### 4. Mock Best Practices
```python
# Mock at the right level
@patch('utils.mcp_client.MCPClient')  # Mock the class
@patch.object(validator, 'method')  # Mock specific method

# Use spec for type safety
mock_logger = Mock(spec=Logger)

# Assert mock calls
mock_client.get_task_status.assert_called_once_with(task_id='123')
mock_logger.log.assert_called_with('error', ANY, ANY)
```

### 5. Fixture Organization
```python
# conftest.py for shared fixtures
@pytest.fixture(scope='session')
def config_dir():
    """Shared configuration directory"""
    return Path(__file__).parent / 'config'

@pytest.fixture
def clean_environment():
    """Ensure clean test environment"""
    yield
    # Cleanup code here
```

## Troubleshooting Guide

### Common Issues

1. **Import Errors**
```python
# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

2. **Configuration Not Found**
```python
# Use absolute paths for configs
config_path = Path(__file__).parent / 'config' / 'file.yaml'
```

3. **Mock Not Working**
```python
# Patch at import location, not definition location
@patch('pre_tool_use.ConfigFactory')  # Where it's imported
```

4. **Async Issues**
```python
# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
```

## Summary

The hook system architecture follows clean code principles with:
- Clear separation of concerns through abstract base classes
- Factory pattern for component creation
- Configuration-driven behavior
- Comprehensive validation and processing pipeline

Testing should cover:
- Unit tests for individual components
- Integration tests for component interactions
- End-to-end tests for complete workflows
- Performance tests for response times and resource usage

Follow the patterns and examples in this guide to ensure consistent, reliable tests that maintain the integrity of the hook system.