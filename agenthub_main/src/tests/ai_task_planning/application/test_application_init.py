"""Test suite for ai_task_planning.application package initialization"""

import pytest
from fastmcp.ai_task_planning import application


class TestAITaskPlanningApplicationInit:
    """Test cases for ai_task_planning.application package initialization"""
    
    def test_application_package_import(self):
        """Test that the application package can be imported"""
        assert application is not None
    
    def test_application_package_structure(self):
        """Test that the application package has expected structure"""
        assert hasattr(application, '__file__') or hasattr(application, '__path__')