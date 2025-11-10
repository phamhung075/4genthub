"""
Unit tests for Agent Converter Infrastructure Service
Generated from agent_converter.py analysis
Date: 2025-09-26

Tests the agent converter service that converts simplified agent data to full Agent entities.
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from fastmcp.task_management.domain.entities.agent import (
    Agent,
    AgentCapability,
    AgentStatus,
)
from fastmcp.task_management.infrastructure.services.agent_converter import (
    AgentConverter,
)


class TestAgentConverter:
    """Test suite for AgentConverter infrastructure service"""
    
    @pytest.fixture
    def converter(self):
        """Create converter instance for testing"""
        return AgentConverter()
    
    def test_convert_simplified_agent_to_entity_basic(self, converter):
        """Test converting basic agent data to entity"""
        agent_data = {
            "id": "coding_agent",
            "name": "Coding Agent",
            "call_agent": "@coding-agent"
        }
        project_id = "project_123"
        
        result = converter.convert_simplified_agent_to_entity(agent_data, project_id)
        
        assert isinstance(result, Agent)
        assert result.id == "coding_agent"
        assert result.name == "Coding Agent"
        assert result.description == "Agent Coding Agent - @coding-agent"
        assert result.status == AgentStatus.AVAILABLE
        assert result.max_concurrent_tasks == 3
        assert result.current_workload == 0
        assert result.priority_preference == "high"
        assert project_id in result.assigned_projects
    
    def test_convert_simplified_agent_to_entity_system_architect(self, converter):
        """Test converting system architect agent with specific capabilities"""
        agent_data = {
            "id": "sys_arch",
            "name": "System Architect",
            "call_agent": "@system-architect-agent"
        }
        project_id = "project_456"
        
        result = converter.convert_simplified_agent_to_entity(agent_data, project_id)
        
        assert AgentCapability.ARCHITECTURE in result.capabilities
        assert AgentCapability.BACKEND_DEVELOPMENT in result.capabilities
        assert "system_design" in result.specializations
        assert "architecture_patterns" in result.specializations
        assert "scalability" in result.specializations
        assert "python" in result.preferred_languages
        assert "java" in result.preferred_languages
        assert "typescript" in result.preferred_languages
    
    def test_convert_simplified_agent_to_entity_coding_agent(self, converter):
        """Test converting coding agent with full stack capabilities"""
        agent_data = {
            "id": "coder",
            "name": "Full Stack Developer",
            "call_agent": "@coding-agent"
        }
        project_id = "project_789"
        
        result = converter.convert_simplified_agent_to_entity(agent_data, project_id)
        
        assert AgentCapability.FRONTEND_DEVELOPMENT in result.capabilities
        assert AgentCapability.BACKEND_DEVELOPMENT in result.capabilities
        assert "full_stack_development" in result.specializations
        assert "api_development" in result.specializations
        assert "web_development" in result.specializations
        assert set(["python", "javascript", "typescript", "html", "css"]).issubset(set(result.preferred_languages))
    
    def test_convert_simplified_agent_to_entity_documentation_agent(self, converter):
        """Test converting documentation agent"""
        agent_data = {
            "id": "doc_writer",
            "name": "Documentation Writer",
            "call_agent": "@documentation-agent"
        }
        project_id = "project_doc"
        
        result = converter.convert_simplified_agent_to_entity(agent_data, project_id)
        
        assert AgentCapability.DOCUMENTATION in result.capabilities
        assert "technical_writing" in result.specializations
        assert "api_documentation" in result.specializations
        assert "user_guides" in result.specializations
        assert "markdown" in result.preferred_languages
        assert "html" in result.preferred_languages
    
    def test_convert_simplified_agent_to_entity_test_orchestrator(self, converter):
        """Test converting test orchestrator agent"""
        agent_data = {
            "id": "tester",
            "name": "Test Orchestrator",
            "call_agent": "@test-orchestrator-agent"
        }
        project_id = "project_test"
        
        result = converter.convert_simplified_agent_to_entity(agent_data, project_id)
        
        assert AgentCapability.TESTING in result.capabilities
        assert "test_automation" in result.specializations
        assert "quality_assurance" in result.specializations
        assert "integration_testing" in result.specializations
    
    def test_convert_simplified_agent_to_entity_devops_agent(self, converter):
        """Test converting DevOps agent"""
        agent_data = {
            "id": "devops",
            "name": "DevOps Engineer",
            "call_agent": "@devops-agent"
        }
        project_id = "project_ops"
        
        result = converter.convert_simplified_agent_to_entity(agent_data, project_id)
        
        assert AgentCapability.DEVOPS in result.capabilities
        assert "ci_cd" in result.specializations
        assert "deployment" in result.specializations
        assert "infrastructure" in result.specializations
        assert "containerization" in result.specializations
        assert "bash" in result.preferred_languages
        assert "yaml" in result.preferred_languages
    
    def test_convert_simplified_agent_to_entity_security_auditor(self, converter):
        """Test converting security auditor agent"""
        agent_data = {
            "id": "security",
            "name": "Security Auditor",
            "call_agent": "@security-auditor-agent"
        }
        project_id = "project_sec"
        
        result = converter.convert_simplified_agent_to_entity(agent_data, project_id)
        
        assert AgentCapability.SECURITY in result.capabilities
        assert "security_audit" in result.specializations
        assert "vulnerability_assessment" in result.specializations
        assert "secure_coding" in result.specializations
    
    def test_convert_simplified_agent_to_entity_unknown_agent(self, converter):
        """Test converting unknown agent type uses defaults"""
        agent_data = {
            "id": "unknown",
            "name": "Unknown Agent",
            "call_agent": "@unknown-agent"
        }
        project_id = "project_unknown"
        
        result = converter.convert_simplified_agent_to_entity(agent_data, project_id)
        
        # Should use default capabilities
        assert AgentCapability.BACKEND_DEVELOPMENT in result.capabilities
        assert "general_development" in result.specializations
        assert "python" in result.preferred_languages
    
    def test_convert_simplified_agent_to_entity_no_call_agent(self, converter):
        """Test converting agent without call_agent field"""
        agent_data = {
            "id": "no_call",
            "name": "No Call Agent"
            # No call_agent field
        }
        project_id = "project_no_call"
        
        result = converter.convert_simplified_agent_to_entity(agent_data, project_id)
        
        # Should generate call_agent from id
        assert result.description == "Agent No Call Agent - @no-call-agent"
    
    def test_extract_agent_details_strips_at_symbol(self, converter):
        """Test that @ symbol is properly stripped from call_agent"""
        capabilities, specializations, languages = converter._extract_agent_details("@coding-agent")
        
        assert AgentCapability.FRONTEND_DEVELOPMENT in capabilities
        assert "full_stack_development" in specializations
        assert "python" in languages
    
    def test_extract_agent_details_handles_underscores(self, converter):
        """Test that underscores and hyphens are properly handled"""
        # Test with underscores converted from hyphens
        capabilities1, spec1, lang1 = converter._extract_agent_details("test-orchestrator-agent")
        capabilities2, spec2, lang2 = converter._extract_agent_details("test_orchestrator_agent")
        
        # Both should map to test-orchestrator-agent
        assert AgentCapability.TESTING in capabilities1
        assert "test_automation" in spec1
    
    def test_convert_project_agents_to_entities(self, converter):
        """Test converting all agents in a project"""
        project_data = {
            "id": "project_multi",
            "registered_agents": {
                "agent1": {
                    "id": "agent1",
                    "name": "Agent One",
                    "call_agent": "@coding-agent"
                },
                "agent2": {
                    "id": "agent2", 
                    "name": "Agent Two",
                    "call_agent": "@documentation-agent"
                }
            }
        }
        
        result = converter.convert_project_agents_to_entities(project_data)
        
        assert len(result) == 2
        assert "agent1" in result
        assert "agent2" in result
        assert isinstance(result["agent1"], Agent)
        assert isinstance(result["agent2"], Agent)
        assert AgentCapability.BACKEND_DEVELOPMENT in result["agent1"].capabilities
        assert AgentCapability.DOCUMENTATION in result["agent2"].capabilities
    
    def test_convert_project_agents_to_entities_with_error(self, converter):
        """Test that conversion errors create fallback agents"""
        project_data = {
            "id": "project_error",
            "registered_agents": {
                "good_agent": {
                    "id": "good_agent",
                    "name": "Good Agent",
                    "call_agent": "@coding-agent"
                },
                "bad_agent": {
                    # Missing required 'id' field
                    "name": "Bad Agent"
                }
            }
        }
        
        with patch.object(converter.logger, 'error') as mock_error:
            result = converter.convert_project_agents_to_entities(project_data)
        
        # Should have both agents, with bad_agent as fallback
        assert len(result) == 2
        assert "good_agent" in result
        assert "bad_agent" in result
        
        # Good agent should be normal
        assert result["good_agent"].name == "Good Agent"
        
        # Bad agent should be fallback
        assert result["bad_agent"].name == "Bad Agent"
        assert result["bad_agent"].description == "Fallback agent for bad_agent"
        assert result["bad_agent"].max_concurrent_tasks == 1  # Fallback has lower limit
        
        # Error should be logged
        mock_error.assert_called_once()
    
    def test_create_fallback_agent(self, converter):
        """Test creating fallback agent with minimal data"""
        agent_id = "fallback_test"
        agent_data = {"name": "Fallback Test"}
        project_id = "project_fallback"
        
        result = converter._create_fallback_agent(agent_id, agent_data, project_id)
        
        assert result.id == agent_id
        assert result.name == "Fallback Test"
        assert result.description == f"Fallback agent for {agent_id}"
        assert result.max_concurrent_tasks == 1
        assert result.current_workload == 0
        assert AgentCapability.BACKEND_DEVELOPMENT in result.capabilities
        assert "general_development" in result.specializations
        assert project_id in result.assigned_projects
    
    def test_create_fallback_agent_no_name(self, converter):
        """Test creating fallback agent without name uses id"""
        agent_id = "no_name_agent"
        agent_data = {}  # No name
        project_id = "project_no_name"
        
        result = converter._create_fallback_agent(agent_id, agent_data, project_id)
        
        assert result.name == agent_id  # Uses id as name
    
    def test_update_agent_assignments(self, converter):
        """Test updating agents with tree assignments"""
        # Create mock agents
        agent1 = Mock(spec=Agent)
        agent2 = Mock(spec=Agent)
        agent_entities = {
            "agent1": agent1,
            "agent2": agent2
        }
        
        agent_assignments = {
            "feature_branch": "agent1",
            "bugfix_branch": "agent2",
            "unknown_branch": "agent3"  # Non-existent agent
        }
        
        converter.update_agent_assignments(agent_entities, agent_assignments)
        
        # Should call assign_to_tree for existing agents
        agent1.assign_to_tree.assert_called_once_with("feature_branch")
        agent2.assign_to_tree.assert_called_once_with("bugfix_branch")
    
    def test_agent_timestamp_fields(self, converter):
        """Test that created_at and updated_at are properly set"""
        before = datetime.now(UTC)
        
        agent_data = {
            "id": "timestamp_test",
            "name": "Timestamp Test",
            "call_agent": "@coding-agent"
        }
        
        result = converter.convert_simplified_agent_to_entity(agent_data, "project_time")
        
        after = datetime.now(UTC)
        
        # Timestamps should be between before and after
        assert before <= result.created_at <= after
        assert before <= result.updated_at <= after
        assert isinstance(result.created_at, datetime)
        assert isinstance(result.updated_at, datetime)