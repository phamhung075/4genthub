# Hook System Testing Techniques

## Quick Reference Test Patterns

### 1. Testing Validators

#### Pattern: Test Both Valid and Invalid Cases

```python
class TestValidator:
    """Standard validator test pattern"""

    def setup_method(self):
        """Initialize validator with known state"""
        self.validator = YourValidator()
        # Set any required configuration
        self.validator.config = {'key': 'value'}

    def test_valid_input_passes(self):
        """Valid input should return (True, None)"""
        is_valid, error = self.validator.validate('ToolName', {'valid': 'input'})
        assert is_valid is True
        assert error is None

    def test_invalid_input_blocks(self):
        """Invalid input should return (False, error_message)"""
        is_valid, error = self.validator.validate('ToolName', {'invalid': 'input'})
        assert is_valid is False
        assert error is not None
        assert "BLOCKED" in error

    def test_edge_cases(self):
        """Test boundary conditions"""
        # Empty input
        is_valid, _ = self.validator.validate('ToolName', {})
        assert is_valid is True  # Should handle gracefully

        # None input
        is_valid, _ = self.validator.validate('ToolName', None)
        assert is_valid is True  # Should handle gracefully
```

### 2. Testing Context Providers

#### Pattern: Mock External Dependencies

```python
class TestContextProvider:
    """Standard context provider test pattern"""

    def setup_method(self):
        self.provider = YourContextProvider()

    @patch('subprocess.run')
    def test_successful_context_gathering(self, mock_run):
        """Test successful context retrieval"""
        # Mock external command
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "expected output\n"

        context = self.provider.get_context({})

        assert context is not None
        assert 'expected_key' in context
        mock_run.assert_called_once()

    def test_handles_failure_gracefully(self):
        """Test graceful failure handling"""
        with patch('subprocess.run', side_effect=Exception("Command failed")):
            context = self.provider.get_context({})

            # Should return None or error context, not crash
            assert context is None or 'error' in context
```

### 3. Testing Processors

#### Pattern: Verify Output Formatting

```python
class TestProcessor:
    """Standard processor test pattern"""

    def setup_method(self):
        self.mock_logger = Mock(spec=Logger)
        self.processor = YourProcessor(self.mock_logger)

    def test_processes_and_formats_output(self):
        """Test output formatting"""
        output = self.processor.process('ToolName', {'input': 'data'})

        assert output is not None
        assert "expected text" in output
        # Verify logger was called
        self.mock_logger.log.assert_called()

    def test_returns_none_for_irrelevant_input(self):
        """Test that processor ignores irrelevant tools"""
        output = self.processor.process('IrrelevantTool', {})
        assert output is None
```

### 4. Testing Complete Hooks

#### Pattern: Test Full Execution Flow

```python
class TestCompleteHook:
    """Test complete hook execution"""

    @pytest.fixture
    def hook(self):
        """Create hook with mocked dependencies"""
        with patch('utils.env_loader.get_ai_data_path') as mock_path:
            mock_path.return_value = Path('/tmp/test')
            return YourHook()

    def test_successful_execution(self, hook):
        """Test successful hook execution"""
        data = {
            'tool_name': 'Read',
            'tool_input': {'file_path': 'valid/file.py'}
        }

        exit_code = hook.execute(data)

        assert exit_code == 0

    def test_validation_failure_blocks(self, hook):
        """Test that validation failures block execution"""
        data = {
            'tool_name': 'Write',
            'tool_input': {'file_path': '.env', 'content': 'secret'}
        }

        exit_code = hook.execute(data)

        assert exit_code == 1  # Should be blocked
```

## Common Mock Scenarios

### 1. Mocking File System Operations

```python
# Mock file existence
@patch('pathlib.Path.exists')
def test_file_check(mock_exists):
    mock_exists.return_value = True
    # Your test code

# Mock file reading
@patch('builtins.open', new_callable=mock_open, read_data='file contents')
def test_file_read(mock_file):
    # Your test code

# Mock directory listing
@patch('pathlib.Path.iterdir')
def test_directory_listing(mock_iterdir):
    mock_iterdir.return_value = [
        Path('file1.py'),
        Path('file2.py')
    ]
    # Your test code

# Mock file writing
def test_file_write():
    mock_file = mock_open()
    with patch('builtins.open', mock_file):
        # Your code that writes to file
        pass

    # Verify write was called
    mock_file().write.assert_called()
```

### 2. Mocking MCP Client

