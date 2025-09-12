"""Test suite for ai_task_planning.interface package initialization"""

import pytest
from fastmcp.ai_task_planning import interface


class TestAITaskPlanningInterfaceInit:
    """Test cases for ai_task_planning.interface package initialization"""
    
    def test_interface_package_import(self):
        """Test that the interface package can be imported"""
        assert interface is not None
    
    def test_interface_package_structure(self):
        """Test that the interface package has expected structure"""
        assert hasattr(interface, '__file__') or hasattr(interface, '__path__')