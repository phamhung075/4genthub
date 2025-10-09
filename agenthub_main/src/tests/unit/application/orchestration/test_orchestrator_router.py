"""
Tests for Orchestrator Router - Strangler Fig Pattern

Tests verify:
1. Router correctly selects domain orchestrator when flag is False
2. Router correctly selects application orchestrator when flag is True
3. Both implementations provide identical interface
4. Feature flag can be toggled dynamically
"""

import pytest
from unittest.mock import patch, MagicMock

from fastmcp.task_management.application.orchestration.orchestrator_router import (
    get_orchestrator,
    OrchestratorRouter,
    orchestrate_project,
)


class TestOrchestratorRouter:
    """Test suite for orchestrator router with feature flag"""

    def test_get_orchestrator_uses_domain_layer_when_flag_false(self):
        """Test router returns domain orchestrator when feature flag is False"""
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = False

            orchestrator = get_orchestrator()

            # Should be domain layer orchestrator
            assert orchestrator.__class__.__name__ == 'Orchestrator'
            assert orchestrator.__class__.__module__.endswith('domain.services.orchestrator')

    def test_get_orchestrator_uses_application_layer_when_flag_true(self):
        """Test router returns application orchestrator when feature flag is True"""
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = True

            orchestrator = get_orchestrator()

            # Should be application layer orchestrator
            assert orchestrator.__class__.__name__ == 'ProjectOrchestrator'
            assert orchestrator.__class__.__module__.endswith('application.orchestration.project_orchestrator')

    def test_orchestrator_router_delegates_to_correct_implementation(self):
        """Test OrchestratorRouter class delegates to appropriate orchestrator"""
        # Test with domain layer (flag False)
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = False

            router = OrchestratorRouter()

            assert router.current_layer == "domain"
            assert router.is_using_domain_layer is True
            assert router.is_using_application_layer is False

        # Test with application layer (flag True)
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = True

            router = OrchestratorRouter()

            assert router.current_layer == "application"
            assert router.is_using_application_layer is True
            assert router.is_using_domain_layer is False

    def test_router_maintains_identical_interface(self):
        """Test both orchestrator implementations have identical interface"""
        # Create mock project
        mock_project = MagicMock()

        # Test domain orchestrator interface
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = False
            router = OrchestratorRouter()

            # Verify methods exist
            assert hasattr(router, 'orchestrate_project')
            assert hasattr(router, 'coordinate_cross_tree_dependencies')
            assert hasattr(router, 'balance_workload')

        # Test application orchestrator interface
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = True
            router = OrchestratorRouter()

            # Verify same methods exist
            assert hasattr(router, 'orchestrate_project')
            assert hasattr(router, 'coordinate_cross_tree_dependencies')
            assert hasattr(router, 'balance_workload')

    def test_convenience_function_orchestrate_project(self):
        """Test convenience function works with feature flag"""
        mock_project = MagicMock()
        mock_project.id = "test-project-123"
        mock_project.registered_agents = {}
        mock_project.git_branchs = {}
        mock_project.active_work_sessions = {}
        mock_project.cross_tree_dependencies = {}

        # Test with domain layer
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = False

            result = orchestrate_project(mock_project)

            # Should get response from domain orchestrator
            assert isinstance(result, dict)
            assert 'project_id' in result
            # Domain orchestrator doesn't add layer field
            assert 'orchestrator_layer' not in result or result.get('orchestrator_layer') != 'application'

    def test_feature_flag_can_be_toggled(self):
        """Test that feature flag changes are picked up by router"""
        # Start with False
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = False
            router1 = OrchestratorRouter()
            assert router1.current_layer == "domain"

        # Switch to True
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = True
            router2 = OrchestratorRouter()
            assert router2.current_layer == "application"

        # Verify they're different
        assert router1.current_layer != router2.current_layer

    def test_both_orchestrators_return_dict_with_project_id(self):
        """Test both orchestrators return expected response structure"""
        mock_project = MagicMock()
        mock_project.id = "test-project-456"
        mock_project.registered_agents = {}
        mock_project.git_branchs = {}
        mock_project.active_work_sessions = {}
        mock_project.cross_tree_dependencies = {}

        # Test domain orchestrator response
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = False
            orchestrator = get_orchestrator()
            result = orchestrator.orchestrate_project(mock_project)

            assert isinstance(result, dict)
            assert result['project_id'] == "test-project-456"

        # Test application orchestrator response
        with patch('fastmcp.task_management.application.orchestration.orchestrator_router.settings') as mock_settings:
            mock_settings.feature_application_orchestrator = True
            orchestrator = get_orchestrator()
            result = orchestrator.orchestrate_project(mock_project)

            assert isinstance(result, dict)
            assert result['project_id'] == "test-project-456"
            # Application orchestrator adds layer identifier
            assert result.get('orchestrator_layer') == 'application'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