```python
@pytest.fixture
def mock_mcp_client():
    """Fixture for MCP client"""
    with patch('utils.mcp_client.MCPClient') as mock_class:
        mock_instance = Mock()
        mock_instance.is_authenticated = True
        mock_instance.get_task_status.return_value = {
            'active_tasks': 2,
            'pending_tasks': 3,
            'blocked_tasks': 0
        }
        mock_instance.call_tool.return_value = {
            'success': True,
            'data': {'result': 'test'}
        }
        mock_class.return_value = mock_instance
        yield mock_instance

def test_with_mcp(mock_mcp_client):
    """Test using MCP client"""
    # Your test code
    assert mock_mcp_client.is_authenticated
```

### 3. Mocking Git Commands

```python
@pytest.fixture
def mock_git():
    """Fixture for git commands"""
    with patch('subprocess.run') as mock_run:
        def git_side_effect(*args, **kwargs):
            cmd = args[0]
            if 'branch' in cmd:
                return Mock(returncode=0, stdout='main\n')
            elif 'status' in cmd:
                return Mock(returncode=0, stdout='M file.py\n')
            elif 'log' in cmd:
                return Mock(returncode=0, stdout='abc123 commit message\n')
            return Mock(returncode=0, stdout='')

        mock_run.side_effect = git_side_effect
        yield mock_run
```

### 4. Mocking Configuration

```python
@pytest.fixture
def mock_config():
    """Fixture for configuration"""
    with patch('utils.config_factory.ConfigFactory') as mock_factory:
        mock_instance = Mock()
        mock_instance.get_config.return_value = {
            'error_messages': {
                'test_error': {
                    'message': 'Test error: {detail}',
                    'hint': 'Test hint'
                }
            }
        }
        mock_factory.return_value = mock_instance
        yield mock_instance
```

## Testing Patterns by Component Type

### Session Start Hook Testing

```python
class TestSessionStart:
    """Specific patterns for session start hook"""

    def test_detects_principal_session(self):
        """Test principal session detection"""
        with patch.dict(os.environ, {}, clear=True):
            hook = SessionStartHook()
            result = hook.execute({})

            # Should contain master orchestrator recommendation
            assert "master-orchestrator-agent" in str(result)

    def test_detects_subagent_session(self):
        """Test sub-agent session detection"""
        with patch.dict(os.environ, {'CLAUDE_SUBAGENT': 'true'}):
            hook = SessionStartHook()
            result = hook.execute({})

            # Should show sub-agent context
            assert "sub-agent" in str(result).lower()

    def test_formats_git_context(self):
        """Test git context formatting"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='feature/new-branch\n'
            )

            hook = SessionStartHook()
            result = hook.execute({})

            assert "feature/new-branch" in str(result)
```

### Pre-Tool Use Hook Testing

```python
class TestPreToolUse:
    """Specific patterns for pre-tool use hook"""

    @pytest.mark.parametrize("tool_name,file_path,should_block", [
        ('Write', '.env', True),           # Block env files
        ('Write', 'test.txt', True),        # Block root files
        ('Write', 'ai_docs/test.md', False), # Allow ai_docs
        ('Read', '.env', True),             # Block env read
        ('Edit', 'src/file.py', False),     # Allow subdirectory
        ('Bash', 'rm -rf /', True),         # Block dangerous
    ])
    def test_validation_matrix(self, tool_name, file_path, should_block):
        """Test validation across multiple scenarios"""
        hook = PreToolUseHook()

        if tool_name == 'Bash':
            data = {'tool_name': tool_name, 'tool_input': {'command': file_path}}
        else:
            data = {'tool_name': tool_name, 'tool_input': {'file_path': file_path}}

        exit_code = hook.execute(data)

        if should_block:
            assert exit_code == 1
        else:
            assert exit_code == 0
```

### Post-Tool Use Hook Testing

```python
class TestPostToolUse:
    """Specific patterns for post-tool use hook"""

    def test_updates_documentation_index(self):
        """Test documentation index update"""
        with patch('utils.docs_indexer.update_index') as mock_update:
            hook = PostToolUseHook()
            data = {
                'tool_name': 'Write',
                'tool_input': {'file_path': 'ai_docs/new.md'},
                'tool_output': 'success'
            }

            hook.execute(data)

            mock_update.assert_called()

    def test_generates_hints(self):
        """Test hint generation"""
        hook = PostToolUseHook()
        data = {
            'tool_name': 'manage_task',
            'tool_input': {'action': 'create'},
            'tool_output': {'task_id': '123'}
        }

        with patch('sys.stderr') as mock_stderr:
            hook.execute(data)

            # Should output hints to stderr
            mock_stderr.write.assert_called()
```

## Data-Driven Testing

### Using Parametrize for Comprehensive Coverage

