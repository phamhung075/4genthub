"""
Unit tests for Template domain entities.
Tests Template, TemplateResult, TemplateRenderRequest, and TemplateUsage entities.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from fastmcp.task_management.domain.entities.template import (
    Template,
    TemplateResult,
    TemplateRenderRequest,
    TemplateUsage
)
from fastmcp.task_management.domain.value_objects.template_id import TemplateId
from fastmcp.task_management.domain.enums.template_enums import (
    TemplateType,
    TemplateCategory,
    TemplateStatus,
    TemplatePriority
)


class TestTemplateEntity:
    """Test suite for Template domain entity"""
    
    @pytest.fixture
    def template_id(self):
        """Create a template ID for testing"""
        return TemplateId.generate()
    
    @pytest.fixture
    def valid_template_data(self, template_id):
        """Provide valid test data for Template creation"""
        return {
            'id': template_id,
            'name': 'Test Template',
            'description': 'A test template for unit tests',
            'content': 'Template content with {{variable}}',
            'template_type': TemplateType.TASK,
            'category': TemplateCategory.DEVELOPMENT,
            'status': TemplateStatus.ACTIVE,
            'priority': TemplatePriority.MEDIUM,
            'compatible_agents': ['agent1', 'agent2'],
            'file_patterns': ['*.py', '*.js'],
            'variables': ['variable', 'name'],
            'metadata': {'author': 'test_user', 'tags': ['test']},
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
    
    @pytest.fixture
    def template(self, valid_template_data):
        """Create a Template instance for testing"""
        return Template(**valid_template_data)
    
    def test_create_template_with_valid_data_success(self, valid_template_data):
        """Test Template creation with valid data"""
        template = Template(**valid_template_data)
        
        assert template.id == valid_template_data['id']
        assert template.name == valid_template_data['name']
        assert template.description == valid_template_data['description']
        assert template.content == valid_template_data['content']
        assert template.template_type == valid_template_data['template_type']
        assert template.category == valid_template_data['category']
        assert template.status == valid_template_data['status']
        assert template.priority == valid_template_data['priority']
        assert template.compatible_agents == valid_template_data['compatible_agents']
        assert template.file_patterns == valid_template_data['file_patterns']
        assert template.variables == valid_template_data['variables']
        assert template.metadata == valid_template_data['metadata']
        assert template.version == 1
        assert template.is_active is True
    
    def test_create_template_with_empty_name_raises_error(self, valid_template_data):
        """Test Template creation with empty name raises ValueError"""
        valid_template_data['name'] = ''
        
        with pytest.raises(ValueError, match="Template name cannot be empty"):
            Template(**valid_template_data)
    
    def test_create_template_with_whitespace_name_raises_error(self, valid_template_data):
        """Test Template creation with whitespace-only name raises ValueError"""
        valid_template_data['name'] = '   '
        
        with pytest.raises(ValueError, match="Template name cannot be empty"):
            Template(**valid_template_data)
    
    def test_create_template_with_empty_content_raises_error(self, valid_template_data):
        """Test Template creation with empty content raises ValueError"""
        valid_template_data['content'] = ''
        
        with pytest.raises(ValueError, match="Template content cannot be empty"):
            Template(**valid_template_data)
    
    def test_create_template_with_empty_description_raises_error(self, valid_template_data):
        """Test Template creation with empty description raises ValueError"""
        valid_template_data['description'] = ''
        
        with pytest.raises(ValueError, match="Template description cannot be empty"):
            Template(**valid_template_data)
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_update_content_with_valid_content_success(self, mock_datetime, template):
        """Test updating template content successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        new_content = 'Updated template content with {{new_variable}}'
        original_version = template.version
        
        template.update_content(new_content)
        
        assert template.content == new_content
        assert template.version == original_version + 1
        assert template.updated_at == mock_now
    
    def test_update_content_with_empty_content_raises_error(self, template):
        """Test updating template content with empty string raises ValueError"""
        with pytest.raises(ValueError, match="Template content cannot be empty"):
            template.update_content('')
    
    def test_update_content_with_whitespace_content_raises_error(self, template):
        """Test updating template content with whitespace raises ValueError"""
        with pytest.raises(ValueError, match="Template content cannot be empty"):
            template.update_content('   ')
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_update_metadata_success(self, mock_datetime, template):
        """Test updating template metadata successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        new_metadata = {'version': '2.0', 'category': 'enhanced'}
        original_metadata = template.metadata.copy()
        
        template.update_metadata(new_metadata)
        
        expected_metadata = {**original_metadata, **new_metadata}
        assert template.metadata == expected_metadata
        assert template.updated_at == mock_now
    
    def test_update_metadata_preserves_existing_data(self, template):
        """Test updating metadata preserves existing metadata"""
        original_author = template.metadata.get('author')
        
        template.update_metadata({'new_key': 'new_value'})
        
        assert template.metadata.get('author') == original_author
        assert template.metadata.get('new_key') == 'new_value'
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_add_compatible_agent_new_agent_success(self, mock_datetime, template):
        """Test adding new compatible agent successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        new_agent = 'agent3'
        original_agents = template.compatible_agents.copy()
        
        template.add_compatible_agent(new_agent)
        
        assert new_agent in template.compatible_agents
        assert len(template.compatible_agents) == len(original_agents) + 1
        assert template.updated_at == mock_now
    
    def test_add_compatible_agent_existing_agent_no_duplicate(self, template):
        """Test adding existing compatible agent doesn't create duplicate"""
        existing_agent = template.compatible_agents[0]
        original_count = len(template.compatible_agents)
        
        template.add_compatible_agent(existing_agent)
        
        assert len(template.compatible_agents) == original_count
        assert template.compatible_agents.count(existing_agent) == 1
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_remove_compatible_agent_existing_agent_success(self, mock_datetime, template):
        """Test removing existing compatible agent successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        agent_to_remove = template.compatible_agents[0]
        original_count = len(template.compatible_agents)
        
        template.remove_compatible_agent(agent_to_remove)
        
        assert agent_to_remove not in template.compatible_agents
        assert len(template.compatible_agents) == original_count - 1
        assert template.updated_at == mock_now
    
    def test_remove_compatible_agent_non_existing_agent_no_effect(self, template):
        """Test removing non-existing compatible agent has no effect"""
        non_existing_agent = 'non_existing_agent'
        original_agents = template.compatible_agents.copy()
        original_updated_at = template.updated_at
        
        template.remove_compatible_agent(non_existing_agent)
        
        assert template.compatible_agents == original_agents
        assert template.updated_at == original_updated_at
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_add_file_pattern_new_pattern_success(self, mock_datetime, template):
        """Test adding new file pattern successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        new_pattern = '*.tsx'
        original_patterns = template.file_patterns.copy()
        
        template.add_file_pattern(new_pattern)
        
        assert new_pattern in template.file_patterns
        assert len(template.file_patterns) == len(original_patterns) + 1
        assert template.updated_at == mock_now
    
    def test_add_file_pattern_existing_pattern_no_duplicate(self, template):
        """Test adding existing file pattern doesn't create duplicate"""
        existing_pattern = template.file_patterns[0]
        original_count = len(template.file_patterns)
        
        template.add_file_pattern(existing_pattern)
        
        assert len(template.file_patterns) == original_count
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_remove_file_pattern_existing_pattern_success(self, mock_datetime, template):
        """Test removing existing file pattern successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        pattern_to_remove = template.file_patterns[0]
        original_count = len(template.file_patterns)
        
        template.remove_file_pattern(pattern_to_remove)
        
        assert pattern_to_remove not in template.file_patterns
        assert len(template.file_patterns) == original_count - 1
        assert template.updated_at == mock_now
    
    def test_remove_file_pattern_non_existing_pattern_no_effect(self, template):
        """Test removing non-existing file pattern has no effect"""
        non_existing_pattern = '*.unknown'
        original_patterns = template.file_patterns.copy()
        
        template.remove_file_pattern(non_existing_pattern)
        
        assert template.file_patterns == original_patterns
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_add_variable_new_variable_success(self, mock_datetime, template):
        """Test adding new variable successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        new_variable = 'new_var'
        original_variables = template.variables.copy()
        
        template.add_variable(new_variable)
        
        assert new_variable in template.variables
        assert len(template.variables) == len(original_variables) + 1
        assert template.updated_at == mock_now
    
    def test_add_variable_existing_variable_no_duplicate(self, template):
        """Test adding existing variable doesn't create duplicate"""
        existing_variable = template.variables[0]
        original_count = len(template.variables)
        
        template.add_variable(existing_variable)
        
        assert len(template.variables) == original_count
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_remove_variable_existing_variable_success(self, mock_datetime, template):
        """Test removing existing variable successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        variable_to_remove = template.variables[0]
        original_count = len(template.variables)
        
        template.remove_variable(variable_to_remove)
        
        assert variable_to_remove not in template.variables
        assert len(template.variables) == original_count - 1
        assert template.updated_at == mock_now
    
    def test_remove_variable_non_existing_variable_no_effect(self, template):
        """Test removing non-existing variable has no effect"""
        non_existing_variable = 'non_existing_var'
        original_variables = template.variables.copy()
        
        template.remove_variable(non_existing_variable)
        
        assert template.variables == original_variables
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_activate_template_success(self, mock_datetime, template):
        """Test activating template successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        template.is_active = False
        template.status = TemplateStatus.INACTIVE
        
        template.activate()
        
        assert template.is_active is True
        assert template.status == TemplateStatus.ACTIVE
        assert template.updated_at == mock_now
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_deactivate_template_success(self, mock_datetime, template):
        """Test deactivating template successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        template.deactivate()
        
        assert template.is_active is False
        assert template.status == TemplateStatus.INACTIVE
        assert template.updated_at == mock_now
    
    @patch('fastmcp.task_management.domain.entities.template.datetime')
    def test_archive_template_success(self, mock_datetime, template):
        """Test archiving template successfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        template.archive()
        
        assert template.is_active is False
        assert template.status == TemplateStatus.ARCHIVED
        assert template.updated_at == mock_now
    
    def test_is_compatible_with_agent_exact_match_returns_true(self, template):
        """Test agent compatibility check with exact match returns True"""
        agent_name = template.compatible_agents[0]
        
        assert template.is_compatible_with_agent(agent_name) is True
    
    def test_is_compatible_with_agent_wildcard_returns_true(self, template):
        """Test agent compatibility check with wildcard returns True"""
        template.compatible_agents = ['*']
        
        assert template.is_compatible_with_agent('any_agent') is True
    
    def test_is_compatible_with_agent_no_match_returns_false(self, template):
        """Test agent compatibility check with no match returns False"""
        assert template.is_compatible_with_agent('unknown_agent') is False
    
    def test_matches_file_patterns_exact_match_returns_true(self, template):
        """Test file pattern matching with exact match returns True"""
        file_patterns = [template.file_patterns[0]]
        
        assert template.matches_file_patterns(file_patterns) is True
    
    def test_matches_file_patterns_partial_match_returns_true(self, template):
        """Test file pattern matching with partial match returns True"""
        template.file_patterns = ['*.py']
        file_patterns = ['test.py']
        
        assert template.matches_file_patterns(file_patterns) is True
    
    def test_matches_file_patterns_no_restrictions_returns_true(self, template):
        """Test file pattern matching with no restrictions returns True"""
        template.file_patterns = []
        file_patterns = ['any_file.txt']
        
        assert template.matches_file_patterns(file_patterns) is True
    
    def test_matches_file_patterns_no_match_returns_false(self, template):
        """Test file pattern matching with no match returns False"""
        template.file_patterns = ['*.py']
        file_patterns = ['file.txt']
        
        assert template.matches_file_patterns(file_patterns) is False
    
    def test_pattern_matches_exact_match_returns_true(self, template):
        """Test internal pattern matching with exact match"""
        assert template._pattern_matches('*.py', '*.py') is True
    
    def test_pattern_matches_contains_match_returns_true(self, template):
        """Test internal pattern matching with wildcard patterns"""
        assert template._pattern_matches('*.py', 'test.py') is True
        assert template._pattern_matches('test.*', 'test.py') is True
    
    def test_pattern_matches_wildcard_returns_true(self, template):
        """Test internal pattern matching with wildcard"""
        assert template._pattern_matches('*', 'any_pattern') is True
    
    def test_pattern_matches_no_match_returns_false(self, template):
        """Test internal pattern matching with no match returns False"""
        assert template._pattern_matches('*.py', 'file.txt') is False
    
    def test_to_dict_complete_conversion(self, template):
        """Test converting template to dictionary representation"""
        template_dict = template.to_dict()
        
        assert template_dict['id'] == template.id.value
        assert template_dict['name'] == template.name
        assert template_dict['description'] == template.description
        assert template_dict['content'] == template.content
        assert template_dict['template_type'] == template.template_type.value
        assert template_dict['category'] == template.category.value
        assert template_dict['status'] == template.status.value
        assert template_dict['priority'] == template.priority.value
        assert template_dict['compatible_agents'] == template.compatible_agents
        assert template_dict['file_patterns'] == template.file_patterns
        assert template_dict['variables'] == template.variables
        assert template_dict['metadata'] == template.metadata
        assert template_dict['version'] == template.version
        assert template_dict['is_active'] == template.is_active
        assert 'created_at' in template_dict
        assert 'updated_at' in template_dict
    
    def test_from_dict_complete_conversion(self, valid_template_data):
        """Test creating template from dictionary representation"""
        template = Template(**valid_template_data)
        template_dict = template.to_dict()
        
        reconstructed_template = Template.from_dict(template_dict)
        
        assert reconstructed_template.id.value == template.id.value
        assert reconstructed_template.name == template.name
        assert reconstructed_template.description == template.description
        assert reconstructed_template.content == template.content
        assert reconstructed_template.template_type == template.template_type
        assert reconstructed_template.category == template.category
        assert reconstructed_template.status == template.status
        assert reconstructed_template.priority == template.priority
        assert reconstructed_template.compatible_agents == template.compatible_agents
        assert reconstructed_template.file_patterns == template.file_patterns
        assert reconstructed_template.variables == template.variables
        assert reconstructed_template.metadata == template.metadata
        assert reconstructed_template.version == template.version
        assert reconstructed_template.is_active == template.is_active
    
    def test_from_dict_with_missing_optional_fields_uses_defaults(self, valid_template_data):
        """Test creating template from dict with missing optional fields uses defaults"""
        template = Template(**valid_template_data)
        template_dict = template.to_dict()
        
        # Remove optional fields
        del template_dict['version']
        del template_dict['is_active']
        
        reconstructed_template = Template.from_dict(template_dict)
        
        assert reconstructed_template.version == 1
        assert reconstructed_template.is_active is True


