"""
Tests for manage_task_description module - Task Management Tool Description
"""

import pytest
from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.manage_task_description import (
    TOOL_NAME,
    TOOL_DESCRIPTION,
    MANAGE_TASK_DESCRIPTION,
    MANAGE_TASK_PARAMETERS_DESCRIPTION,
    MANAGE_TASK_PARAMS,
    get_manage_task_description,
    get_manage_task_parameters
)


class TestConstants:
    """Test module constants."""

    def test_tool_name(self):
        """Test tool name constant."""
        assert TOOL_NAME == "manage_task"

    def test_tool_description(self):
        """Test tool description constant."""
        assert TOOL_DESCRIPTION == "Comprehensive task management with CRUD operations and dependency support"
        
    def test_manage_task_description_exists(self):
        """Test that comprehensive description exists."""
        assert MANAGE_TASK_DESCRIPTION is not None
        assert len(MANAGE_TASK_DESCRIPTION) > 0
        assert "TASK MANAGEMENT SYSTEM" in MANAGE_TASK_DESCRIPTION


class TestParameterDescriptions:
    """Test parameter descriptions."""

    def test_all_required_parameters_have_descriptions(self):
        """Test that all essential parameters have descriptions."""
        required_params = [
            "action", "git_branch_id", "task_id", "title", "description",
            "status", "priority", "assignees", "completion_summary",
            "query", "dependency_id"
        ]
        
        for param in required_params:
            assert param in MANAGE_TASK_PARAMETERS_DESCRIPTION
            assert len(MANAGE_TASK_PARAMETERS_DESCRIPTION[param]) > 0

    def test_action_parameter_description(self):
        """Test action parameter has comprehensive description."""
        action_desc = MANAGE_TASK_PARAMETERS_DESCRIPTION["action"]
        assert "Valid:" in action_desc
        assert "create" in action_desc
        assert "update" in action_desc
        assert "delete" in action_desc
        assert "complete" in action_desc

    def test_assignees_parameter_description(self):
        """Test assignees parameter mentions it's required for create."""
        assignees_desc = MANAGE_TASK_PARAMS["properties"]["assignees"]["description"]
        assert "REQUIRED for create action" in assignees_desc
        assert "@agent-name" in assignees_desc
        assert "comma-separated" in assignees_desc

    def test_status_parameter_description(self):
        """Test status parameter lists valid values."""
        status_desc = MANAGE_TASK_PARAMETERS_DESCRIPTION["status"]
        assert "todo" in status_desc
        assert "in_progress" in status_desc
        assert "blocked" in status_desc
        assert "done" in status_desc

    def test_priority_parameter_description(self):
        """Test priority parameter lists valid values."""
        priority_desc = MANAGE_TASK_PARAMETERS_DESCRIPTION["priority"]
        assert "low" in priority_desc
        assert "medium" in priority_desc
        assert "high" in priority_desc
        assert "urgent" in priority_desc
        assert "critical" in priority_desc


class TestJSONSchema:
    """Test JSON schema structure."""

    def test_schema_basic_structure(self):
        """Test schema has required structure."""
        assert MANAGE_TASK_PARAMS["type"] == "object"
        assert "properties" in MANAGE_TASK_PARAMS
        assert "required" in MANAGE_TASK_PARAMS
        assert MANAGE_TASK_PARAMS["additionalProperties"] is False

    def test_only_action_is_required(self):
        """Test that only 'action' is marked as required in schema."""
        required = MANAGE_TASK_PARAMS["required"]
        assert len(required) == 1
        assert required[0] == "action"

    def test_action_property_exists(self):
        """Test action property is defined."""
        assert "action" in MANAGE_TASK_PARAMS["properties"]
        action_prop = MANAGE_TASK_PARAMS["properties"]["action"]
        assert action_prop["type"] == "string"
        assert "description" in action_prop

    def test_all_properties_have_type(self):
        """Test all properties have a type defined."""
        for prop_name, prop_def in MANAGE_TASK_PARAMS["properties"].items():
            assert "type" in prop_def, f"Property {prop_name} missing type"
            assert prop_def["type"] in ["string", "integer", "boolean"], f"Property {prop_name} has invalid type"

    def test_all_properties_have_description(self):
        """Test all properties have a description."""
        for prop_name, prop_def in MANAGE_TASK_PARAMS["properties"].items():
            assert "description" in prop_def, f"Property {prop_name} missing description"
            assert len(prop_def["description"]) > 0, f"Property {prop_name} has empty description"

    def test_string_parameters(self):
        """Test string type parameters."""
        string_params = [
            "action", "task_id", "git_branch_id", "title", "description",
            "status", "priority", "details", "estimated_effort", "assignees",
            "labels", "due_date", "dependencies", "dependency_id", "context_id",
            "completion_summary", "testing_notes", "query", "sort_by",
            "sort_order", "assignee", "tag", "user_id"
        ]
        
        for param in string_params:
            assert param in MANAGE_TASK_PARAMS["properties"]
            assert MANAGE_TASK_PARAMS["properties"][param]["type"] == "string"

    def test_integer_parameters(self):
        """Test integer type parameters."""
        integer_params = ["limit", "offset"]
        
        for param in integer_params:
            assert param in MANAGE_TASK_PARAMS["properties"]
            assert MANAGE_TASK_PARAMS["properties"][param]["type"] == "integer"

    def test_boolean_parameters(self):
        """Test boolean type parameters."""
        boolean_params = ["include_context", "force_full_generation"]
        
        for param in boolean_params:
            assert param in MANAGE_TASK_PARAMS["properties"]
            assert MANAGE_TASK_PARAMS["properties"][param]["type"] == "boolean"


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_manage_task_description(self):
        """Test get_manage_task_description function."""
        description = get_manage_task_description()
        assert description == MANAGE_TASK_DESCRIPTION
        assert isinstance(description, str)
        assert len(description) > 0

    def test_get_manage_task_parameters(self):
        """Test get_manage_task_parameters function."""
        params = get_manage_task_parameters()
        assert params == MANAGE_TASK_PARAMS
        assert isinstance(params, dict)
        assert "properties" in params