```python
class TestDataDriven:
    """Data-driven test examples"""

    @pytest.mark.parametrize("input_data,expected_result", [
        # Test case 1: Valid input
        ({'type': 'valid'}, True),
        # Test case 2: Invalid type
        ({'type': 'invalid'}, False),
        # Test case 3: Missing type
        ({}, False),
        # Test case 4: None input
        (None, False),
    ])
    def test_multiple_scenarios(self, input_data, expected_result):
        """Test multiple scenarios with single test"""
        result = process_data(input_data)
        assert result == expected_result

    @pytest.mark.parametrize("file_path", [
        'test.py',
        'src/module.py',
        'tests/test_file.py',
        '/absolute/path/file.py',
        './relative/path/file.py',
    ])
    def test_path_handling(self, file_path):
        """Test various path formats"""
        result = validate_path(file_path)
        assert result is not None
```

## Error Testing Patterns

### Testing Error Handling

```python
class TestErrorHandling:
    """Error handling test patterns"""

    def test_handles_missing_config_gracefully(self):
        """Test missing configuration handling"""
        with patch('pathlib.Path.exists', return_value=False):
            hook = YourHook()
            # Should not crash, should use defaults
            result = hook.execute({})
            assert result is not None

    def test_handles_malformed_input(self):
        """Test malformed input handling"""
        hook = YourHook()

        # Various malformed inputs
        malformed_inputs = [
            None,
            {},
            {'tool_name': None},
            {'tool_input': 'not a dict'},
            {'unexpected': 'field'},
        ]

        for bad_input in malformed_inputs:
            # Should not crash
            result = hook.execute(bad_input)
            assert result in [0, 1]  # Valid exit codes

    def test_logs_errors_appropriately(self):
        """Test error logging"""
        mock_logger = Mock()
        component = YourComponent(mock_logger)

        # Trigger an error condition
        with patch('some.dependency', side_effect=Exception("Test error")):
            component.process_with_error()

        # Verify error was logged
        mock_logger.log.assert_called_with('error', ANY, ANY)
```

## Performance Testing Patterns

### Testing Response Times

```python
class TestPerformance:
    """Performance testing patterns"""

    @pytest.mark.timeout(1)  # Fail if takes more than 1 second
    def test_response_time(self):
        """Test that operation completes quickly"""
        hook = YourHook()
        large_input = {'data': 'x' * 10000}  # Large input

        hook.execute(large_input)  # Should complete within timeout

    def test_caching_improves_performance(self):
        """Test that caching works"""
        import time

        # First call (no cache)
        start = time.time()
        result1 = expensive_operation()
        first_duration = time.time() - start

        # Second call (should be cached)
        start = time.time()
        result2 = expensive_operation()
        second_duration = time.time() - start

        assert result1 == result2  # Same result
        assert second_duration < first_duration * 0.1  # Much faster
```

## Test Organization Best Practices

### Directory Structure

```
.claude/hooks/tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_validators.py   # Validator unit tests
│   ├── test_processors.py   # Processor unit tests
│   └── test_providers.py    # Provider unit tests
├── integration/
│   ├── test_hook_flow.py    # Complete hook flow tests
│   └── test_config.py       # Configuration system tests
├── e2e/
│   └── test_scenarios.py    # End-to-end scenarios
└── fixtures/
    ├── sample_configs.yaml  # Test configurations
    └── sample_data.json     # Test data
```

### Naming Conventions

```python
# Test files: test_*.py
test_pre_tool_use.py

# Test classes: Test<ComponentName>
class TestRootFileValidator:

# Test methods: test_<action>_<condition>_<expected>
def test_validate_root_file_blocks_unauthorized():
def test_process_valid_input_returns_output():
def test_execute_with_error_returns_failure_code():
```

### Running Specific Test Suites

```bash
# Run only unit tests
pytest .claude/hooks/tests/unit/ -v

# Run only integration tests
pytest .claude/hooks/tests/integration/ -v

# Run tests matching pattern
pytest -k "validator" -v

# Run with specific marker
pytest -m "performance" -v

# Run with coverage for hooks only
pytest --cov=.claude/hooks --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=.claude/hooks --cov-report=html
```

## Debugging Failed Tests

### Using pytest debugging features

```bash
# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l

# Show print statements
pytest -s

# Maximum verbosity
pytest -vv

# Show first failure and stop
pytest -x

# Show last failed
pytest --lf

# Show failed first, then others
pytest --ff
```

### Adding debug information to tests

```python
def test_complex_scenario():
    """Test with debug information"""

    # Add descriptive assertions
    result = complex_operation()
    assert result is not None, f"Result was None, expected dict. Input: {input_data}"

    # Use pytest.fail for clear failures
    if not condition:
        pytest.fail(f"Condition failed. State: {current_state}")

    # Add debug prints (visible with pytest -s)
    print(f"Debug: Processing {len(items)} items")

    # Use logging for detailed traces
    logger.debug(f"Intermediate result: {intermediate}")
```

This documentation provides comprehensive testing techniques specifically for the hook system, with practical examples and patterns that can be directly applied to test development.