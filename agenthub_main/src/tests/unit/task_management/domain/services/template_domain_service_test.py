"""Unit tests for TemplateDomainService"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from fastmcp.task_management.domain.entities.template import (
    Template,
    TemplateRenderRequest,
)
from fastmcp.task_management.domain.services.template_domain_service import (
    TemplateDomainService,
)
from fastmcp.task_management.domain.value_objects.template_enums import (
    TemplateCategory,
    TemplatePriority,
    TemplateStatus,
    TemplateType,
)
from fastmcp.task_management.domain.value_objects.template_id import TemplateId


class TestTemplateDomainService:
    @pytest.fixture
    def service(self):
        return TemplateDomainService()

    @pytest.fixture
    def mock_template(self):
        """Create a mock template with default values"""
        template = Mock(spec=Template)
        template.name = "Test Template"
        template.content = "Template content"
        template.description = "Test description"
        template.variables = ["var1", "var2"]
        template.file_patterns = ["*.js", "*.ts"]
        template.compatible_agents = ["agent1", "agent2"]
        template.is_active = True
        template.status = TemplateStatus.ACTIVE
        template.priority = TemplatePriority.MEDIUM
        template.template_type = TemplateType.CODE
        template.category = TemplateCategory.DOCUMENTATION
        template.metadata = {"key": "value"}

        # Mock methods
        template.is_compatible_with_agent = Mock(return_value=True)
        template.matches_file_patterns = Mock(return_value=True)

        return template

    def test_validate_template_valid(self, service, mock_template):
        """Test validation of a valid template"""
        errors = service.validate_template(mock_template)
        assert errors == []

    def test_validate_template_empty_name(self, service, mock_template):
        """Test validation fails for empty name"""
        mock_template.name = "   "
        errors = service.validate_template(mock_template)
        assert "Template name cannot be empty" in errors

    def test_validate_template_empty_content(self, service, mock_template):
        """Test validation fails for empty content"""
        mock_template.content = ""
        errors = service.validate_template(mock_template)
        assert "Template content cannot be empty" in errors

    def test_validate_template_empty_description(self, service, mock_template):
        """Test validation fails for empty description"""
        mock_template.description = "  "
        errors = service.validate_template(mock_template)
        assert "Template description cannot be empty" in errors

    def test_validate_template_content_too_large(self, service, mock_template):
        """Test validation fails for content exceeding size limit"""
        mock_template.content = "x" * 1000001  # Over 1MB limit
        errors = service.validate_template(mock_template)
        assert "Template content exceeds maximum size limit" in errors

    def test_validate_template_name_too_long(self, service, mock_template):
        """Test validation fails for name exceeding length limit"""
        mock_template.name = "x" * 256  # Over 255 limit
        errors = service.validate_template(mock_template)
        assert "Template name exceeds maximum length" in errors

    def test_validate_template_description_too_long(self, service, mock_template):
        """Test validation fails for description exceeding length limit"""
        mock_template.description = "x" * 1001  # Over 1000 limit
        errors = service.validate_template(mock_template)
        assert "Template description exceeds maximum length" in errors

    def test_validate_template_empty_variable_name(self, service, mock_template):
        """Test validation fails for empty variable names"""
        mock_template.variables = ["var1", "  ", "var2"]
        errors = service.validate_template(mock_template)
        assert "Variable name cannot be empty" in errors

    def test_validate_template_invalid_variable_characters(
        self, service, mock_template
    ):
        """Test validation fails for variables with invalid characters"""
        mock_template.variables = ["var1", "var@2", "var3"]
        errors = service.validate_template(mock_template)
        assert "Variable 'var@2' contains invalid characters" in errors

    def test_validate_template_empty_file_pattern(self, service, mock_template):
        """Test validation fails for empty file patterns"""
        mock_template.file_patterns = ["*.js", "   ", "*.ts"]
        errors = service.validate_template(mock_template)
        assert "File pattern cannot be empty" in errors

    def test_validate_template_no_compatible_agents(self, service, mock_template):
        """Test validation fails when no compatible agents"""
        mock_template.compatible_agents = []
        errors = service.validate_template(mock_template)
        assert "Template must be compatible with at least one agent" in errors

    def test_can_render_template_success(self, service, mock_template):
        """Test successful template render check"""
        result = service.can_render_template(mock_template, "agent1", ["test.js"])
        assert result is True
        mock_template.is_compatible_with_agent.assert_called_once_with("agent1")
        mock_template.matches_file_patterns.assert_called_once_with(["test.js"])

    def test_can_render_template_inactive(self, service, mock_template):
        """Test render check fails for inactive template"""
        mock_template.is_active = False
        result = service.can_render_template(mock_template, "agent1")
        assert result is False

    def test_can_render_template_wrong_status(self, service, mock_template):
        """Test render check fails for non-active status"""
        mock_template.status = TemplateStatus.DRAFT
        result = service.can_render_template(mock_template, "agent1")
        assert result is False

    def test_can_render_template_incompatible_agent(self, service, mock_template):
        """Test render check fails for incompatible agent"""
        mock_template.is_compatible_with_agent.return_value = False
        result = service.can_render_template(mock_template, "agent3")
        assert result is False

    def test_can_render_template_no_pattern_match(self, service, mock_template):
        """Test render check fails when patterns don't match"""
        mock_template.matches_file_patterns.return_value = False
        result = service.can_render_template(mock_template, "agent1", ["test.py"])
        assert result is False

    def test_calculate_template_score_active_template(self, service, mock_template):
        """Test score calculation for active template"""
        task_context = {"task_type": "code_generation", "category": "documentation"}
        score = service.calculate_template_score(mock_template, task_context, "agent1")
        assert score > 10.0  # Base score for active template

    def test_calculate_template_score_priority_critical(self, service, mock_template):
        """Test score calculation with critical priority"""
        mock_template.priority = TemplatePriority.CRITICAL
        task_context = {}
        score = service.calculate_template_score(mock_template, task_context, "agent1")
        assert score >= 30.0  # Base (10) + critical priority (20)

    def test_calculate_template_score_agent_wildcard(self, service, mock_template):
        """Test score calculation with wildcard agent compatibility"""
        mock_template.compatible_agents = ["*"]
        mock_template.is_compatible_with_agent.return_value = True
        task_context = {}
        score = service.calculate_template_score(
            mock_template, task_context, "any_agent"
        )
        assert score >= 30.0  # Base (10) + wildcard agent (20)

    def test_calculate_template_score_task_type_match(self, service, mock_template):
        """Test score calculation with exact task type match"""
        task_context = {"task_type": "code"}  # Matches template type
        score = service.calculate_template_score(mock_template, task_context, "agent1")
        assert score >= 80.0  # Should include task type match bonus

    def test_calculate_template_score_with_usage_stats(self, service, mock_template):
        """Test score calculation with usage statistics"""
        task_context = {}
        usage_stats = {
            "usage_count": 150,
            "success_rate": 0.95,
            "avg_generation_time": 50,
        }
        score = service.calculate_template_score(
            mock_template, task_context, "agent1", usage_stats=usage_stats
        )
        # Should include usage frequency, success rate, and performance bonuses
        assert score > 50.0

    def test_get_suggestion_reason_critical_priority(self, service, mock_template):
        """Test suggestion reason for critical priority"""
        mock_template.priority = TemplatePriority.CRITICAL
        task_context = {}
        reason = service.get_suggestion_reason(mock_template, task_context, 85.0)
        assert "Critical priority template" in reason

    def test_get_suggestion_reason_task_type_match(self, service, mock_template):
        """Test suggestion reason for task type match"""
        task_context = {"task_type": "code"}
        reason = service.get_suggestion_reason(mock_template, task_context, 70.0)
        assert "Exact match for code tasks" in reason

    def test_get_suggestion_reason_high_score(self, service, mock_template):
        """Test suggestion reason for high score"""
        task_context = {}
        reason = service.get_suggestion_reason(mock_template, task_context, 85.0)
        assert "Highly recommended based on usage patterns" in reason

    def test_get_suggestion_reason_default(self, service, mock_template):
        """Test default suggestion reason"""
        task_context = {}
        reason = service.get_suggestion_reason(mock_template, task_context, 10.0)
        assert "Available template option" in reason

    def test_validate_render_request_valid(self, service):
        """Test validation of valid render request"""
        request = Mock(spec=TemplateRenderRequest)
        request.template_id = TemplateId.generate_new()
        request.variables = {"var1": "value1"}
        request.cache_strategy = "default"

        errors = service.validate_render_request(request)
        assert errors == []

    def test_validate_render_request_missing_template_id(self, service):
        """Test validation fails for missing template ID"""
        request = Mock(spec=TemplateRenderRequest)
        request.template_id = None
        request.variables = {"var1": "value1"}
        request.cache_strategy = "default"

        errors = service.validate_render_request(request)
        assert "Template ID is required" in errors

    def test_validate_render_request_invalid_cache_strategy(self, service):
        """Test validation fails for invalid cache strategy"""
        request = Mock(spec=TemplateRenderRequest)
        request.template_id = TemplateId.generate_new()
        request.variables = {"var1": "value1"}
        request.cache_strategy = "invalid"

        errors = service.validate_render_request(request)
        assert "Invalid cache strategy" in errors

    def test_merge_template_variables_basic(self, service):
        """Test basic variable merging"""
        template_variables = ["var1", "var2", "var3"]
        request_variables = {"var1": "value1", "var3": "value3"}

        result = service.merge_template_variables(template_variables, request_variables)

        assert result == {"var1": "value1", "var2": None, "var3": "value3"}

    def test_merge_template_variables_with_context(self, service):
        """Test variable merging with task context"""
        template_variables = ["var1", "var2", "var3"]
        request_variables = {"var1": "request_value"}
        task_context = {"var1": "context_value", "var2": "context_value2"}

        result = service.merge_template_variables(
            template_variables, request_variables, task_context
        )

        # Request variables should override context variables
        assert result == {
            "var1": "request_value",
            "var2": "context_value2",
            "var3": None,
        }

    def test_create_template_usage(self, service):
        """Test creation of template usage record"""
        template_id = TemplateId.generate_new()

        with patch(
            "fastmcp.task_management.domain.services.template_domain_service.datetime"
        ) as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = mock_now

            usage = service.create_template_usage(
                template_id=template_id,
                task_id="task-123",
                project_id="proj-456",
                agent_name="agent1",
                variables_used={"var1": "value1"},
                output_path="/output/file.js",
                generation_time_ms=150,
                cache_hit=True,
            )

            assert usage.template_id == template_id
            assert usage.task_id == "task-123"
            assert usage.project_id == "proj-456"
            assert usage.agent_name == "agent1"
            assert usage.variables_used == {"var1": "value1"}
            assert usage.output_path == "/output/file.js"
            assert usage.generation_time_ms == 150
            assert usage.cache_hit is True
            assert usage.used_at == mock_now

    def test_should_cache_result_force_regenerate(self, service, mock_template):
        """Test caching disabled when force regenerate is set"""
        request = Mock(spec=TemplateRenderRequest)
        request.force_regenerate = True
        request.cache_strategy = "aggressive"

        result = service.should_cache_result(mock_template, request)
        assert result is False

    def test_should_cache_result_cache_none(self, service, mock_template):
        """Test caching disabled with 'none' strategy"""
        request = Mock(spec=TemplateRenderRequest)
        request.force_regenerate = False
        request.cache_strategy = "none"

        result = service.should_cache_result(mock_template, request)
        assert result is False

    def test_should_cache_result_aggressive(self, service, mock_template):
        """Test caching enabled with aggressive strategy"""
        request = Mock(spec=TemplateRenderRequest)
        request.force_regenerate = False
        request.cache_strategy = "aggressive"

        result = service.should_cache_result(mock_template, request)
        assert result is True

    def test_should_cache_result_minimal_high_priority(self, service, mock_template):
        """Test minimal caching for high priority template"""
        request = Mock(spec=TemplateRenderRequest)
        request.force_regenerate = False
        request.cache_strategy = "minimal"
        mock_template.priority = TemplatePriority.HIGH

        result = service.should_cache_result(mock_template, request)
        assert result is True

    def test_should_cache_result_minimal_low_priority(self, service, mock_template):
        """Test minimal caching disabled for low priority"""
        request = Mock(spec=TemplateRenderRequest)
        request.force_regenerate = False
        request.cache_strategy = "minimal"
        mock_template.priority = TemplatePriority.LOW

        result = service.should_cache_result(mock_template, request)
        assert result is False

    def test_get_cache_ttl_aggressive(self, service, mock_template):
        """Test TTL for aggressive caching"""
        request = Mock(spec=TemplateRenderRequest)
        request.cache_strategy = "aggressive"

        ttl = service.get_cache_ttl(mock_template, request)
        assert ttl == 86400  # 24 hours

    def test_get_cache_ttl_minimal(self, service, mock_template):
        """Test TTL for minimal caching"""
        request = Mock(spec=TemplateRenderRequest)
        request.cache_strategy = "minimal"

        ttl = service.get_cache_ttl(mock_template, request)
        assert ttl == 300  # 5 minutes

    def test_get_cache_ttl_critical_priority(self, service, mock_template):
        """Test TTL for critical priority template"""
        request = Mock(spec=TemplateRenderRequest)
        request.cache_strategy = "default"
        mock_template.priority = TemplatePriority.CRITICAL

        ttl = service.get_cache_ttl(mock_template, request)
        assert ttl == 21600  # 6 hours

    def test_get_cache_ttl_default(self, service, mock_template):
        """Test default TTL"""
        request = Mock(spec=TemplateRenderRequest)
        request.cache_strategy = "default"
        mock_template.priority = TemplatePriority.LOW

        ttl = service.get_cache_ttl(mock_template, request)
        assert ttl == 3600  # 1 hour