class TestDescriptionContent:
    """Test the content of the task description."""

    def test_description_has_key_sections(self):
        """Test description contains all key sections."""
        desc = MANAGE_TASK_DESCRIPTION
        
        # Key sections
        assert "WHAT IT DOES:" in desc
        assert "WHEN TO USE:" in desc
        assert "CRITICAL FOR:" in desc
        assert "AI USAGE GUIDELINES:" in desc
        assert "PARAMETER VALIDATION PATTERN" in desc
        assert "VALIDATION FLOW:" in desc
        assert "PRACTICAL EXAMPLES FOR AI:" in desc
        assert "VISION SYSTEM FEATURES" in desc
        assert "BEST PRACTICES FOR AI:" in desc
        assert "ERROR HANDLING:" in desc

    def test_description_action_table(self):
        """Test description contains action table."""
        desc = MANAGE_TASK_DESCRIPTION
        
        # Action table headers
        assert "| Action" in desc
        assert "| Required Parameters" in desc
        assert "| Optional Parameters" in desc
        assert "| Description" in desc
        
        # All actions in table
        actions = [
            "create", "update", "get", "delete", "complete",
            "list", "search", "next", "add_dependency", "remove_dependency"
        ]
        
        for action in actions:
            assert f"| {action}" in desc

    def test_description_examples(self):
        """Test description contains practical examples."""
        desc = MANAGE_TASK_DESCRIPTION
        
        # Example markers
        assert "Starting a new feature:" in desc
        assert "Getting recommended work:" in desc
        assert "Updating progress:" in desc
        assert "Completing with context:" in desc
        assert "Finding related tasks:" in desc
        assert "Creating task with dependencies:" in desc
        assert "Managing dependencies:" in desc

    def test_description_dependency_workflow(self):
        """Test description contains dependency workflow patterns."""
        desc = MANAGE_TASK_DESCRIPTION
        
        assert "DEPENDENCY WORKFLOW PATTERNS:" in desc
        assert "Sequential Tasks:" in desc
        assert "Parallel Work:" in desc
        assert "Blocking Dependencies:" in desc
        assert "Dependency Chain:" in desc
        assert "Cross-Feature Dependencies:" in desc

    def test_description_ai_decision_rules(self):
        """Test description contains AI decision rules."""
        desc = MANAGE_TASK_DESCRIPTION
        
        assert "AI DECISION RULES FOR DEPENDENCIES:" in desc
        assert "IF task requires another task's output:" in desc
        assert "ELIF task is independent:" in desc
        assert "ELIF task is part of sequence:" in desc
        assert "ELIF testing/verification task:" in desc

    def test_description_enhanced_parameters(self):
        """Test description contains enhanced parameter explanations."""
        desc = MANAGE_TASK_DESCRIPTION
        
        assert "ENHANCED PARAMETERS:" in desc
        assert "Be specific and action-oriented" in desc
        assert "Include acceptance criteria" in desc
        assert "REQUIRED for task creation" in desc
        assert "Must have at least one agent" in desc