class TestTemplateResultEntity:
    """Test suite for TemplateResult entity"""
    
    @pytest.fixture
    def template_result(self):
        """Create a TemplateResult instance for testing"""
        return TemplateResult(
            content="Rendered template content",
            template_id=TemplateId.generate(),
            variables_used={"name": "test", "version": "1.0"},
            generated_at=datetime.now(timezone.utc),
            generation_time_ms=150,
            cache_hit=False,
            output_path="/path/to/output.txt"
        )
    
    def test_template_result_creation_success(self, template_result):
        """Test TemplateResult creation with all fields"""
        assert template_result.content == "Rendered template content"
        assert isinstance(template_result.template_id, TemplateId)
        assert template_result.variables_used == {"name": "test", "version": "1.0"}
        assert isinstance(template_result.generated_at, datetime)
        assert template_result.generation_time_ms == 150
        assert template_result.cache_hit is False
        assert template_result.output_path == "/path/to/output.txt"
    
    def test_template_result_creation_without_output_path_success(self):
        """Test TemplateResult creation without output path"""
        result = TemplateResult(
            content="Content",
            template_id=TemplateId.generate(),
            variables_used={},
            generated_at=datetime.now(timezone.utc),
            generation_time_ms=100,
            cache_hit=True
        )
        
        assert result.output_path is None
    
    def test_template_result_to_dict_success(self, template_result):
        """Test converting TemplateResult to dictionary"""
        result_dict = template_result.to_dict()
        
        assert result_dict['content'] == template_result.content
        assert result_dict['template_id'] == template_result.template_id.value
        assert result_dict['variables_used'] == template_result.variables_used
        assert result_dict['generated_at'] == template_result.generated_at.isoformat()
        assert result_dict['generation_time_ms'] == template_result.generation_time_ms
        assert result_dict['cache_hit'] == template_result.cache_hit
        assert result_dict['output_path'] == template_result.output_path


