"""Test suite for ai_task_planning package initialization"""

import pytest
from fastmcp import ai_task_planning


class TestAITaskPlanningPackageInit:
    """Test cases for ai_task_planning package initialization"""
    
    def test_package_import(self):
        """Test that the ai_task_planning package can be imported"""
        assert ai_task_planning is not None
    
    def test_package_structure(self):
        """Test that the package has expected structure"""
        # The package should exist and be importable
        assert hasattr(ai_task_planning, '__file__') or hasattr(ai_task_planning, '__path__')