class TestTwoStageValidation:
    """Test two-stage validation documentation."""

    def test_two_stage_validation_explained(self):
        """Test that two-stage validation pattern is explained."""
        desc = MANAGE_TASK_DESCRIPTION
        
        assert "TWO-STAGE VALIDATION:" in desc
        assert "Schema Level:" in desc
        assert "Business Logic Level:" in desc
        assert "Only 'action' is marked as required in JSON schema" in desc

    def test_validation_flow_explained(self):
        """Test validation flow is documented."""
        desc = MANAGE_TASK_DESCRIPTION
        
        assert "VALIDATION FLOW:" in desc
        assert "MCP receives request" in desc
        assert "Controller receives request" in desc
        assert "Returns specific error" in desc

    def test_actual_required_parameters_table(self):
        """Test actual required parameters table exists."""
        desc = MANAGE_TASK_DESCRIPTION
        
        assert "ACTUAL REQUIRED PARAMETERS BY ACTION" in desc
        assert "| create | action, git_branch_id, title, assignees |" in desc
        assert "| update | action, task_id |" in desc
        assert "| complete | action, task_id |" in desc
        assert "| search | action, query |" in desc
        assert "| add_dependency | action, task_id, dependency_id |" in desc


class TestSpecialParameters:
    """Test special parameter handling."""

    def test_assignees_required_documentation(self):
        """Test assignees parameter documents requirement and format."""
        # Check in main description
        desc = MANAGE_TASK_DESCRIPTION
        assert "MUST have at least 1 agent" in desc
        assert "@agent-name" in desc
        assert "@coding-agent" in desc
        assert "@test-orchestrator-agent" in desc
        
        # Check in parameter description
        param_desc = MANAGE_TASK_PARAMS["properties"]["assignees"]["description"]
        assert "REQUIRED for create action" in param_desc
        assert "minimum 1 required" in param_desc
        assert "42 total available" in param_desc

    def test_multi_value_parameters(self):
        """Test documentation for multi-value parameters."""
        desc = MANAGE_TASK_DESCRIPTION
        
        # Labels
        assert "Can be a single string \"frontend\"" in desc
        assert "or list [\"frontend\", \"auth\"]" in desc
        assert "or comma-separated \"frontend,auth,security\"" in desc
        
        # Dependencies
        assert "can be list [\"task-id-1\", \"task-id-2\"]" in desc
        assert "single string \"task-id\"" in desc
        assert "comma-separated \"task-id-1,task-id-2\"" in desc

    def test_deprecated_parameters(self):
        """Test deprecated parameters are marked."""
        query_desc = MANAGE_TASK_PARAMETERS_DESCRIPTION["query"]
        assert "DEPRECATED for dependency operations" in query_desc
        assert "use 'dependency_id' instead" in query_desc


class TestResponseEnhancements:
    """Test response enhancement documentation."""

    def test_response_enhancements_section(self):
        """Test response enhancements are documented."""
        desc = MANAGE_TASK_DESCRIPTION
        
        assert "RESPONSE ENHANCEMENTS:" in desc
        assert "vision_insights:" in desc
        assert "workflow_hints:" in desc
        assert "related_tasks:" in desc
        assert "progress_indicators:" in desc
        assert "blocker_analysis:" in desc
        assert "impact_assessment:" in desc


class TestBestPractices:
    """Test best practices documentation."""

    def test_best_practices_comprehensive(self):
        """Test best practices section is comprehensive."""
        desc = MANAGE_TASK_DESCRIPTION
        
        practices = [
            "Create tasks BEFORE starting work",
            "Use descriptive titles",
            "Include technical details",
            "Update task status when starting work",
            "Use 'next' action when unsure",
            "Complete tasks with detailed summaries",
            "Search before creating to avoid duplicates",
            "Add dependencies for tasks that must be done in sequence",
            "Use labels for better organization",
            "Define dependencies upfront",
            "Review dependency chains before starting work"
        ]
        
        for practice in practices:
            assert practice in desc


class TestParameterDefaults:
    """Test parameter default values are documented."""

    def test_status_default(self):
        """Test status parameter default behavior is documented."""
        desc = MANAGE_TASK_DESCRIPTION
        assert "create→todo" in desc
        assert "update→in_progress" in desc
        assert "complete→done" in desc

    def test_priority_default(self):
        """Test priority default is documented."""
        priority_desc = MANAGE_TASK_PARAMETERS_DESCRIPTION["priority"]
        assert "Default: 'medium'" in priority_desc

    def test_include_context_default(self):
        """Test include_context default is documented."""
        context_desc = MANAGE_TASK_PARAMETERS_DESCRIPTION["include_context"]
        assert "Default: false" in context_desc

    def test_limit_default(self):
        """Test limit default and range is documented."""
        limit_desc = MANAGE_TASK_PARAMETERS_DESCRIPTION["limit"]
        assert "Default: 50" in limit_desc
        assert "Range: 1-100" in limit_desc