class TestTemplateRenderRequestEntity:
    """Test suite for TemplateRenderRequest entity"""
    
    @pytest.fixture
    def render_request(self):
        """Create a TemplateRenderRequest instance for testing"""
        return TemplateRenderRequest(
            template_id=TemplateId.generate(),
            variables={"name": "test", "version": "1.0"},
            task_context={"task_id": "123", "project": "test_project"},
            output_path="/output/file.txt",
            cache_strategy="aggressive",
            force_regenerate=True
        )
    
    def test_template_render_request_creation_success(self, render_request):
        """Test TemplateRenderRequest creation with all fields"""
        assert isinstance(render_request.template_id, TemplateId)
        assert render_request.variables == {"name": "test", "version": "1.0"}
        assert render_request.task_context == {"task_id": "123", "project": "test_project"}
        assert render_request.output_path == "/output/file.txt"
        assert render_request.cache_strategy == "aggressive"
        assert render_request.force_regenerate is True
    
    def test_template_render_request_creation_with_defaults_success(self):
        """Test TemplateRenderRequest creation with default values"""
        request = TemplateRenderRequest(
            template_id=TemplateId.generate(),
            variables={}
        )
        
        assert request.task_context is None
        assert request.output_path is None
        assert request.cache_strategy == "default"
        assert request.force_regenerate is False
    
    def test_template_render_request_to_dict_success(self, render_request):
        """Test converting TemplateRenderRequest to dictionary"""
        request_dict = render_request.to_dict()
        
        assert request_dict['template_id'] == render_request.template_id.value
        assert request_dict['variables'] == render_request.variables
        assert request_dict['task_context'] == render_request.task_context
        assert request_dict['output_path'] == render_request.output_path
        assert request_dict['cache_strategy'] == render_request.cache_strategy
        assert request_dict['force_regenerate'] == render_request.force_regenerate


