"""Unit tests for infrastructure factories __init__.py module."""
import pytest
from fastmcp.task_management.infrastructure.factories import (
    RuleServiceFactory,
    ProjectServiceFactory
)


class TestFactoriesInit:
    """Test cases for factories package initialization"""
    
    def test_all_factories_are_imported(self):
        """Test that all expected factories are available from the package"""
        # Verify each factory class is importable
        assert RuleServiceFactory is not None
        assert ProjectServiceFactory is not None
    
    def test_factories_are_classes(self):
        """Test that imported items are actually classes"""
        assert isinstance(RuleServiceFactory, type)
        assert isinstance(ProjectServiceFactory, type)
    
    def test_all_exports(self):
        """Test that __all__ contains expected exports"""
        from fastmcp.task_management.infrastructure import factories
        
        expected_exports = [
            "RuleServiceFactory",
            "ProjectServiceFactory",
        ]
        
        assert hasattr(factories, "__all__")
        assert set(factories.__all__) == set(expected_exports)
    
    def test_factory_classes_are_distinct(self):
        """Test that each factory class is a distinct type"""
        factory_classes = [
            RuleServiceFactory,
            ProjectServiceFactory,
        ]
        
        # Convert to set to check uniqueness (removes duplicates)
        unique_classes = set(factory_classes)
        assert len(unique_classes) == len(factory_classes)
    
    def test_import_from_package(self):
        """Test importing from the package namespace"""
        # This tests that the imports work correctly from the package level
        from fastmcp.task_management.infrastructure.factories import RuleServiceFactory as RSF
        from fastmcp.task_management.infrastructure.factories import ProjectServiceFactory as PSF
        
        assert RSF == RuleServiceFactory
        assert PSF == ProjectServiceFactory