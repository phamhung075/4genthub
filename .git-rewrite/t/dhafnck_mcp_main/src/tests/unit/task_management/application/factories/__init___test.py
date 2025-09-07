"""Unit tests for application factories __init__.py module."""
import pytest
from fastmcp.task_management.application.factories import (
    TaskFacadeFactory,
    UnifiedContextFacadeFactory,
    ContextServiceFactory,
    SubtaskFacadeFactory,
    AgentFacadeFactory,
    RuleServiceFactory,
    ContextResponseFactory
)


class TestFactoriesInit:
    """Test cases for factories package initialization"""
    
    def test_all_factories_are_imported(self):
        """Test that all expected factories are available from the package"""
        # Verify each factory class is importable
        assert TaskFacadeFactory is not None
        assert UnifiedContextFacadeFactory is not None
        assert ContextServiceFactory is not None
        assert SubtaskFacadeFactory is not None
        assert AgentFacadeFactory is not None
        assert RuleServiceFactory is not None
        assert ContextResponseFactory is not None
    
    def test_context_service_factory_alias(self):
        """Test that ContextServiceFactory is an alias for UnifiedContextFacadeFactory"""
        assert ContextServiceFactory is UnifiedContextFacadeFactory
    
    def test_all_exports(self):
        """Test that __all__ contains expected exports"""
        from fastmcp.task_management.application import factories
        
        expected_exports = [
            "TaskFacadeFactory",
            "UnifiedContextFacadeFactory", 
            "ContextServiceFactory",
            "SubtaskFacadeFactory",
            "AgentFacadeFactory",
            "RuleServiceFactory",
            "ContextResponseFactory",
        ]
        
        assert hasattr(factories, "__all__")
        assert set(factories.__all__) == set(expected_exports)
    
    def test_factory_classes_are_distinct(self):
        """Test that each factory class is a distinct type (except the alias)"""
        factory_classes = [
            TaskFacadeFactory,
            UnifiedContextFacadeFactory,
            SubtaskFacadeFactory,
            AgentFacadeFactory,
            RuleServiceFactory,
            ContextResponseFactory
        ]
        
        # Convert to set to check uniqueness (removes duplicates)
        unique_classes = set(factory_classes)
        assert len(unique_classes) == len(factory_classes)
    
    def test_import_from_package(self):
        """Test importing from the package namespace"""
        # This tests that the imports work correctly from the package level
        from fastmcp.task_management.application.factories import TaskFacadeFactory as TFF
        from fastmcp.task_management.application.factories import UnifiedContextFacadeFactory as UCFF
        from fastmcp.task_management.application.factories import ContextServiceFactory as CSF
        from fastmcp.task_management.application.factories import SubtaskFacadeFactory as SFF
        from fastmcp.task_management.application.factories import AgentFacadeFactory as AFF
        from fastmcp.task_management.application.factories import RuleServiceFactory as RSF
        from fastmcp.task_management.application.factories import ContextResponseFactory as CRF
        
        assert TFF == TaskFacadeFactory
        assert UCFF == UnifiedContextFacadeFactory
        assert CSF == ContextServiceFactory
        assert SFF == SubtaskFacadeFactory
        assert AFF == AgentFacadeFactory
        assert RSF == RuleServiceFactory
        assert CRF == ContextResponseFactory