class TestTemplateUsageEntity:
    """Test suite for TemplateUsage entity"""
    
    @pytest.fixture
    def template_usage(self):
        """Create a TemplateUsage instance for testing"""
        return TemplateUsage(
            template_id=TemplateId.generate(),
            task_id="task_123",
            project_id="project_456",
            agent_name="test_agent",
            variables_used={"var1": "value1", "var2": "value2"},
            output_path="/output/generated_file.txt",
            generation_time_ms=250,
            cache_hit=False,
            used_at=datetime.now(timezone.utc)
        )
    
    def test_template_usage_creation_success(self, template_usage):
        """Test TemplateUsage creation with all fields"""
        assert isinstance(template_usage.template_id, TemplateId)
        assert template_usage.task_id == "task_123"
        assert template_usage.project_id == "project_456"
        assert template_usage.agent_name == "test_agent"
        assert template_usage.variables_used == {"var1": "value1", "var2": "value2"}
        assert template_usage.output_path == "/output/generated_file.txt"
        assert template_usage.generation_time_ms == 250
        assert template_usage.cache_hit is False
        assert isinstance(template_usage.used_at, datetime)
    
    def test_template_usage_creation_with_optional_none_success(self):
        """Test TemplateUsage creation with optional fields as None"""
        usage = TemplateUsage(
            template_id=TemplateId.generate(),
            task_id=None,
            project_id=None,
            agent_name=None,
            variables_used={},
            output_path=None,
            generation_time_ms=100,
            cache_hit=True,
            used_at=datetime.now(timezone.utc)
        )
        
        assert usage.task_id is None
        assert usage.project_id is None
        assert usage.agent_name is None
        assert usage.output_path is None
    
    def test_template_usage_to_dict_success(self, template_usage):
        """Test converting TemplateUsage to dictionary"""
        usage_dict = template_usage.to_dict()
        
        assert usage_dict['template_id'] == template_usage.template_id.value
        assert usage_dict['task_id'] == template_usage.task_id
        assert usage_dict['project_id'] == template_usage.project_id
        assert usage_dict['agent_name'] == template_usage.agent_name
        assert usage_dict['variables_used'] == template_usage.variables_used
        assert usage_dict['output_path'] == template_usage.output_path
        assert usage_dict['generation_time_ms'] == template_usage.generation_time_ms
        assert usage_dict['cache_hit'] == template_usage.cache_hit
        assert usage_dict['used_at'] == template_usage.used_at.isoformat()


class TestTemplateBusinessRules:
    """Test suite for Template business rules and constraints"""
    
    @pytest.fixture
    def template(self):
        """Create a Template for business rule testing"""
        return Template(
            id=TemplateId.generate(),
            name='Test Template',
            description='Test description',
            content='Template content',
            template_type=TemplateType.TASK,
            category=TemplateCategory.DEVELOPMENT,
            status=TemplateStatus.ACTIVE,
            priority=TemplatePriority.MEDIUM,
            compatible_agents=['agent1'],
            file_patterns=['*.py'],
            variables=['var1'],
            metadata={'key': 'value'},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    def test_template_version_increments_on_content_update(self, template):
        """Test that version increments when content is updated"""
        original_version = template.version
        
        template.update_content('New content')
        
        assert template.version == original_version + 1
    
    def test_template_version_doesnt_increment_on_other_updates(self, template):
        """Test that version doesn't increment on non-content updates"""
        original_version = template.version
        
        template.update_metadata({'new_key': 'new_value'})
        template.add_compatible_agent('new_agent')
        template.add_file_pattern('*.js')
        template.add_variable('new_var')
        
        assert template.version == original_version
    
    def test_template_updated_at_changes_on_modifications(self, template):
        """Test that updated_at changes on any modification"""
        original_updated_at = template.updated_at
        
        # Wait a bit to ensure timestamp difference
        import time
        time.sleep(0.001)
        
        template.update_metadata({'key': 'new_value'})
        
        assert template.updated_at > original_updated_at
    
    def test_template_status_consistency_with_is_active_on_activate(self, template):
        """Test status consistency with is_active when activating"""
        template.is_active = False
        template.status = TemplateStatus.INACTIVE
        
        template.activate()
        
        assert template.is_active is True
        assert template.status == TemplateStatus.ACTIVE
    
    def test_template_status_consistency_with_is_active_on_deactivate(self, template):
        """Test status consistency with is_active when deactivating"""
        template.deactivate()
        
        assert template.is_active is False
        assert template.status == TemplateStatus.INACTIVE
    
    def test_template_status_consistency_with_is_active_on_archive(self, template):
        """Test status consistency with is_active when archiving"""
        template.archive()
        
        assert template.is_active is False
        assert template.status == TemplateStatus.ARCHIVED
    
    def test_template_agent_compatibility_prevents_duplicates(self, template):
        """Test agent compatibility list prevents duplicates"""
        existing_agent = template.compatible_agents[0]
        original_count = len(template.compatible_agents)
        
        template.add_compatible_agent(existing_agent)
        
        assert len(template.compatible_agents) == original_count
        assert template.compatible_agents.count(existing_agent) == 1
    
    def test_template_file_patterns_prevents_duplicates(self, template):
        """Test file patterns list prevents duplicates"""
        existing_pattern = template.file_patterns[0]
        original_count = len(template.file_patterns)
        
        template.add_file_pattern(existing_pattern)
        
        assert len(template.file_patterns) == original_count
    
    def test_template_variables_prevents_duplicates(self, template):
        """Test variables list prevents duplicates"""
        existing_variable = template.variables[0]
        original_count = len(template.variables)
        
        template.add_variable(existing_variable)
        
        assert len(template.variables) == original_count
    
    def test_template_wildcard_agent_compatibility(self, template):
        """Test wildcard agent compatibility business rule"""
        template.compatible_agents = ['*']
        
        # Should be compatible with any agent
        assert template.is_compatible_with_agent('any_agent') is True
        assert template.is_compatible_with_agent('another_agent') is True
        assert template.is_compatible_with_agent('') is True
    
    def test_template_file_pattern_matching_logic(self, template):
        """Test file pattern matching business logic"""
        # Empty patterns should match everything
        template.file_patterns = []
        assert template.matches_file_patterns(['any.file']) is True
        
        # Specific patterns should be selective
        template.file_patterns = ['*.py']
        assert template.matches_file_patterns(['script.py']) is True
        assert template.matches_file_patterns(['style.css']) is False


class TestTemplateEdgeCases:
    """Test suite for Template edge cases and error conditions"""
    
    def test_template_with_unicode_content_success(self):
        """Test template with unicode content"""
        template = Template(
            id=TemplateId.generate(),
            name='Template with émojis 🚀',
            description='Déscription with açcénts',
            content='Content with 中文 and émojis 🎉',
            template_type=TemplateType.CUSTOM,
            category=TemplateCategory.GENERAL,
            status=TemplateStatus.ACTIVE,
            priority=TemplatePriority.LOW,
            compatible_agents=[],
            file_patterns=[],
            variables=[],
            metadata={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert '🚀' in template.name
        assert 'açcénts' in template.description
        assert '中文' in template.content
        assert '🎉' in template.content
    
    def test_template_with_empty_collections_success(self):
        """Test template with empty collections"""
        template = Template(
            id=TemplateId.generate(),
            name='Empty Collections Template',
            description='Template with empty collections',
            content='Simple content',
            template_type=TemplateType.TASK,
            category=TemplateCategory.GENERAL,
            status=TemplateStatus.ACTIVE,
            priority=TemplatePriority.LOW,
            compatible_agents=[],
            file_patterns=[],
            variables=[],
            metadata={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert template.compatible_agents == []
        assert template.file_patterns == []
        assert template.variables == []
        assert template.metadata == {}
    
    def test_template_with_very_large_content_success(self):
        """Test template with very large content"""
        large_content = 'X' * 10000  # 10KB of content
        
        template = Template(
            id=TemplateId.generate(),
            name='Large Template',
            description='Template with large content',
            content=large_content,
            template_type=TemplateType.DOCUMENTATION,
            category=TemplateCategory.GENERAL,
            status=TemplateStatus.ACTIVE,
            priority=TemplatePriority.LOW,
            compatible_agents=[],
            file_patterns=[],
            variables=[],
            metadata={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert len(template.content) == 10000
    
    def test_template_serialization_round_trip_with_complex_data(self):
        """Test template serialization round-trip with complex data"""
        template = Template(
            id=TemplateId.generate(),
            name='Complex Template',
            description='Template with complex data structures',
            content='Complex {{nested.variable}} content',
            template_type=TemplateType.CODE,
            category=TemplateCategory.DEVELOPMENT,
            status=TemplateStatus.ACTIVE,
            priority=TemplatePriority.HIGH,
            compatible_agents=['agent1', 'agent2', 'special-agent_123'],
            file_patterns=['*.py', '**/*.js', 'src/**/*.ts'],
            variables=['nested.variable', 'array[0]', 'object.key'],
            metadata={
                'complex_object': {
                    'nested': {'deep': 'value'},
                    'array': [1, 2, 3],
                    'boolean': True,
                    'null_value': None
                }
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=5,
            is_active=False
        )
        
        # Convert to dict and back
        template_dict = template.to_dict()
        reconstructed = Template.from_dict(template_dict)
        
        assert reconstructed.metadata['complex_object']['nested']['deep'] == 'value'
        assert reconstructed.metadata['complex_object']['array'] == [1, 2, 3]
        assert reconstructed.metadata['complex_object']['boolean'] is True
        assert reconstructed.metadata['complex_object']['null_value'] is None
        assert reconstructed.version == 5
        assert reconstructed.is_active is False